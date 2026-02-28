from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from db.crud import get_transactions
from db.database import init_db
from db.seed import seed_categories

init_db()
seed_categories()

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")

# --- Date range selector ---
col1, col2 = st.columns([1, 3])
with col1:
    range_option = st.selectbox(
        "Time period",
        ["This month", "Last 3 months", "Last 6 months", "This year", "All time", "Custom"],
    )

today = date.today()

if range_option == "This month":
    start, end = today.replace(day=1), today
elif range_option == "Last 3 months":
    start = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
    end = today
elif range_option == "Last 6 months":
    start = (today.replace(day=1) - timedelta(days=150)).replace(day=1)
    end = today
elif range_option == "This year":
    start, end = today.replace(month=1, day=1), today
elif range_option == "All time":
    start, end = None, None
else:
    with col2:
        c1, c2 = st.columns(2)
        start = c1.date_input("From", value=today.replace(day=1))
        end = c2.date_input("To", value=today)

start_dt = datetime.combine(start, datetime.min.time()) if start else None
end_dt = datetime.combine(end, datetime.max.time()) if end else None

txs = get_transactions(start_dt, end_dt)

if not txs:
    st.info("No transactions found for the selected period. Add some transactions to see your dashboard.")
    st.stop()

df = pd.DataFrame(txs)
df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.to_period("M").astype(str)
df["signed_amount"] = df.apply(
    lambda r: r["amount"] if r["flow_type"] == "income" else -r["amount"], axis=1
)

income_df = df[df["flow_type"] == "income"]
expense_df = df[df["flow_type"] == "expense"]

total_income = income_df["amount"].sum()
total_expenses = expense_df["amount"].sum()
net = total_income - total_expenses

# --- KPI Cards ---
st.markdown("---")
k1, k2, k3 = st.columns(3)
k1.metric("Total Income", f"£{total_income:,.2f}")
k2.metric("Total Expenses", f"£{total_expenses:,.2f}")
k3.metric("Net", f"£{net:,.2f}", delta=f"£{net:,.2f}")
st.markdown("---")

# --- Row 1: Monthly bar + Expenses donut ---
chart1, chart2 = st.columns(2)

with chart1:
    st.subheader("Monthly Income vs Expenses")
    monthly = df.groupby(["month", "flow_type"])["amount"].sum().reset_index()
    monthly.columns = ["Month", "Type", "Amount"]
    monthly["Type"] = monthly["Type"].str.capitalize()
    fig1 = px.bar(
        monthly,
        x="Month",
        y="Amount",
        color="Type",
        barmode="group",
        color_discrete_map={"Income": "#2ecc71", "Expense": "#e74c3c"},
    )
    fig1.update_layout(margin=dict(t=20, b=20), legend_title_text="", yaxis_title="£")
    st.plotly_chart(fig1, use_container_width=True)

with chart2:
    st.subheader("Expenses by Type")
    if expense_df.empty:
        st.info("No expense data for this period.")
    else:
        by_type = expense_df.groupby("type")["amount"].sum().reset_index()
        fig2 = px.pie(by_type, values="amount", names="type", hole=0.45)
        fig2.update_layout(margin=dict(t=20, b=20))
        st.plotly_chart(fig2, use_container_width=True)

# --- Row 2: Cumulative net line ---
st.subheader("Cumulative Net Over Time")
df_sorted = df.sort_values("date").copy()
df_sorted["cumulative_net"] = df_sorted["signed_amount"].cumsum()
fig3 = px.line(
    df_sorted,
    x="date",
    y="cumulative_net",
    labels={"date": "Date", "cumulative_net": "Cumulative Net (£)"},
)
fig3.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
fig3.update_traces(line_color="#3498db")
fig3.update_layout(margin=dict(t=20, b=20))
st.plotly_chart(fig3, use_container_width=True)

# --- Row 3: Top expense categories ---
st.subheader("Top Expense Categories")
if not expense_df.empty:
    top = expense_df.groupby(["type", "subtype"])["amount"].sum().reset_index()
    top.columns = ["Type", "Subtype", "Total"]
    top = top.sort_values("Total", ascending=False).head(10)
    top["Total"] = top["Total"].map(lambda x: f"£{x:,.2f}")
    st.dataframe(top, hide_index=True, use_container_width=True)
