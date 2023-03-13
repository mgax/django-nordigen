from django.core.management.base import BaseCommand

from django_nordigen.api import get_api


class Command(BaseCommand):
    help = "Create a Nordigen requisition"

    def add_arguments(self, parser):
        parser.add_argument("institution")
        parser.add_argument("--days", default=90)

    def handle(self, *args, **options):
        institution = options["institution"]
        days = options["days"]
        link = get_api().create_requisition(institution, days)
        print(link)
