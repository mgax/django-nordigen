import logging
from urllib.parse import urljoin
from uuid import uuid4

from django.conf import settings
from django.urls import reverse
from nordigen import NordigenClient

from .models import Account, Institution, Integration, Token

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


def get_api():
    integration, _ = Integration.objects.get_or_create(
        nordigen_id=settings.NORDIGEN_ID,
    )

    return Api(integration, get_client(integration))
