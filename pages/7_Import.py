import pandas as pd
import streamlit as st

from db.crud import (
    build_subcat_name_map,
    bulk_import_transactions,
    get_uncategorised_ids,
)
from db.database import init_db
from db.seed import ensure_uncategorised_category, seed_categories
from import_utils import BANK_TO_SUBCAT, parse_csv_file

init_db()
seed_categories()
ensure_uncategorised_category()

st.set_page_config(page_title="Import", page_icon="📥", layout="wide")
st.title("📥 Import Transactions")
st.markdown(
    "Upload a bank statement CSV to bulk-import transactions. "
    "Categories are mapped automatically where possible — anything unrecognised "
    "is imported as **Uncategorised** so you can edit it afterwards."
)
st.markdown("---")

# --- Category mapping reference ---
with st.expander("ℹ️ How bank categories are mapped"):
    st.markdown("The following bank category names are recognised and mapped to your subcategories:")
    map_rows = [
        {
            "Bank Category": k.title(),
            "Maps To": v.title() if v else "⚠️ Uncategorised",
        }
        for k, v in BANK_TO_SUBCAT.items()
    ]
    st.dataframe(pd.DataFrame(map_rows), hide_index=True, use_container_width=True)
    st.caption(
        "Any bank category not in this list will also be imported as Uncategorised. "
        "You can edit categories in the Transactions page after importing."
    )

st.markdown("---")

# --- File uploader ---
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

if not uploaded_file:
    st.info("Upload a CSV file to preview and import transactions.")
    st.stop()

# --- Parse the file ---
subcat_map = build_subcat_name_map()
uncat_expense_id, uncat_income_id = get_uncategorised_ids()

try:
    file_bytes = uploaded_file.read()
    valid_rows, failed_rows = parse_csv_file(
        file_bytes, subcat_map, uncat_expense_id, uncat_income_id
    )
except ValueError as e:
    st.error(f"Could not read file: {e}")
    st.stop()

total_rows = len(valid_rows) + len(failed_rows)
mapped_count = sum(1 for r in valid_rows if r["mapped"])
unmapped_count = sum(1 for r in valid_rows if not r["mapped"])

# --- Summary metrics ---
st.markdown("---")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Rows found", total_rows)
m2.metric("Ready to import", len(valid_rows))
m3.metric("Will be Uncategorised", unmapped_count)
m4.metric("Parse errors", len(failed_rows), delta=None if not failed_rows else f"-{len(failed_rows)}")

# --- Handle failures ---
if failed_rows:
    st.markdown("---")
    if len(failed_rows) > 3:
        st.error(
            f"**Import blocked — {len(failed_rows)} rows failed to parse.**\n\n"
            "More than 3 rows have errors. Please check the file and try again. "
            "Nothing has been imported."
        )
        with st.expander(f"Show {len(failed_rows)} errors"):
            for f in failed_rows:
                st.warning(f"Row {f['row']} ({f['description']}): {f['error']}")
        st.stop()
    else:
        st.warning(
            f"**{len(failed_rows)} row(s) could not be parsed and will be skipped.** "
            f"The remaining {len(valid_rows)} transaction(s) will be imported."
        )
        for f in failed_rows:
            st.error(f"Row {f['row']} ({f['description']}): {f['error']}")

if not valid_rows:
    st.error("No valid rows found to import.")
    st.stop()

# --- Preview table ---
st.markdown("---")
st.subheader(f"Preview — {len(valid_rows)} transactions")

# Build reverse map for display: category_id → subcategory name
id_to_subcat = {v: k.title() for k, v in subcat_map.items()}

preview_rows = []
for r in valid_rows:
    if r["mapped"]:
        mapped_label = "✅ " + id_to_subcat.get(r["category_id"], "?")
    else:
        mapped_label = "⚠️ Uncategorised"

    preview_rows.append({
        "Date": r["date"].strftime("%d %b %Y"),
        "Flow": r["flow_type"].capitalize(),
        "Amount (£)": f"£{r['amount']:,.2f}",
        "Description": r["description"],
        "Bank Category": r["bank_category"],
        "Mapped To": mapped_label,
    })

st.dataframe(pd.DataFrame(preview_rows), hide_index=True, use_container_width=True)

income_total = sum(r["amount"] for r in valid_rows if r["flow_type"] == "income")
expense_total = sum(r["amount"] for r in valid_rows if r["flow_type"] == "expense")
pt1, pt2, pt3 = st.columns(3)
pt1.metric("Income rows", f"£{income_total:,.2f}")
pt2.metric("Expense rows", f"£{expense_total:,.2f}")
pt3.metric("Unmapped (need editing)", unmapped_count)

# --- Import button ---
st.markdown("---")

if st.button(
    f"Import {len(valid_rows)} Transactions",
    type="primary",
    use_container_width=True,
):
    count = bulk_import_transactions(valid_rows)
    st.success(f"Successfully imported **{count} transactions**.")
    if failed_rows:
        st.warning(f"{len(failed_rows)} row(s) were skipped due to parse errors.")
    if unmapped_count:
        st.info(
            f"{unmapped_count} transaction(s) were imported as **Uncategorised**. "
            "Go to the **Transactions** page, filter by 'Uncategorised' source or subtype, "
            "and edit their categories."
        )
    st.balloons()
