from argparse import BooleanOptionalAction
from datetime import timedelta
from uuid import UUID

from django.core.management.base import BaseCommand

from django_nordigen.api import ALL_REQUISITIONS, get_api


class Command(BaseCommand):
    help = "Sync data from Nordigen"

    def add_arguments(self, parser):
        parser.add_argument("requisition", nargs="*")
        parser.add_argument("--max-age", default=900, type=int)
        parser.add_argument("--history", action="store_true")
        parser.add_argument(
            "--transactions", action=BooleanOptionalAction, default=True
        )

    def handle(self, *args, **options):
        requisitions = [UUID(r) for r in options["requisition"]] or ALL_REQUISITIONS
        history = options["history"]
        max_age = timedelta(seconds=options["max_age"])
        get_api().sync(requisitions, max_age, history, options["transactions"])
