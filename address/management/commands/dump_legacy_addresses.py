import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from address.models import Address


class Command(BaseCommand):
    help = "Export legacy addresses to JSON or JSONL for ingestion."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True, help="Output file path")
        parser.add_argument(
            "--format",
            choices=["jsonl", "json"],
            default="jsonl",
            help="Export format",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])
        fmt = options["format"]

        payload = [
            {
                "line1": address.address1,
                "line2": address.address2,
                "city": address.locality,
                "state": address.state,
                "postal_code": address.postal_code,
                "country": address.country,
                "raw": address.raw,
            }
            for address in Address.objects.all().order_by("id")
        ]

        if not payload:
            raise CommandError("No legacy addresses to export")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "jsonl":
            with output_path.open("w", encoding="utf-8") as handle:
                for entry in payload:
                    handle.write(json.dumps(entry) + "\n")
        else:
            with output_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f"Exported {len(payload)} address(es) to {output_path}")
        )
