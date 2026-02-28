import calendar
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from .database import get_session
from .models import Budget, Category, RecurringTransaction, Transaction


def get_parent_categories(flow_type=None):
    session = get_session()
    try:
        q = session.query(Category).filter(Category.parent_id.is_(None))
        if flow_type:
            q = q.filter(Category.flow_type == flow_type)
        return [
            {"id": c.id, "name": c.name, "flow_type": c.flow_type}
            for c in q.order_by(Category.name).all()
        ]
    finally:
        session.close()


def get_subcategories(parent_id):
    session = get_session()
    try:
        cats = (
            session.query(Category)
            .filter(Category.parent_id == parent_id)
            .order_by(Category.name)
            .all()
        )
        return [{"id": c.id, "name": c.name, "flow_type": c.flow_type} for c in cats]
    finally:
        session.close()


def get_all_categories():
    session = get_session()
    try:
        cats = session.query(Category).order_by(Category.flow_type, Category.name).all()
        return [
            {"id": c.id, "name": c.name, "parent_id": c.parent_id, "flow_type": c.flow_type}
            for c in cats
        ]
    finally:
        session.close()


def add_transaction(date, amount, category_id, description, notes="", source="manual"):
    session = get_session()
    try:
        cat = session.query(Category).filter(Category.id == category_id).first()
        tx = Transaction(
            date=date,
            amount=amount,
            category_id=category_id,
            description=description,
            notes=notes,
            source=source,
            flow_type=cat.flow_type if cat else None,
        )
        session.add(tx)
        session.commit()
    finally:
        session.close()


def get_transactions(start_date=None, end_date=None):
    session = get_session()
    try:
        q = session.query(Transaction, Category).join(Category)
        if start_date:
            q = q.filter(Transaction.date >= start_date)
        if end_date:
            q = q.filter(Transaction.date <= end_date)
        rows = q.order_by(Transaction.date.desc()).all()

        result = []
        for tx, cat in rows:
            parent = (
                session.query(Category).filter(Category.id == cat.parent_id).first()
                if cat.parent_id
                else None
            )
            result.append(
                {
                    "id": tx.id,
                    "date": tx.date,
                    "amount": tx.amount,
                    "description": tx.description or "",
                    "notes": tx.notes or "",
                    "subtype": cat.name,
                    "type": parent.name if parent else cat.name,
                    "flow_type": tx.flow_type or cat.flow_type,
                    "category_id": tx.category_id,
                    "source": tx.source or "manual",
                }
            )
        return result
    finally:
        session.close()


def delete_transaction(tx_id):
    session = get_session()
    try:
        tx = session.query(Transaction).filter(Transaction.id == tx_id).first()
        if tx:
            session.delete(tx)
            session.commit()
    finally:
        session.close()


def update_transaction(tx_id, date, amount, category_id, description, notes):
    session = get_session()
    try:
        tx = session.query(Transaction).filter(Transaction.id == tx_id).first()
        if tx:
            tx.date = date
            tx.amount = amount
            tx.category_id = category_id
            tx.description = description
            tx.notes = notes
            session.commit()
    finally:
        session.close()


def add_category(name, flow_type, parent_id=None):
    session = get_session()
    try:
        cat = Category(name=name, flow_type=flow_type, parent_id=parent_id)
        session.add(cat)
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Budget functions
# ---------------------------------------------------------------------------

def get_budgets():
    session = get_session()
    try:
        rows = session.query(Budget, Category).join(Category, Budget.category_id == Category.id).all()
        result = []
        for b, cat in rows:
            parent = (
                session.query(Category).filter(Category.id == cat.parent_id).first()
                if cat.parent_id
                else None
            )
            result.append({
                "id": b.id,
                "category_id": b.category_id,
                "category": cat.name,
                "type": parent.name if parent else cat.name,
                "is_subtype": cat.parent_id is not None,
                "flow_type": cat.flow_type,
                "monthly_amount": b.monthly_amount,
                "annual_amount": b.monthly_amount * 12,
                "notes": b.notes or "",
            })
        return sorted(result, key=lambda x: (x["flow_type"], x["type"], x["category"]))
    finally:
        session.close()


def set_budget(category_id, monthly_amount, notes=""):
    session = get_session()
    try:
        existing = session.query(Budget).filter(Budget.category_id == category_id).first()
        if existing:
            existing.monthly_amount = monthly_amount
            existing.notes = notes
        else:
            session.add(Budget(category_id=category_id, monthly_amount=monthly_amount, notes=notes))
        session.commit()
    finally:
        session.close()


def delete_budget(budget_id):
    session = get_session()
    try:
        b = session.query(Budget).filter(Budget.id == budget_id).first()
        if b:
            session.delete(b)
            session.commit()
    finally:
        session.close()


def get_budget_vs_actual(year, month):
    session = get_session()
    try:
        month_start = datetime(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        month_end = datetime(year, month, last_day, 23, 59, 59)
        year_start = datetime(year, 1, 1)

        # Aggregate actuals by category
        monthly_actuals = dict(
            session.query(Transaction.category_id, func.sum(Transaction.amount))
            .filter(Transaction.date >= month_start, Transaction.date <= month_end)
            .group_by(Transaction.category_id)
            .all()
        )
        ytd_actuals = dict(
            session.query(Transaction.category_id, func.sum(Transaction.amount))
            .filter(Transaction.date >= year_start, Transaction.date <= month_end)
            .group_by(Transaction.category_id)
            .all()
        )

        rows = session.query(Budget, Category).join(Category, Budget.category_id == Category.id).all()
        result = []
        for b, cat in rows:
            parent = (
                session.query(Category).filter(Category.id == cat.parent_id).first()
                if cat.parent_id
                else None
            )
            monthly_actual = monthly_actuals.get(cat.id, 0.0)
            ytd_actual = ytd_actuals.get(cat.id, 0.0)
            ytd_budget = b.monthly_amount * month
            annual_budget = b.monthly_amount * 12
            projected = (ytd_actual / month * 12) if month > 0 and ytd_actual > 0 else 0.0

            result.append({
                "category_id": cat.id,
                "category": cat.name,
                "type": parent.name if parent else cat.name,
                "flow_type": cat.flow_type,
                "is_subtype": cat.parent_id is not None,
                # Monthly
                "monthly_budget": b.monthly_amount,
                "monthly_actual": monthly_actual,
                "monthly_remaining": b.monthly_amount - monthly_actual,
                "monthly_pct": (monthly_actual / b.monthly_amount * 100) if b.monthly_amount > 0 else 0.0,
                # Annual / YTD
                "annual_budget": annual_budget,
                "ytd_budget": ytd_budget,
                "ytd_actual": ytd_actual,
                "ytd_diff": ytd_actual - ytd_budget,
                "projected_annual": projected,
            })
        return sorted(result, key=lambda x: (x["flow_type"], x["type"], x["category"]))
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Recurring transaction functions
# ---------------------------------------------------------------------------

def _next_date(d, frequency):
    freq = frequency.lower()
    if freq == "weekly":
        return d + timedelta(weeks=1)
    elif freq == "fortnightly":
        return d + timedelta(weeks=2)
    elif freq == "monthly":
        return d + relativedelta(months=1)
    elif freq == "quarterly":
        return d + relativedelta(months=3)
    elif freq == "annually":
        return d + relativedelta(years=1)
    return d + timedelta(days=30)


def process_recurring_transactions():
    """Create any overdue recurring transactions. Returns count created."""
    session = get_session()
    today = date.today()
    created = 0
    try:
        due = (
            session.query(RecurringTransaction)
            .filter(
                RecurringTransaction.active == True,
                RecurringTransaction.next_run_date <= datetime.combine(today, datetime.min.time()),
            )
            .all()
        )
        for rec in due:
            run_date = rec.next_run_date.date()
            while run_date <= today:
                if rec.end_date and run_date > rec.end_date.date():
                    rec.active = False
                    break
                cat = session.query(Category).filter(Category.id == rec.category_id).first()
                session.add(Transaction(
                    date=datetime.combine(run_date, datetime.min.time()),
                    amount=rec.amount,
                    category_id=rec.category_id,
                    description=rec.description or f"Recurring ({rec.frequency})",
                    notes=rec.notes or "",
                    source="recurring",
                    flow_type=cat.flow_type if cat else None,
                ))
                created += 1
                run_date = _next_date(run_date, rec.frequency)
            if rec.active:
                rec.next_run_date = datetime.combine(run_date, datetime.min.time())
        session.commit()
        return created
    finally:
        session.close()


def get_recurring_transactions():
    session = get_session()
    try:
        rows = (
            session.query(RecurringTransaction, Category)
            .join(Category)
            .order_by(RecurringTransaction.active.desc(), RecurringTransaction.description)
            .all()
        )
        result = []
        for rec, cat in rows:
            parent = (
                session.query(Category).filter(Category.id == cat.parent_id).first()
                if cat.parent_id
                else None
            )
            result.append({
                "id": rec.id,
                "amount": rec.amount,
                "description": rec.description or "",
                "category": cat.name,
                "type": parent.name if parent else cat.name,
                "flow_type": cat.flow_type,
                "frequency": rec.frequency,
                "start_date": rec.start_date.date(),
                "end_date": rec.end_date.date() if rec.end_date else None,
                "next_run_date": rec.next_run_date.date(),
                "active": rec.active,
                "category_id": rec.category_id,
            })
        return result
    finally:
        session.close()


def add_recurring_transaction(amount, category_id, description, notes, frequency, start_date, end_date=None):
    session = get_session()
    try:
        session.add(RecurringTransaction(
            amount=amount,
            category_id=category_id,
            description=description,
            notes=notes,
            frequency=frequency,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.min.time()) if end_date else None,
            next_run_date=datetime.combine(start_date, datetime.min.time()),
            active=True,
        ))
        session.commit()
    finally:
        session.close()


def toggle_recurring(rec_id):
    session = get_session()
    try:
        rec = session.query(RecurringTransaction).filter(RecurringTransaction.id == rec_id).first()
        if rec:
            rec.active = not rec.active
            session.commit()
            return rec.active
    finally:
        session.close()


def delete_recurring(rec_id):
    session = get_session()
    try:
        rec = session.query(RecurringTransaction).filter(RecurringTransaction.id == rec_id).first()
        if rec:
            session.delete(rec)
            session.commit()
    finally:
        session.close()


def delete_category(cat_id):
    session = get_session()
    try:
        tx_count = (
            session.query(Transaction).filter(Transaction.category_id == cat_id).count()
        )
        if tx_count > 0:
            return False, f"Cannot delete: {tx_count} transaction(s) use this category."

        sub_count = session.query(Category).filter(Category.parent_id == cat_id).count()
        if sub_count > 0:
            return False, f"Cannot delete: {sub_count} subtype(s) exist. Delete subtypes first."

        cat = session.query(Category).filter(Category.id == cat_id).first()
        if cat:
            session.delete(cat)
            session.commit()
        return True, "Deleted successfully."
    finally:
        session.close()


# ---------------------------------------------------------------------------
# CSV import helpers
# ---------------------------------------------------------------------------

def build_subcat_name_map():
    """Returns {subcategory_name_lowercase: category_id} for all subcategories."""
    session = get_session()
    try:
        children = session.query(Category).filter(Category.parent_id.isnot(None)).all()
        return {c.name.lower(): c.id for c in children}
    finally:
        session.close()


def get_uncategorised_ids():
    """Returns (expense_uncat_id, income_fallback_id) for rows that cannot be mapped."""
    session = get_session()
    try:
        expense_uncat = session.query(Category).filter(
            Category.name == "Uncategorised", Category.flow_type == "expense"
        ).first()
        income_other = session.query(Category).filter(
            Category.name == "Other Income", Category.flow_type == "income"
        ).first()
        return (
            expense_uncat.id if expense_uncat else None,
            income_other.id if income_other else None,
        )
    finally:
        session.close()


def bulk_import_transactions(valid_rows):
    """Insert a list of pre-validated transaction dicts. Returns count inserted."""
    session = get_session()
    try:
        for row in valid_rows:
            session.add(Transaction(
                date=row["date"],
                amount=row["amount"],
                category_id=row["category_id"],
                description=row["description"],
                notes="",
                source="import",
                flow_type=row["flow_type"],
            ))
        session.commit()
        return len(valid_rows)
    finally:
        session.close()
