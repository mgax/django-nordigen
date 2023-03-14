import logging
from datetime import date, timedelta
from urllib.parse import urljoin
from uuid import uuid4

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from nordigen import NordigenClient

from .models import Account, Institution, Integration, Token, Transaction

logger = logging.getLogger(__name__)

ALL_REQUISITIONS = object()


def get_client(integration):
    client = NordigenClient(
        secret_id=str(integration.nordigen_id),
        secret_key=settings.NORDIGEN_KEY,
        timeout=60,
    )

    access_token = integration.get_token(Token.TokenType.ACCESS)
    if access_token is None:
        logger.info("No valid access token found; getting one ...")
        refresh_token = integration.get_token(Token.TokenType.REFRESH)

        if refresh_token is None:
            logger.info("No valid refresh token found; getting one ...")
            token_data = client.generate_token()
            integration.save_token(
                Token.TokenType.REFRESH,
                token_data["refresh_expires"],
                token_data["refresh"],
            )
            access_token = integration.save_token(
                Token.TokenType.ACCESS,
                token_data["access_expires"],
                token_data["access"],
            )
            logger.info("Got access and refresh tokens")

        else:
            logger.info("Exchanging refresh token ...")
            token_data = client.exchange_token(refresh_token.value)
            access_token = integration.save_token(
                Token.TokenType.ACCESS,
                token_data["access_expires"],
                token_data["access"],
            )
            logger.info("Got access token")

    client.token = access_token.value
    return client


def get_or_create_institution(client, nordigen_id):
    try:
        return Institution.objects.get(nordigen_id=nordigen_id)
    except Institution.DoesNotExist:
        api_data = client.institution.get_institution_by_id(nordigen_id)
        return Institution.objects.create(
            nordigen_id=nordigen_id,
            api_data=api_data,
        )


class Api:
    def __init__(self, integration, client):
        self.integration = integration
        self.client = client

    def get_institutions(self, country):
        return self.client.institution.get_institutions(country=country)

    def create_requisition(self, institution_id, days):
        reference_id = str(uuid4())
        institution = get_or_create_institution(self.client, institution_id)
        redirect_uri = urljoin(settings.NORDIGEN_SITE_URL, reverse("nordigen:redirect"))
        session = self.client.initialize_session(
            institution_id=institution_id,
            redirect_uri=redirect_uri,
            reference_id=reference_id,
            max_historical_days=days,
        )
        self.integration.requisition_set.create(
            institution=institution,
            nordigen_id=session.requisition_id,
            reference_id=reference_id,
            max_historical_days=days,
        )
        return session.link

    def accept_requisition(self, requisition):
        self.sync_requisition(requisition)
        requisition.completed = True
        requisition.save(update_fields=["completed"])

    def sync_requisition(self, requisition):
        api_data = self.client.requisition.get_requisition_by_id(
            requisition_id=requisition.nordigen_id
        )
        if api_data != requisition.api_data:
            logger.info("Requisition data updated for %s", requisition)
            requisition.api_data = api_data
            requisition.save(update_fields=["api_data"])

        for account_id in requisition.api_data["accounts"]:
            account_api = self.client.account_api(id=account_id)
            api_data = account_api.get_metadata()
            api_details = account_api.get_details()

            try:
                account = self.integration.account_set.get(nordigen_id=account_id)

            except Account.DoesNotExist:
                account = self.integration.account_set.create(
                    institution=requisition.institution,
                    nordigen_id=account_id,
                    api_data=api_data,
                    api_details=api_details,
                )
                logger.info("Account %s created", account)

            else:
                changed = []

                if dict(api_data, last_accessed=None) != dict(
                    account.api_data, last_accessed=None
                ):
                    changed.append("api_data")
                    account.api_data = api_data

                if api_details != account.api_details:
                    changed.append("api_details")
                    account.api_details = api_details

                if changed:
                    logger.info("Account fields for %s changed: %s", account, changed)
                    account.save(update_fields=changed)

            account.requisitions.add(requisition)

    def sync(self, requisitions, max_age, history, transactions=True):
        now = timezone.now()
        for requisition in self.integration.requisition_set.all():
            if (
                requisitions is ALL_REQUISITIONS
                or requisition.nordigen_id in requisitions
            ):
                try:
                    self.sync_requisition(requisition)
                    for account in requisition.account_set.exclude(
                        synced_at__gt=now - max_age
                    ):
                        try:
                            self.sync_account(account, history, transactions)
                        except Exception:
                            logger.error("Error syncing account %r", account)
                            raise

                except Exception:
                    logger.error("Error syncing requisition %r", requisition)
                    raise

    def iter_transactions(self, account, since, interval=timedelta(days=30)):
        account_api = self.client.account_api(id=account.nordigen_id)
        now = timezone.now().date()

        date_from = since
        while date_from < now:
            date_to = min([date_from + interval, now])
            logger.info(
                "Fetching transactions from %s %s %s",
                account.nordigen_id,
                date_from,
                date_to,
            )
            resp = account_api.get_transactions(date_from=date_from, date_to=date_to)
            for api_data in resp["transactions"]["booked"]:
                nordigen_id = api_data.get("internalTransactionId")
                if nordigen_id:
                    yield nordigen_id, api_data

            date_from = date_to

    def get_balances(self, account):
        account_api = self.client.account_api(id=account.nordigen_id)
        logger.info("Fetching balances from %s", account.nordigen_id)
        return account_api.get_balances()["balances"]

    def _sync_transactions(self, account, since):
        seen = set()
        for tr in account.transaction_set.all():
            seen.add(tr.nordigen_id)
            if tr.booking_date and tr.booking_date > since:
                since = tr.booking_date

        new = []
        for nordigen_id, api_data in self.iter_transactions(account, since):
            if nordigen_id in seen:
                continue
            bookingDate = api_data.get("bookingDate")
            booking_date = bookingDate and date.fromisoformat(bookingDate)
            new.append(
                Transaction(
                    account=account,
                    nordigen_id=nordigen_id,
                    api_data=api_data,
                    booking_date=booking_date,
                )
            )
            seen.add(nordigen_id)

        Transaction.objects.bulk_create(new)
        if new:
            logger.info("Created %d transactions", len(new))

    def sync_account(self, account, history, transactions=True):
        logger.info("Sync account %s", account)
        now = timezone.now()

        for api_data in self.get_balances(account):
            account.balance_set.update_or_create(
                type=api_data["balanceType"],
                defaults=dict(
                    api_data=api_data,
                    synced_at=now,
                ),
            )

        if transactions:
            if history:
                req = account.requisitions.order_by("-created_at").first()
                since = now.date() - timedelta(days=req.max_historical_days)

            else:
                since = now.date() - timedelta(days=30)

            self._sync_transactions(account, since)

        account.synced_at = now
        account.save(update_fields=["synced_at"])


def get_api():
    integration, _ = Integration.objects.get_or_create(
        nordigen_id=settings.NORDIGEN_ID,
    )

    return Api(integration, get_client(integration))
