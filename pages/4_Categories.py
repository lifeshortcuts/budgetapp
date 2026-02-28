import streamlit as st

from db.crud import add_category, delete_category, get_all_categories, get_parent_categories
from db.database import init_db
from db.seed import seed_categories

init_db()
seed_categories()

st.set_page_config(page_title="Categories", page_icon="🗂️", layout="wide")
st.title("🗂️ Categories")
st.markdown("Manage the categories and subcategories used to classify transactions.")
st.markdown("---")

cats = get_all_categories()
parents = [c for c in cats if c["parent_id"] is None]
children = [c for c in cats if c["parent_id"] is not None]

# --- Category tree display ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Income")
    for p in [x for x in parents if x["flow_type"] == "income"]:
        with st.expander(f"📂 {p['name']}"):
            subs = [c for c in children if c["parent_id"] == p["id"]]
            if subs:
                for s in subs:
                    st.write(f"└ {s['name']}")
            else:
                st.caption("No subtypes yet.")

with col2:
    st.subheader("Expenses")
    for p in [x for x in parents if x["flow_type"] == "expense"]:
        with st.expander(f"📂 {p['name']}"):
            subs = [c for c in children if c["parent_id"] == p["id"]]
            if subs:
                for s in subs:
                    st.write(f"└ {s['name']}")
            else:
                st.caption("No subtypes yet.")

st.markdown("---")

# --- Add a Category Type ---
with st.expander("➕ Add a Category Type"):
    with st.form("add_type_form"):
        new_type_name = st.text_input("Name (e.g. 'Hobbies')")
        new_type_flow = st.radio("Flow", ["Expense", "Income"], horizontal=True)
        if st.form_submit_button("Add Type"):
            if new_type_name.strip():
                add_category(
                    new_type_name.strip(),
                    "expense" if new_type_flow == "Expense" else "income",
                )
                st.success(f"Added '{new_type_name}' as a {new_type_flow} type.")
                st.rerun()
            else:
                st.error("Please enter a name.")

# --- Add a Subtype ---
with st.expander("➕ Add a Subtype"):
    with st.form("add_subtype_form"):
        all_parents = get_parent_categories()
        parent_options = {f"{p['name']} ({p['flow_type']})": p for p in all_parents}
        selected_parent_key = st.selectbox("Parent Category", list(parent_options.keys()))
        new_sub_name = st.text_input("Subtype Name (e.g. 'Gym')")
        if st.form_submit_button("Add Subtype"):
            if new_sub_name.strip():
                parent = parent_options[selected_parent_key]
                add_category(new_sub_name.strip(), parent["flow_type"], parent["id"])
                st.success(f"Added '{new_sub_name}' under '{parent['name']}'.")
                st.rerun()
            else:
                st.error("Please enter a name.")

# --- Delete a Category ---
with st.expander("🗑️ Delete a Category"):
    all_cats = get_all_categories()
    if all_cats:
        cat_options = {
            f"{c['name']} ({'subtype' if c['parent_id'] else 'type'}, {c['flow_type']})": c["id"]
            for c in all_cats
        }
        selected_cat = st.selectbox("Select category to delete", list(cat_options.keys()))
        if st.button("Delete Category", type="primary"):
            success, msg = delete_category(cat_options[selected_cat])
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
