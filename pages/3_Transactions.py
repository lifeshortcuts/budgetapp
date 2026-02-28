from datetime import date, datetime

import pandas as pd
import streamlit as st

from db.crud import (
    delete_transaction,
    get_parent_categories,
    get_subcategories,
    get_transactions,
    update_transaction,
)
from db.database import init_db
from db.seed import seed_categories

init_db()
seed_categories()

st.set_page_config(page_title="Transactions", page_icon="📋", layout="wide")
st.title("📋 Transactions")

# --- Filters ---
with st.expander("Filters", expanded=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        start_date = st.date_input("From", value=date.today().replace(month=1, day=1))
        end_date = st.date_input("To", value=date.today())
    with fc2:
        flow_filter = st.multiselect(
            "Flow type", ["Income", "Expense"], default=["Income", "Expense"]
        )
        source_filter = st.multiselect(
            "Source", ["manual", "import", "recurring"], default=["manual", "import", "recurring"]
        )
    with fc3:
        search = st.text_input("Search description")
        show_uncat = st.checkbox("Show only Uncategorised", value=False)

start_dt = datetime.combine(start_date, datetime.min.time())
end_dt = datetime.combine(end_date, datetime.max.time())

txs = get_transactions(start_dt, end_dt)

if not txs:
    st.info("No transactions found. Try adjusting the filters or add some transactions.")
    st.stop()

df = pd.DataFrame(txs)
df["date"] = pd.to_datetime(df["date"]).dt.date

# Apply filters
if flow_filter:
    df = df[df["flow_type"].isin([f.lower() for f in flow_filter])]
if source_filter:
    df = df[df["source"].isin(source_filter)]
if show_uncat:
    df = df[df["subtype"] == "Uncategorised"]
if search:
    df = df[df["description"].str.contains(search, case=False, na=False)]

if df.empty:
    st.info("No transactions match the current filters.")
    st.stop()

# --- Display table ---
display_df = df[["id", "date", "flow_type", "type", "subtype", "description", "amount", "source"]].copy()
display_df.columns = ["ID", "Date", "Flow", "Type", "Subtype", "Description", "Amount ($)", "Source"]
display_df["Flow"] = display_df["Flow"].str.capitalize()
display_df["Amount ($)"] = display_df["Amount ($)"].map(lambda x: f"${x:,.2f}")

st.dataframe(display_df, hide_index=True, use_container_width=True)

totals = df.groupby("flow_type")["amount"].sum()
income_total = totals.get("income", 0)
expense_total = totals.get("expense", 0)
m1, m2, m3 = st.columns(3)
m1.metric("Income (filtered)", f"${income_total:,.2f}")
m2.metric("Expenses (filtered)", f"${expense_total:,.2f}")
m3.metric("Net (filtered)", f"${income_total - expense_total:,.2f}")

csv = df.to_csv(index=False)
st.download_button("Export to CSV", csv, "transactions.csv", "text/csv")

st.markdown("---")

# --- Delete ---
with st.expander("🗑️ Delete a Transaction"):
    options = {
        f"#{row['id']} | {row['date']} | ${row['amount']:.2f} | {row['subtype']} | {row['description']}": row[
            "id"
        ]
        for _, row in df.iterrows()
    }
    selected_del = st.selectbox("Select transaction to delete", list(options.keys()), key="del_select")
    confirm = st.checkbox("I confirm I want to delete this transaction")
    if st.button("Delete", type="primary", disabled=not confirm):
        delete_transaction(options[selected_del])
        st.success("Transaction deleted.")
        st.rerun()

st.markdown("---")

# --- Edit ---
with st.expander("✏️ Edit a Transaction"):
    edit_options = {
        f"#{row['id']} | {row['date']} | ${row['amount']:.2f} | {row['subtype']} | {row['description']}": row
        for _, row in df.iterrows()
    }
    selected_edit_key = st.selectbox(
        "Select transaction to edit", list(edit_options.keys()), key="edit_select"
    )
    row = edit_options[selected_edit_key]

    # Flow type radio — triggers cascade
    new_flow_label = st.radio(
        "Income or Expense?",
        ["Expense", "Income"],
        index=0 if row["flow_type"] == "expense" else 1,
        horizontal=True,
        key="edit_flow",
    )
    new_flow = "expense" if new_flow_label == "Expense" else "income"

    new_parents = get_parent_categories(new_flow)
    new_parent_map = {p["name"]: p["id"] for p in new_parents}
    type_options = list(new_parent_map.keys())
    type_idx = type_options.index(row["type"]) if row["type"] in type_options else 0
    new_type = st.selectbox("Category", type_options, index=type_idx, key="edit_type")

    new_subs = get_subcategories(new_parent_map[new_type])
    new_sub_map = {s["name"]: s["id"] for s in new_subs}
    sub_options = list(new_sub_map.keys())
    sub_idx = sub_options.index(row["subtype"]) if row["subtype"] in sub_options else 0
    new_sub = st.selectbox("Subcategory", sub_options, index=sub_idx, key="edit_sub")

    ec1, ec2 = st.columns(2)
    with ec1:
        new_date = st.date_input("Date", value=row["date"], key="edit_date")
        new_amount = st.number_input(
            "Amount ($)", value=float(row["amount"]), min_value=0.01, step=0.01, key="edit_amount"
        )
    with ec2:
        new_desc = st.text_input("Description", value=row["description"], key="edit_desc")
        new_notes = st.text_area("Notes", value=row["notes"], key="edit_notes")

    if st.button("Save Changes", type="primary"):
        update_transaction(
            tx_id=row["id"],
            date=datetime.combine(new_date, datetime.min.time()),
            amount=new_amount,
            category_id=new_sub_map[new_sub],
            description=new_desc,
            notes=new_notes,
        )
        st.success("Transaction updated.")
        st.rerun()
