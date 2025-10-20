import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from django_address_kit.ingest import ingest_legacy_address


class Command(BaseCommand):
    help = "Ingest legacy django-address payloads into django-address-kit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input", required=True, help="Path to JSONL or JSON file containing legacy addresses"
        )
        parser.add_argument(
            "--format",
            choices=["jsonl", "json"],
            default="jsonl",
            help="Input format: newline-delimited JSON (jsonl) or a JSON array",
        )
        parser.add_argument(
            "--geocode-missing",
            action="store_true",
            help="Geocode entries that lack structured fields using Google Maps",
        )
        parser.add_argument("--google-api-key", help="Google Maps Geocoding API key")

    def handle(self, *args, **options):
        input_path = Path(options["input"])
        if not input_path.exists():
            raise CommandError(f"Input file {input_path} does not exist")

        entries = list(self._iter_entries(input_path, options["format"]))
        if not entries:
            self.stdout.write(self.style.WARNING("No records found; exiting."))
            return

        geocode_missing = options["geocode_missing"]
        google_api_key = options.get("google_api_key")

        ingested = 0
        failures: list[tuple[dict, str]] = []

        for entry in entries:
            try:
                ingest_legacy_address(
                    entry,
                    geocode_missing=geocode_missing,
                    google_api_key=google_api_key,
                )
            except Exception as exc:  # pragma: no cover - defensive
                failures.append((entry, str(exc)))
            else:
                ingested += 1

        self.stdout.write(self.style.SUCCESS(f"Ingested {ingested} address(es)."))

        if failures:
            for record, message in failures[:10]:
                self.stderr.write(f"Failed record: {json.dumps(record)}\n  Reason: {message}")
            raise CommandError(f"{len(failures)} record(s) failed to ingest")

    def _iter_entries(self, path: Path, fmt: str):
        if fmt == "jsonl":
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    yield json.loads(line)
        else:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list):
                for entry in payload:
                    yield entry
            else:
                raise CommandError("JSON input must be an array of objects")
