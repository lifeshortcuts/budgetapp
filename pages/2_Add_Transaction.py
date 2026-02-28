from datetime import date, datetime

import streamlit as st

from db.crud import add_transaction, get_parent_categories, get_subcategories
from db.database import init_db
from db.seed import seed_categories

init_db()
seed_categories()

st.set_page_config(page_title="Add Transaction", page_icon="➕", layout="wide")
st.title("➕ Add Transaction")
st.markdown("---")

# --- Step 1: Category selection (outside form so dropdowns cascade) ---
col1, col2, col3 = st.columns(3)

with col1:
    flow_type = st.radio("Income or Expense?", ["Expense", "Income"], horizontal=True)

flow = "expense" if flow_type == "Expense" else "income"
parents = get_parent_categories(flow)
parent_map = {p["name"]: p["id"] for p in parents}

with col2:
    selected_type_name = st.selectbox("Category", list(parent_map.keys()))

subs = get_subcategories(parent_map[selected_type_name]) if selected_type_name else []
sub_map = {s["name"]: s["id"] for s in subs}

with col3:
    selected_sub_name = st.selectbox("Subcategory", list(sub_map.keys()))

st.markdown("---")

# --- Step 2: Transaction details form ---
with st.form("transaction_details", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        tx_date = st.date_input("Date", value=date.today())
        amount = st.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
    with col2:
        description = st.text_input("Description", placeholder="e.g. Tesco, Monthly salary...")
        notes = st.text_area("Notes (optional)", height=100, placeholder="Any extra detail...")

    submitted = st.form_submit_button("Save Transaction", type="primary", use_container_width=True)

if submitted:
    cat_id = sub_map.get(selected_sub_name)
    if not cat_id:
        st.error("Please select a subcategory.")
    else:
        add_transaction(
            date=datetime.combine(tx_date, datetime.min.time()),
            amount=amount,
            category_id=cat_id,
            description=description,
            notes=notes,
        )
        st.success(
            f"Saved: ${amount:.2f} — {selected_sub_name}"
            + (f" ({description})" if description else "")
        )
