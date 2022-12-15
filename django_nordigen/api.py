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


def get_client(integration):
    client = NordigenClient(
        secret_id=integration.nordigen_id,
        secret_key=settings.NORDIGEN_KEY,
    )

    access_token = integration.get_token(Token.TokenType.ACCESS)
    if access_token is None:
        logger.info('No valid access token found; getting one ...')
        refresh_token = integration.get_token(Token.TokenType.REFRESH)

        if refresh_token is None:
            logger.info('No valid refresh token found; getting one ...')
            token_data = client.generate_token()
            integration.save_token(
                Token.TokenType.REFRESH,
                token_data['refresh_expires'],
                token_data['refresh'],
            )
            access_token = integration.save_token(
                Token.TokenType.ACCESS,
                token_data['access_expires'],
                token_data['access'],
            )
            logger.info('Got access and refresh tokens')

        else:
            logger.info('Exchanging refresh token ...')
            token_data = client.exchange_token(refresh_token.value)
            access_token = integration.save_token(
                Token.TokenType.ACCESS,
                token_data['access_expires'],
                token_data['access'],
            )
            logger.info('Got access token')

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
        redirect_uri = urljoin(
            settings.NORDIGEN_SITE_URL, reverse('nordigen:redirect')
        )
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
        requisition.api_data = self.client.requisition.get_requisition_by_id(
            requisition_id=requisition.nordigen_id
        )

        for account_id in requisition.api_data['accounts']:
            try:
                account = self.integration.account_set.get(
                    nordigen_id=account_id
                )
            except Account.DoesNotExist:
                account_api = self.client.account_api(id=account_id)
                api_data = account_api.get_metadata()
                api_details = account_api.get_details()
                account = self.integration.account_set.create(
                    institution=requisition.institution,
                    nordigen_id=account_id,
                    api_data=api_data,
                    api_details=api_details,
                )

            account.requisitions.add(requisition)

        requisition.completed = True
        requisition.save()

    def sync(self):
        for requisition in self.integration.requisition_set.all():
            self.sync_requisition(requisition)

    def sync_requisition(self, requisition):
        for account in requisition.account_set.all():
            self.sync_account(account)

    def iter_transactions(self, account, since, interval=timedelta(days=30)):
        account_api = self.client.account_api(id=account.nordigen_id)
        now = timezone.now().date()

        date_from = since
        while date_from < now:
            date_to = min([date_from + interval, now])
            logger.info(
                'Fetching transactions from %s %s %s',
                account.nordigen_id,
                date_from,
                date_to,
            )
            resp = account_api.get_transactions(
                date_from=date_from, date_to=date_to
            )
            for api_data in resp['transactions']['booked']:
                nordigen_id = api_data.get('internalTransactionId')
                if nordigen_id:
                    yield nordigen_id, api_data

            date_from = date_to

    def get_balance(self, account):
        account_api = self.client.account_api(id=account.nordigen_id)
        logger.info('Fetching balances from %s', account.nordigen_id)
        api_data = account_api.get_balances()
        assert len(api_data['balances']) == 1
        [item] = api_data['balances']
        assert item['balanceType'] in [
            'expected', 'interimAvailable', 'openingBooked'
        ]
        return item

    def sync_account(self, account):
        logger.info('Sync account %s', account)

        account.balance_set.get_or_create(
            defaults=dict(api_data=self.get_balance(account))
        )

        seen = set()
        req = account.requisitions.order_by('-created_at').first()
        since = timezone.now().date() - timedelta(days=req.max_historical_days)
        for tr in account.transaction_set.all():
            seen.add(tr.nordigen_id)
            if tr.booking_date and tr.booking_date > since:
                since = tr.booking_date

        new = []
        for nordigen_id, api_data in self.iter_transactions(account, since):
            if nordigen_id in seen:
                continue
            bookingDate = api_data.get('bookingDate')
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


def get_api():
    integration, _ = Integration.objects.get_or_create(
        nordigen_id=settings.NORDIGEN_ID,
    )

    return Api(integration, get_client(integration))
