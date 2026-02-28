import streamlit as st

from db.database import init_db
from db.seed import seed_categories

st.set_page_config(
    page_title="Budget Tracker",
    page_icon="💰",
    layout="wide",
)

# One-time setup — safe to call every run (create_all is idempotent)
init_db()
seed_categories()

st.title("💰 Budget Tracker")
st.markdown("---")

st.markdown(
    """
    Welcome! Use the **sidebar** to navigate:

    - **Dashboard** — charts and summaries of your finances
    - **Add Transaction** — record a new income or expense
    - **Transactions** — view, search, edit, or delete entries
    - **Categories** — manage your income and expense categories
    """
)

st.info("Your data is stored locally on this computer and never leaves your machine.")
