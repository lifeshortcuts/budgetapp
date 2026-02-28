from datetime import date

import streamlit as st

from db.crud import (
    add_recurring_transaction,
    delete_recurring,
    get_parent_categories,
    get_recurring_transactions,
    get_subcategories,
    toggle_recurring,
)
from db.database import init_db
from db.seed import seed_categories

init_db()
seed_categories()

st.set_page_config(page_title="Recurring", page_icon="🔄", layout="wide")
st.title("🔄 Recurring Transactions")
st.markdown(
    "Transactions added here are **automatically created** each time the app opens, "
    "based on their schedule. The app will catch up if it hasn't been opened for a while."
)
st.markdown("---")

# --- Existing recurring transactions ---
recurrings = get_recurring_transactions()

if recurrings:
    st.subheader("Scheduled Transactions")
    for rec in recurrings:
        flow_icon = "📈" if rec["flow_type"] == "income" else "📉"
        status_label = "✅ Active" if rec["active"] else "⏸️ Paused"
        label = (
            f"{flow_icon} {rec['description'] or rec['category']} — "
            f"${rec['amount']:,.2f} {rec['frequency'].lower()} | {status_label}"
        )
        with st.expander(label):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.write(f"**Category:** {rec['type']} → {rec['category']}")
                st.write(f"**Amount:** ${rec['amount']:,.2f}")
                st.write(f"**Frequency:** {rec['frequency']}")
            with c2:
                st.write(f"**Start date:** {rec['start_date']}")
                st.write(f"**End date:** {rec['end_date'] if rec['end_date'] else 'No end date'}")
                st.write(f"**Next run:** {rec['next_run_date']}")
            with c3:
                pause_label = "⏸️ Pause" if rec["active"] else "▶️ Resume"
                if st.button(pause_label, key=f"toggle_{rec['id']}"):
                    toggle_recurring(rec["id"])
                    st.rerun()
                if st.button("🗑️ Delete", key=f"del_{rec['id']}"):
                    delete_recurring(rec["id"])
                    st.success("Deleted.")
                    st.rerun()
else:
    st.info("No recurring transactions set up yet. Add one below.")

st.markdown("---")

# --- Add new recurring transaction ---
st.subheader("Add a Recurring Transaction")

# Cascading category selection (outside form so dropdowns update live)
col1, col2, col3 = st.columns(3)
with col1:
    flow_type = st.radio("Income or Expense?", ["Expense", "Income"], horizontal=True, key="rec_flow")

flow = "expense" if flow_type == "Expense" else "income"
parents = get_parent_categories(flow)
parent_map = {p["name"]: p["id"] for p in parents}

with col2:
    selected_type = st.selectbox("Category", list(parent_map.keys()), key="rec_type")

subs = get_subcategories(parent_map[selected_type]) if selected_type else []
sub_map = {s["name"]: s["id"] for s in subs}

with col3:
    selected_sub = st.selectbox("Subcategory", list(sub_map.keys()), key="rec_sub")

st.markdown("")

with st.form("add_recurring_form", clear_on_submit=True):
    fc1, fc2 = st.columns(2)
    with fc1:
        rec_amount = st.number_input("Amount ($)", min_value=0.01, step=1.0, format="%.2f")
        rec_desc = st.text_input("Description", placeholder="e.g. Monthly rent, Netflix...")
        rec_freq = st.selectbox(
            "Frequency", ["Monthly", "Weekly", "Fortnightly", "Quarterly", "Annually"]
        )
    with fc2:
        rec_start = st.date_input("Start Date", value=date.today())
        rec_has_end = st.checkbox("Set an end date")
        rec_end = st.date_input(
            "End Date",
            value=date.today().replace(year=date.today().year + 1),
            disabled=not rec_has_end,
        )
        rec_notes = st.text_area("Notes (optional)", height=68)

    if st.form_submit_button("Add Recurring Transaction", type="primary", use_container_width=True):
        cat_id = sub_map.get(selected_sub)
        if not cat_id:
            st.error("Please select a subcategory.")
        else:
            add_recurring_transaction(
                amount=rec_amount,
                category_id=cat_id,
                description=rec_desc,
                notes=rec_notes,
                frequency=rec_freq,
                start_date=rec_start,
                end_date=rec_end if rec_has_end else None,
            )
            st.success(
                f"Added: ${rec_amount:,.2f} {rec_freq.lower()} — {selected_sub}"
                + (f" ({rec_desc})" if rec_desc else "")
            )
            st.info(
                "The first transaction(s) will be created automatically next time you open the app home page."
            )
