from django.core.management.base import BaseCommand

from django_nordigen.api import get_api


class Command(BaseCommand):
    help = 'Sync data from Nordigen'

    def handle(self, *args, **options):
        get_api().sync()
