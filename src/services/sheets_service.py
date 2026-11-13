"""
Google Sheets sync service for GeM tender opportunities.
Uses gspread with a Google Service Account to read/write the tracker spreadsheet.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DATA_START_ROW = 5  # Rows 1-3 metadata, row 4 headers, row 5 first data

COLUMN_HEADERS = [
    "#",
    "GeM bid number",
    "Scope of work",
    "Closing date & time",
    "Bid document (link)",
    "Days left",
    "Buyer (Ministry / Dept)",
    "Group",
    "Nikom role",
    "Eligibility",
    "Declared est. value (Rs lakh)",
    "EMD (Rs lakh)",
    "Past experience required (yrs)",
    "Min. avg turnover (Rs lakh)",
    "Remarks",
]


class SheetsService:
    """Read/write Nikom's GeM tender tracker spreadsheet."""

    def __init__(
        self,
        spreadsheet_id: str,
        sheet_gid: int = 0,  # "Live GeM Bids" tab
        credentials_json: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_gid = sheet_gid
        self.gc = self._authorize(credentials_json, credentials_path)
        self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
        self.worksheet = self._get_worksheet_by_gid(sheet_gid)
        logger.info(
            f"Connected to spreadsheet '{self.spreadsheet.title}', "
            f"sheet '{self.worksheet.title}'"
        )

    def _authorize(
        self,
        credentials_json: Optional[str],
        credentials_path: Optional[str],
    ) -> gspread.Client:
        """Authorize with Google using service account credentials."""
        if credentials_json:
            info = json.loads(credentials_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        elif credentials_path:
            creds = Credentials.from_service_account_file(
                credentials_path, scopes=SCOPES
            )
        else:
            env_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
            env_path = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_PATH")
            if env_json:
                info = json.loads(env_json)
                creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            elif env_path:
                creds = Credentials.from_service_account_file(env_path, scopes=SCOPES)
            else:
                raise ValueError(
                    "No Google credentials provided. Set GOOGLE_SHEETS_CREDENTIALS "
                    "(JSON string) or GOOGLE_SHEETS_CREDENTIALS_PATH (file path)."
                )
        return gspread.authorize(creds)

    def _get_worksheet_by_gid(self, gid: int) -> gspread.Worksheet:
        """Find the worksheet matching the given gid."""
        for ws in self.spreadsheet.worksheets():
            if ws.id == gid:
                return ws
        logger.warning(f"No sheet with gid={gid}, falling back to first sheet")
        return self.spreadsheet.sheet1

    def get_existing_bid_numbers(self) -> Set[str]:
        """Return the set of GeM bid numbers already in the sheet (column B)."""
        try:
            col_values = self.worksheet.col_values(2)  # Column B
            bids = set()
            for val in col_values[DATA_START_ROW - 1:]:  # Skip metadata + header rows
                cleaned = val.strip()
                if cleaned and cleaned.startswith("GEM/"):
                    bids.add(cleaned)
            logger.info(f"Found {len(bids)} existing bids in the sheet")
            return bids
        except Exception as e:
            logger.error(f"Failed to read existing bids: {e}")
            return set()

    def get_next_row_number(self) -> int:
        """Get the next serial number for the # column."""
        try:
            col_values = self.worksheet.col_values(1)  # Column A
            max_num = 0
            for val in col_values[DATA_START_ROW - 1:]:
                try:
                    num = int(val.strip())
                    max_num = max(max_num, num)
                except (ValueError, AttributeError):
                    pass
            return max_num + 1
        except Exception:
            return 1

    def append_bids(self, bids: List[Dict[str, Any]]) -> int:
        """
        Append new bid rows to the sheet.
        Each bid dict should have keys matching the column structure.
        Returns count of rows appended.
        """
        if not bids:
            logger.info("No new bids to append")
            return 0

        next_num = self.get_next_row_number()
        rows = []

        for i, bid in enumerate(bids):
            closing_str = bid.get("closing_date", "")
            days_left = self._calculate_days_left(closing_str)

            row = [
                next_num + i,                                    # #
                bid.get("bid_number", ""),                       # GeM bid number
                bid.get("scope", ""),                            # Scope of work
                closing_str,                                     # Closing date & time
                bid.get("doc_link", ""),                         # Bid document (link)
                days_left if days_left is not None else "",      # Days left
                bid.get("buyer", ""),                            # Buyer
                bid.get("group", ""),                            # Group
                bid.get("nikom_role", "Direct bidder"),          # Nikom role
                bid.get("eligibility", "Not started"),           # Eligibility
                bid.get("est_value_lakh", ""),                   # Declared est. value
                bid.get("emd_lakh", ""),                         # EMD
                bid.get("experience_yrs", ""),                   # Past experience
                bid.get("min_turnover_lakh", ""),                # Min. avg turnover
                bid.get("remarks", ""),                          # Remarks
            ]
            rows.append(row)

        try:
            self.worksheet.append_rows(
                rows,
                value_input_option="USER_ENTERED",
                insert_data_option="INSERT_ROWS",
            )
            logger.info(f"Appended {len(rows)} new bids to the sheet")
            return len(rows)
        except Exception as e:
            logger.error(f"Failed to append rows: {e}")
            return 0

    def update_days_left(self) -> int:
        """Recalculate 'Days left' (column F) for all rows based on today's date."""
        try:
            all_data = self.worksheet.get_all_values()
            if len(all_data) < DATA_START_ROW:
                return 0

            updates = []
            for row_idx, row in enumerate(all_data[DATA_START_ROW - 1:], start=DATA_START_ROW):
                if len(row) < 6:
                    continue
                closing_str = row[3]  # Column D (0-indexed: col 3)
                days_left = self._calculate_days_left(closing_str)
                if days_left is not None:
                    updates.append({
                        "range": f"F{row_idx}",
                        "values": [[days_left]],
                    })

            if updates:
                self.worksheet.batch_update(updates, value_input_option="USER_ENTERED")
                logger.info(f"Updated 'Days left' for {len(updates)} rows")
            return len(updates)

        except Exception as e:
            logger.error(f"Failed to update days left: {e}")
            return 0

    def remove_expired_bids(self, grace_days: int = 0) -> int:
        """
        Remove rows where the closing date has passed by more than grace_days.
        Returns count of rows removed.
        """
        try:
            all_data = self.worksheet.get_all_values()
            if len(all_data) < DATA_START_ROW:
                return 0

            rows_to_delete = []
            cutoff = datetime.now() - timedelta(days=grace_days)

            for row_idx, row in enumerate(all_data[DATA_START_ROW - 1:], start=DATA_START_ROW):
                if len(row) < 4:
                    continue
                closing_str = row[3]
                closing_dt = self._parse_closing_date(closing_str)
                if closing_dt and closing_dt < cutoff:
                    rows_to_delete.append(row_idx)

            # Delete in reverse order to maintain row indices
            for row_idx in reversed(rows_to_delete):
                self.worksheet.delete_rows(row_idx)

            if rows_to_delete:
                logger.info(f"Removed {len(rows_to_delete)} expired bids")
            return len(rows_to_delete)

        except Exception as e:
            logger.error(f"Failed to remove expired bids: {e}")
            return 0

    def _calculate_days_left(self, closing_str: str) -> Optional[int]:
        """Calculate days left from a closing date string."""
        closing_dt = self._parse_closing_date(closing_str)
        if not closing_dt:
            return None
        delta = closing_dt - datetime.now()
        return max(0, delta.days)

    def _parse_closing_date(self, date_str: str) -> Optional[datetime]:
        """Parse closing date strings in various formats."""
        if not date_str or not date_str.strip():
            return None

        formats = [
            "%d-%b-%Y %H:%M",       # 12-Nov-2026 18:00
            "%d-%b-%Y %I:%M %p",    # 12-Nov-2026 06:00 PM
            "%d/%m/%Y %H:%M",       # 12/11/2026 18:00
            "%d-%m-%Y %H:%M",       # 12-11-2026 18:00
            "%Y-%m-%dT%H:%M:%S",    # ISO format
            "%d-%b-%Y",             # 12-Nov-2026
            "%d/%m/%Y",             # 12/11/2026
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None
