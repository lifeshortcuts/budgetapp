from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from db.crud import get_budget_vs_actual, get_transactions
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
k1.metric("Total Income", f"${total_income:,.2f}")
k2.metric("Total Expenses", f"${total_expenses:,.2f}")
k3.metric("Net", f"${net:,.2f}", delta=f"${net:,.2f}")
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
    fig1.update_layout(margin=dict(t=20, b=20), legend_title_text="", yaxis_title="$")
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
    labels={"date": "Date", "cumulative_net": "Cumulative Net ($)"},
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
    top["Total"] = top["Total"].map(lambda x: f"${x:,.2f}")
    st.dataframe(top, hide_index=True, use_container_width=True)

# --- Budget Tracker ---
st.markdown("---")
st.subheader("🎯 Budget Tracker")

budget_data = get_budget_vs_actual(today.year, today.month)

if not budget_data:
    st.info("No budgets set yet. Go to the **Budgets** page to set monthly targets.")
else:
    tab_month, tab_year = st.tabs(
        [f"This Month ({today.strftime('%B %Y')})", f"This Year ({today.year})"]
    )

    with tab_month:
        st.caption("🟢 ≤75% used  🟡 75–100% used  🔴 over budget")
        rows = []
        for b in budget_data:
            pct = b["monthly_pct"]
            status = "🟢" if pct <= 75 else ("🟡" if pct <= 100 else "🔴")
            # Parent budget row
            rows.append({
                " ": status,
                "Category": b["category"],
                "Budget": f"${b['monthly_budget']:,.2f}",
                "Actual": f"${b['monthly_actual']:,.2f}",
                "Remaining": f"${b['monthly_remaining']:,.2f}",
                "% Used": f"{pct:.0f}%",
            })
            # Subcategory detail rows (indented, no budget/remaining columns)
            for s in b["subcategories"]:
                rows.append({
                    " ": "",
                    "Category": f"  └ {s['name']}",
                    "Budget": "",
                    "Actual": f"${s['monthly_actual']:,.2f}",
                    "Remaining": "",
                    "% Used": "",
                })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        month_budget_total = sum(b["monthly_budget"] for b in budget_data if b["flow_type"] == "expense")
        month_actual_total = sum(b["monthly_actual"] for b in budget_data if b["flow_type"] == "expense")
        mb1, mb2, mb3 = st.columns(3)
        mb1.metric("Total Budget (month)", f"${month_budget_total:,.2f}")
        mb2.metric("Total Actual (month)", f"${month_actual_total:,.2f}")
        mb3.metric("Remaining (month)", f"${month_budget_total - month_actual_total:,.2f}")

    with tab_year:
        st.caption(
            f"YTD Budget = Monthly Budget × {today.month} months elapsed  |  "
            "Projected Annual extrapolates your current spend rate"
        )
        rows = []
        for b in budget_data:
            diff = b["ytd_diff"]
            status = "🟢" if diff <= 0 else ("🟡" if diff <= b["ytd_budget"] * 0.1 else "🔴")
            # Parent budget row
            rows.append({
                " ": status,
                "Category": b["category"],
                "Annual Budget": f"${b['annual_budget']:,.2f}",
                f"YTD Budget ({today.month}m)": f"${b['ytd_budget']:,.2f}",
                "YTD Actual": f"${b['ytd_actual']:,.2f}",
                "vs YTD Budget": f"${diff:,.2f}",
                "Projected Annual": f"${b['projected_annual']:,.2f}" if b["projected_annual"] else "—",
            })
            # Subcategory detail rows
            for s in b["subcategories"]:
                rows.append({
                    " ": "",
                    "Category": f"  └ {s['name']}",
                    "Annual Budget": "",
                    f"YTD Budget ({today.month}m)": "",
                    "YTD Actual": f"${s['ytd_actual']:,.2f}",
                    "vs YTD Budget": "",
                    "Projected Annual": "",
                })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        annual_budget_total = sum(b["annual_budget"] for b in budget_data if b["flow_type"] == "expense")
        ytd_actual_total = sum(b["ytd_actual"] for b in budget_data if b["flow_type"] == "expense")
        projected_total = sum(b["projected_annual"] for b in budget_data if b["flow_type"] == "expense")
        yb1, yb2, yb3 = st.columns(3)
        yb1.metric("Annual Budget (expenses)", f"${annual_budget_total:,.2f}")
        yb2.metric("YTD Actual (expenses)", f"${ytd_actual_total:,.2f}")
        yb3.metric("Projected Annual", f"${projected_total:,.2f}")
