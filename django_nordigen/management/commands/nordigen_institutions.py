from django.core.management.base import BaseCommand

from django_nordigen.api import get_api


class Command(BaseCommand):
    help = 'List institutions from Nordigen'

    def add_arguments(self, parser):
        parser.add_argument('country')

    def handle(self, *args, **options):
        country = options['country']
        for institution in get_api().get_institutions(country=country):
            print(
                institution['id'],
                institution['transaction_total_days'],
                institution['name'],
            )
