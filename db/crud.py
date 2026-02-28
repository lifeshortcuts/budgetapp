from datetime import datetime

from .database import get_session
from .models import Category, Transaction


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
        tx = Transaction(
            date=date,
            amount=amount,
            category_id=category_id,
            description=description,
            notes=notes,
            source=source,
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
                    "flow_type": cat.flow_type,
                    "category_id": tx.category_id,
                    "source": tx.source,
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
