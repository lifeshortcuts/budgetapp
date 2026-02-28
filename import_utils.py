"""
CSV import utilities for the budget tracker.

Handles parsing bank statement CSVs and mapping bank categories to
our internal subcategory names.
"""

import io
from datetime import datetime

import pandas as pd

# ---------------------------------------------------------------------------
# Bank category → our subcategory name mapping
# Keys are bank category strings (lowercased).
# Values are our subcategory names (lowercased for lookup).
# None means intentionally unmapped → will be marked Uncategorised.
# ---------------------------------------------------------------------------
BANK_TO_SUBCAT = {
    "cafe & coffee":          "dining out",
    "subscriptions":          "subscriptions",
    "groceries":              "groceries",
    "medical":                "gp / prescriptions",
    "media":                  "subscriptions",
    "gym & fitness":          "hobbies",
    "uncategorised":          None,
    "travel expenses":        "miscellaneous",
    "fuel":                   "fuel",
    "restaurants & takeaway": "dining out",
    "insurance":              "health insurance",
    "other shopping":         "miscellaneous",
    "home improvements":      "repairs & maintenance",
    "phone & internet":       "internet",
    "alcohol":                "dining out",
    "clothing & accessories": "clothing",
    "internal transfers":     "credit card payment",
}


def _parse_row(row, subcat_map, uncat_expense_id, uncat_income_id):
    """
    Parse one CSV row dict.
    Returns a transaction dict on success.
    Raises ValueError with a descriptive message on parse failure.
    """
    # --- Date ---
    date_str = str(row.get("Date", "")).strip()
    if not date_str:
        raise ValueError("Missing date")
    try:
        tx_date = datetime.strptime(date_str, "%d %b %y")
    except ValueError:
        raise ValueError(f"Cannot parse date: {date_str!r} (expected format: '28 Feb 26')")

    # --- Amount ---
    raw = str(row.get("Amount", "")).strip().replace(",", "")
    if not raw:
        raise ValueError("Missing amount")
    try:
        raw_amount = float(raw)
    except ValueError:
        raise ValueError(f"Cannot parse amount: {row.get('Amount')!r}")

    flow_type = "expense" if raw_amount < 0 else "income"
    amount = abs(raw_amount)

    # --- Description: prefer Merchant Name, fall back to Transaction Details ---
    merchant = str(row.get("Merchant Name", "")).strip()
    details = str(row.get("Transaction Details", "")).strip()
    description = merchant if merchant else details

    # --- Category mapping ---
    bank_cat_raw = str(row.get("Category", "")).strip()
    bank_cat_key = bank_cat_raw.lower()
    subcat_name = BANK_TO_SUBCAT.get(bank_cat_key, "__not_found__")

    if subcat_name == "__not_found__":
        # Bank category not in our mapping at all
        mapped = False
        category_id = uncat_expense_id if flow_type == "expense" else uncat_income_id
    elif subcat_name is None:
        # Explicitly unmapped (e.g. "Uncategorised")
        mapped = False
        category_id = uncat_expense_id if flow_type == "expense" else uncat_income_id
    else:
        category_id = subcat_map.get(subcat_name)
        if category_id:
            mapped = True
        else:
            # Our DB doesn't have that subcategory (shouldn't happen, but safe)
            mapped = False
            category_id = uncat_expense_id if flow_type == "expense" else uncat_income_id

    return {
        "date": tx_date,
        "amount": amount,
        "flow_type": flow_type,
        "description": description,
        "category_id": category_id,
        "bank_category": bank_cat_raw,
        "mapped": mapped,
        "source": "import",
    }


def parse_csv_file(file_bytes, subcat_map, uncat_expense_id, uncat_income_id):
    """
    Parse an uploaded CSV file.

    Args:
        file_bytes:          raw bytes from st.file_uploader
        subcat_map:          {subcategory_name_lower: category_id}
        uncat_expense_id:    category_id for "Uncategorised" expense placeholder
        uncat_income_id:     category_id for "Other Income" income placeholder

    Returns:
        (valid_rows, failed_rows)
        valid_rows:  list of transaction dicts ready for bulk_import_transactions()
        failed_rows: list of {"row": int, "error": str, "description": str}
    """
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Could not read CSV file: {e}")

    valid_rows = []
    failed_rows = []

    for i, (_, row) in enumerate(df.iterrows()):
        try:
            parsed = _parse_row(row, subcat_map, uncat_expense_id, uncat_income_id)
            valid_rows.append(parsed)
        except ValueError as e:
            # Build a short label for the failed row
            merchant = str(row.get("Merchant Name", "")).strip()
            details = str(row.get("Transaction Details", "")).strip()
            label = merchant or details or f"row {i + 2}"
            failed_rows.append({
                "row": i + 2,   # +2: header row + 1-based index
                "error": str(e),
                "description": label,
            })

    return valid_rows, failed_rows
