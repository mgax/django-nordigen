import logging

from django.conf import settings
from nordigen import NordigenClient

from .models import Integration, Token

logger = logging.getLogger(__name__)


def get_client():
    integration, _ = Integration.objects.get_or_create(
        nordigen_id=settings.NORDIGEN_ID
    )

    client = NordigenClient(
        secret_id=settings.NORDIGEN_ID,
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


class Api:
    def __init__(self, client):
        self.client = client

    def get_institutions(self, country):
        return self.client.institution.get_institutions(country=country)


def get_api():
    return Api(get_client())
