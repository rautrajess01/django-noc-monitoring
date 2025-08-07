# base/management/commands/sync_g_sheet.py

import logging
from django.core.management.base import BaseCommand
from base.services import sync_network_events_from_google_sheet

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync data from Google Sheet and update/create NetworkEvent model entries."

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Google Sheet sync to DB...")
        try:
            summary = sync_network_events_from_google_sheet()
            
            if summary.get("message"):
                self.stdout.write(summary["message"])
                return

            summary_str = (
                f"\nSync summary: Created: {summary['created']}, Updated: {summary['updated']}, "
                f"Duplicates: {summary['duplicates']}, Skipped: {summary['skipped']}."
            )
            self.stdout.write(self.style.SUCCESS(summary_str))

        except Exception as e:
            self.stderr.write(f"An error occurred during sync: {e}")
            logger.exception("Google Sheet sync failed.")
