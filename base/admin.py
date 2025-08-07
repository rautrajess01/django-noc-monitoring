import csv
import io
from datetime import datetime
from io import TextIOWrapper

from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.timezone import make_aware

from .forms import NetworkEventImportForm
from .models import NetworkEvent, NetworkEventImport


@admin.register(NetworkEventImport)
class NetworkEventImportAdmin(admin.ModelAdmin):
    form = NetworkEventImportForm
    list_display = [
        "csv_file",
        "uploaded_at",
        "processing_status",
        "processed_rows",
        "created_events",
        "updated_events",  # Added updated events display
        "duplicate_events",
        "skipped_rows_file",
    ]
    list_filter = ["processing_status", "uploaded_at"]
    readonly_fields = [
        "uploaded_at",
        "processed_rows",
        "created_events",
        "updated_events",  # Added updated events as readonly
        "duplicate_events",
        "processing_status",
        "error_message",
        "skipped_rows_file",
    ]

    def save_model(self, request, obj, form, change):
        # First, save the import object and the uploaded file to disk.
        obj.processing_status = "processing"
        super().save_model(request, obj, form, change)

        try:
            # Open the file from disk in BINARY read mode ('rb').
            with obj.csv_file.open(mode="rb") as binary_file:
                # Wrap the binary file with TextIOWrapper to handle UTF-8 decoding.
                text_file = TextIOWrapper(binary_file, encoding="utf-8")
                reader = csv.DictReader(text_file)

                # Helper function for parsing datetime
                def parse_datetime(value):
                    if not value:
                        return None
                    try:
                        dt = datetime.strptime(value.strip(), "%m/%d/%Y %H:%M:%S")
                        return make_aware(
                            dt
                        )  # Converts naive datetime to timezone-aware
                    except (ValueError, TypeError):
                        return None

                row_count = 0
                created_count = 0
                updated_count = 0
                duplicate_count = 0
                skipped_data = []

                def log_skipped_row(reason, row_number, row, problem_value=""):
                    """A helper to capture skipped row details consistently."""
                    info = {
                        "row_number": row_number,
                        "name": row.get("MPLS/Switch", "N/A").strip(),
                        "type": row.get("Type", "N/A").strip(),
                        "date": row.get("Date", "N/A").strip(),
                        "reason": reason,
                        "problem_value": problem_value,
                    }
                    skipped_data.append(info)

                # Process each row using the new create_or_update logic
                with transaction.atomic():
                    for row_number, row in enumerate(
                        reader, 2
                    ):  # Start at 2 to account for header
                        row_count += 1
                        name = row.get("MPLS/Switch", "").strip()
                        if not name:
                            continue
                        down_time_str = row.get("Down Time", "")
                        down_time = parse_datetime(down_time_str)

                        if not down_time:
                            # --- NEW: Capture skipped row info ---
                            log_skipped_row(
                                "Invalid Down Time", row_number, row, down_time_str
                            )
                            continue  # Skip processing this row
                        up_time_str = row.get("Up Time", "").strip()
                        up_time = None  # Assume no valid up_time yet

                        # Only try to parse if there's actually text in the cell
                        if up_time_str:
                            up_time = parse_datetime(up_time_str)

                            # Check for MALFORMED Up Time
                            if not up_time:
                                log_skipped_row(
                                    "Malformed Up Time", row_number, row, up_time_str
                                )
                                continue

                        # Check for ILLOGICAL Up Time (only if up_time is a valid date)
                        if up_time and up_time < down_time:
                            log_skipped_row(
                                "Illogical Up Time (before Down Time)",
                                row_number,
                                row,
                                f"Up: {up_time_str}, Down: {down_time_str}",
                            )
                            continue

                        # Prepare event data
                        event_data = {
                            "name": name,
                            "down_time": down_time,
                            "up_time": parse_datetime(row.get("Up Time")),
                            "date": row.get("Date", "").strip(),
                            "type": row.get("Type", "").strip(),
                            "region": row.get("Region", "").strip(),
                            "reason": row.get("Reason/Issue", "").strip(),
                            "solar": row.get("Full SOLAR POP", "").strip(),
                            "remarks": row.get("Remarks(from mail if any)", "").strip(),
                            "category": row.get("Category", "").strip(),
                            "down_count": (
                                int(row.get("down_count", 0))
                                if row.get("down_count", "").isdigit()
                                else 0
                            ),
                        }

                        # Use the new create_or_update_event method
                        event, created, updated = NetworkEvent.create_or_update_event(
                            **event_data
                        )

                        if created:
                            created_count += 1
                        elif updated:
                            updated_count += 1
                        else:
                            duplicate_count += 1
                if skipped_data:
                    # Use io.StringIO as an in-memory text file
                    csv_buffer = io.StringIO()
                    writer = csv.writer(csv_buffer)

                    # Write header
                    writer.writerow(
                        [
                            "Row Number",
                            "Name",
                            "Type",
                            "Date",
                            "Reason",
                            "Problematic Value",
                        ]
                    )

                    for item in skipped_data:
                        writer.writerow(
                            [
                                item["row_number"],
                                item["name"],
                                item["type"],
                                item["date"],
                                item["reason"],
                                item["problem_value"],
                            ]
                        )
                    # Create a Django ContentFile from the in-memory buffer
                    file_name = f"skipped_rows_import_{obj.id}.csv"
                    skipped_file = ContentFile(csv_buffer.getvalue().encode("utf-8"))

                    # Save the file to the model field (do not save the model itself yet)
                    obj.skipped_rows_file.save(file_name, skipped_file, save=False)

                # Update import statistics
                obj.processed_rows = row_count
                obj.created_events = created_count
                obj.updated_events = updated_count
                obj.duplicate_events = duplicate_count
                obj.processing_status = "completed"
                obj.error_message = ""  # Clear any previous error
                obj.save()

                # Create success message with all statistics
                message_parts = [
                    f"CSV processing complete! Processed {row_count} rows."
                ]
                if created_count > 0:
                    message_parts.append(f"Created {created_count} new events.")
                if updated_count > 0:
                    message_parts.append(f"Updated {updated_count} existing events.")
                if duplicate_count > 0:
                    message_parts.append(f"Skipped {duplicate_count} duplicates.")
                if skipped_data:
                    message_parts.append(
                        f"Skipped {len(skipped_data)} rows due to errors. "
                        f"See the 'Skipped Rows Log' for details."
                    )

                self.message_user(
                    request,
                    " ".join(message_parts),
                    level=messages.SUCCESS,
                )

        except Exception as e:
            # This will catch errors from opening the file or processing it.
            obj.processing_status = "failed"
            obj.error_message = f"An error occurred during processing: {e}"
            obj.save()
            self.message_user(
                request,
                f"An error occurred during processing: {e}",
                level=messages.ERROR,
            )


@admin.register(NetworkEvent)
class NetworkEventAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "down_time",
        "up_time",
        "date",
        "type",
        "region",
        "reason",
        "duration_display",
        "last_updated",  # Added to show when record was last updated
    ]
    list_filter = ["type", "region", "date", "updated_at"]  # Added updated_at filter
    search_fields = ["name", "reason", "region", "remarks"]  # Added remarks to search
    date_hierarchy = "down_time"
    list_per_page = 50
    readonly_fields = [
        "unique_hash",
        "base_hash",  # Added base_hash as readonly
        "duration_seconds",
        "created_at",
        "updated_at",
    ]

    def duration_display(self, obj):
        return obj.duration()

    duration_display.short_description = "Duration"

    def last_updated(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M") if obj.updated_at else "-"

    last_updated.short_description = "Last Updated"

    # Add actions for bulk operations
    actions = [
        "delete_selected_events",
        "recalculate_hashes",
        "find_potential_updates",  # New action to find records that might need updates
    ]

    def delete_selected_events(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f"Successfully deleted {count} network events.",
            level=messages.SUCCESS,
        )

    delete_selected_events.short_description = "Delete selected events"

    def recalculate_hashes(self, request, queryset):
        count = 0
        for event in queryset:
            event.save()  # This will regenerate both hashes
            count += 1
        self.message_user(
            request,
            f"Successfully recalculated hashes for {count} events.",
            level=messages.SUCCESS,
        )

    recalculate_hashes.short_description = "Recalculate hashes"

    def find_potential_updates(self, request, queryset):
        """Find records that might have updates based on base_hash"""
        base_hashes = queryset.values_list("base_hash", flat=True)

        # Find all events with the same base_hash but different unique_hash
        potential_updates = NetworkEvent.objects.filter(
            base_hash__in=base_hashes
        ).exclude(id__in=queryset.values_list("id", flat=True))

        count = potential_updates.count()
        if count > 0:
            self.message_user(
                request,
                f"Found {count} potential related records that might be updates. "
                f"Check records with matching base fields but different up_time or remarks.",
                level=messages.INFO,
            )
        else:
            self.message_user(
                request,
                "No potential updates found for selected records.",
                level=messages.INFO,
            )

    find_potential_updates.short_description = "Find potential updates"

    # Add custom fieldsets for better organization in detail view
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "down_time", "up_time", "date", "type", "region")},
        ),
        (
            "Details",
            {"fields": ("reason", "solar", "category", "down_count", "remarks")},
        ),
        (
            "System Fields",
            {
                "fields": (
                    "unique_hash",
                    "base_hash",
                    "duration_seconds",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),  # Collapsed by default
            },
        ),
    )
