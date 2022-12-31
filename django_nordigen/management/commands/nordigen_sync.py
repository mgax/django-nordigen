from datetime import timedelta

from django.core.management.base import BaseCommand

from django_nordigen.api import ALL_REQUISITIONS, get_api


class Command(BaseCommand):
    help = 'Sync data from Nordigen'

    def add_arguments(self, parser):
        parser.add_argument('requisition', nargs='*')
        parser.add_argument('--max-age', default=900, type=int)

    def handle(self, *args, **options):
        requisitions = options['requisition'] or ALL_REQUISITIONS
        max_age = timedelta(seconds=options['max_age'])
        get_api().sync(requisitions, max_age)
