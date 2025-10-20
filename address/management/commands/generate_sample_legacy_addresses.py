import random
from typing import Sequence

from django.core.management.base import BaseCommand

from address.models import Address


SAMPLE_ADDRESSES: Sequence[dict] = (
    {
        "line1": "1600 Amphitheatre Pkwy",
        "city": "Mountain View",
        "state": "CA",
        "postal_code": "94043",
        "country": "United States",
    },
    {
        "line1": "1 Infinite Loop",
        "city": "Cupertino",
        "state": "CA",
        "postal_code": "95014",
        "country": "United States",
    },
    {
        "line1": "350 5th Ave",
        "city": "New York",
        "state": "NY",
        "postal_code": "10118",
        "country": "United States",
    },
    {
        "line1": "221B Baker Street",
        "city": "London",
        "state": "",
        "postal_code": "NW1 6XE",
        "country": "United Kingdom",
    },
    {
        "line1": "200 Broadway",
        "city": "Oakland",
        "state": "CA",
        "postal_code": "94607",
        "country": "United States",
    },
)


class Command(BaseCommand):
    help = "Populate the legacy address table with sample data for ingestion testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=20, help="Number of legacy addresses to create"
        )
        parser.add_argument(
            "--duplicate-ratio",
            type=float,
            default=0.3,
            help="Fraction of rows that reuse existing sample addresses",
        )

    def handle(self, *args, **options):
        count = options["count"]
        duplicate_ratio = max(0.0, min(1.0, options["duplicate_ratio"]))

        created = 0
        duplicates = 0

        for idx in range(count):
            if random.random() < duplicate_ratio and Address.objects.exists():
                sample = Address.objects.order_by("?").first()
                if sample:
                    Address.objects.create(
                        raw=sample.raw,
                        address1=sample.address1,
                        address2=sample.address2,
                        locality=sample.locality,
                        state=sample.state,
                        postal_code=sample.postal_code,
                        country=sample.country,
                    )
                    duplicates += 1
                    continue

            record = dict(random.choice(SAMPLE_ADDRESSES))
            raw = ", ".join(
                filter(
                    None,
                    [
                        record["line1"],
                        record["city"],
                        record["state"],
                        record["postal_code"],
                        record["country"],
                    ],
                )
            )
            Address.objects.create(
                raw=raw,
                address1=record["line1"],
                locality=record["city"],
                state=record["state"],
                postal_code=record["postal_code"],
                country=record["country"],
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Created {created} new legacy addresses ({duplicates} duplicates).")
        )
