from django.core.management.base import BaseCommand

from django_nordigen.api import get_api


class Command(BaseCommand):
    help = "Create a Nordigen requisition"

    def add_arguments(self, parser):
        parser.add_argument("institution")
        parser.add_argument("--max-historical-days", default=30)
        parser.add_argument("--access-valid-for-days", default=180)

    def handle(
        self,
        *,
        institution,
        max_historical_days,
        access_valid_for_days,
        **options,
    ):
        link = get_api().create_requisition(
            institution, max_historical_days, access_valid_for_days
        )
        print(link)
