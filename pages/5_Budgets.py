import pandas as pd
import streamlit as st

from db.crud import delete_budget, get_all_categories, get_budgets, set_budget
from db.database import init_db
from db.seed import seed_categories

init_db()
seed_categories()

st.set_page_config(page_title="Budgets", page_icon="🎯", layout="wide")
st.title("🎯 Budget Settings")
st.markdown(
    "Set a **monthly** budget for any category or subcategory. "
    "The dashboard will show how you're tracking month-by-month and year-to-date."
)
st.markdown("---")

# --- Current budgets ---
budgets = get_budgets()

if budgets:
    st.subheader("Current Budgets")
    display = []
    for b in budgets:
        display.append({
            "Level": "Subtype" if b["is_subtype"] else "Type",
            "Flow": b["flow_type"].capitalize(),
            "Type": b["type"],
            "Category": b["category"],
            "Monthly ($)": f"${b['monthly_amount']:,.2f}",
            "Annual ($)": f"${b['annual_amount']:,.2f}",
            "Notes": b["notes"],
        })
    st.dataframe(pd.DataFrame(display), hide_index=True, use_container_width=True)

    expense_budgets = [b for b in budgets if b["flow_type"] == "expense"]
    if expense_budgets:
        total_monthly = sum(b["monthly_amount"] for b in expense_budgets)
        m1, m2 = st.columns(2)
        m1.metric("Total Monthly Expense Budget", f"${total_monthly:,.2f}")
        m2.metric("Total Annual Expense Budget", f"${total_monthly * 12:,.2f}")
else:
    st.info("No budgets set yet. Add your first one below.")

st.markdown("---")

# --- Set / update a budget ---
st.subheader("Set or Update a Budget")

all_cats = get_all_categories()
cat_options = {}
for c in all_cats:
    level = "subtype" if c["parent_id"] else "type"
    label = f"[{c['flow_type'].upper()}] {c['name']} ({level})"
    cat_options[label] = c

selected_cat_key = st.selectbox("Category", list(cat_options.keys()))
selected_cat = cat_options[selected_cat_key]

# Pre-populate if a budget already exists for this category
existing = next((b for b in budgets if b["category_id"] == selected_cat["id"]), None)

col1, col2 = st.columns(2)
with col1:
    current_val = float(existing["monthly_amount"]) if existing else 1.0
    monthly_amount = st.number_input(
        "Monthly Budget ($)",
        value=current_val,
        min_value=0.01,
        step=10.0,
        format="%.2f",
    )
    st.caption(f"Annual equivalent: **${monthly_amount * 12:,.2f}**")
with col2:
    notes = st.text_input("Notes (optional)", value=existing["notes"] if existing else "")

if existing:
    st.caption(
        f"A budget of ${existing['monthly_amount']:,.2f}/month already exists for **{selected_cat['name']}**. "
        "Saving will update it."
    )

if st.button("Save Budget", type="primary"):
    set_budget(selected_cat["id"], monthly_amount, notes)
    action = "Updated" if existing else "Set"
    st.success(
        f"{action}: **${monthly_amount:,.2f}/month** for {selected_cat['name']} "
        f"(${monthly_amount * 12:,.2f}/year)"
    )
    st.rerun()

# --- Remove a budget ---
if budgets:
    st.markdown("---")
    with st.expander("🗑️ Remove a Budget"):
        budget_options = {
            f"{b['category']} ({b['type']}) — ${b['monthly_amount']:,.2f}/month": b["id"]
            for b in budgets
        }
        selected_to_del = st.selectbox("Select budget to remove", list(budget_options.keys()))
        if st.button("Remove Budget", type="primary"):
            delete_budget(budget_options[selected_to_del])
            st.success("Budget removed.")
            st.rerun()
