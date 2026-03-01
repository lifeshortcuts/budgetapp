import streamlit as st

from db.crud import process_recurring_transactions
from db.database import init_db
from db.seed import run_migrations, seed_categories

st.set_page_config(
    page_title="Budget Tracker",
    page_icon="💰",
    layout="wide",
)

init_db()
seed_categories()
run_migrations()

# Process recurring transactions once per browser session
if "recurring_processed" not in st.session_state:
    n = process_recurring_transactions()
    st.session_state.recurring_processed = True
    st.session_state.recurring_count = n

st.title("💰 Budget Tracker")
st.markdown("---")

if st.session_state.get("recurring_count", 0) > 0:
    st.success(f"{st.session_state.recurring_count} recurring transaction(s) were added automatically today.")

st.markdown(
    """
    Welcome! Use the **sidebar** to navigate:

    - **Dashboard** — charts, summaries, and budget tracking
    - **Add Transaction** — record a new income or expense
    - **Transactions** — view, search, edit, or delete entries
    - **Categories** — manage your income and expense categories
    - **Budgets** — set monthly spending targets per category
    - **Recurring** — manage automatic repeat transactions
    """
)

st.info("Your data is stored locally on this computer and never leaves your machine.")
