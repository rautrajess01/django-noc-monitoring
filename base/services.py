# base/services.py

import hashlib
import logging
from datetime import datetime

import gspread
from django.conf import settings
from django.utils.timezone import make_aware

from .models import NetworkEvent

logger = logging.getLogger(__name__)

def sync_network_events_from_google_sheet():
    """
    Connects to Google Sheets, fetches data, and syncs it with the NetworkEvent model.

    Returns:
        dict: A summary of the operation with counts for created, updated,
              duplicate, and skipped records.
    Raises:
        Exception: If there's an error connecting to Google Sheets or if
                   required columns are missing.
    """
    # --- 1. Connect and Fetch Data ---
    try:
        gc = gspread.service_account(filename=settings.GOOGLE_CREDENTIALS_FILE)
        spreadsheet = gc.open_by_key(settings.GOOGLE_SHEET_KEY)
        worksheet = spreadsheet.worksheet("Total")
        all_rows = worksheet.get_all_values()
        logger.info("Successfully connected to Google Sheet.")
    except Exception as e:
        logger.error(f"Error connecting to Google Sheets: {e}")
        raise  # Re-raise the exception to be handled by the caller

    if not all_rows:
        return {"created": 0, "updated": 0, "duplicates": 0, "skipped": 0, "message": "Sheet is empty."}

    headers = [h.strip() for h in all_rows[0]]
    records_as_lists = all_rows[1:]
    logger.info(f"Found {len(records_as_lists)} data rows in the Google Sheet.")

    # --- 2. Validate Headers ---
    try:
        idx_map = {h: i for i, h in enumerate(headers)}
        required_cols = [
            "MPLS/Switch", "Full SOLAR POP", "Down Time", "Up Time", "Type",
            "Region", "Reason/Issue", "Date", "Remarks(from mail if any)", "Category",
        ]
        for col in required_cols:
            if col not in idx_map:
                raise ValueError(f"Required column '{col}' not found in sheet.")
    except ValueError as e:
        logger.fatal(f"Header validation failed: {e}")
        raise

    # --- 3. Process Rows ---
    created_count = 0
    updated_count = 0
    duplicate_count = 0
    skipped_count = 0

    def parse_datetime(value):
        if not value or not isinstance(value, str):
            return None
        try:
            dt = datetime.strptime(value.strip(), "%m/%d/%Y %H:%M:%S")
            return make_aware(dt)
        except (ValueError, TypeError):
            return None

    for row_list in records_as_lists:
        if len(row_list) < len(headers):
            row_list.extend([""] * (len(headers) - len(row_list)))

        event_data = {col: row_list[idx_map[col]].strip() for col in required_cols}

        if not event_data["MPLS/Switch"]:
            skipped_count += 1
            continue

        down_time = parse_datetime(event_data["Down Time"])
        if not down_time:
            skipped_count += 1
            continue

        # This `base_hash` logic seems to be unused in the create_or_update call.
        # I'll keep it here in case your model method uses it implicitly.
        base_data_string = "|".join([
            event_data["MPLS/Switch"].lower(),
            str(down_time),
            event_data["Type"].lower(),
            event_data["Region"].lower(),
        ])
        base_hash = hashlib.sha256(base_data_string.encode("utf-8")).hexdigest()

        model_data = {
            "name": event_data["MPLS/Switch"],
            "down_time": down_time,
            "up_time": parse_datetime(event_data["Up Time"]),
            "date": event_data["Date"],
            "type": event_data["Type"],
            "region": event_data["Region"],
            "reason": event_data["Reason/Issue"],
            "solar": event_data["Full SOLAR POP"],
            "remarks": event_data["Remarks(from mail if any)"],
            "category": event_data["Category"],
            "down_count": 0,  # Default, as not in sheet
        }
        
        # We need to assume your NetworkEvent model has this custom manager method.
        # If not, you can implement it as shown in the bonus section below.
        event, created, updated = NetworkEvent.create_or_update_event(**model_data)

        if created:
            created_count += 1
        elif updated:
            updated_count += 1
        else:
            duplicate_count += 1

    return {
        "created": created_count,
        "updated": updated_count,
        "duplicates": duplicate_count,
        "skipped": skipped_count,
    }
