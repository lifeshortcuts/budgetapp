from .database import get_session
from .models import Budget, Category, RecurringTransaction, Transaction

SEED_DATA = [
    {
        "name": "Income",
        "flow_type": "income",
        "subtypes": ["Superannuation", "Joffre St", "Gifts", "Wages", "Other", "Interest", "Tax Returns"],
    },
    {
        "name": "Personal",
        "flow_type": "expense",
        "subtypes": ["Weekly", "Clothing", "Shoes", "Haircuts", "Kindle", "Donations", "Tax", "Cash", "Super"],
    },
    {
        "name": "Home",
        "flow_type": "expense",
        "subtypes": ["Council Rates", "Electricity", "Water", "Insurance", "Gardening", "R&M", "Pest Control", "Sundry Items"],
    },
    {
        "name": "Tech",
        "flow_type": "expense",
        "subtypes": ["Mobile Phone", "TV Subscriptions", "Internet"],
    },
    {
        "name": "Cars",
        "flow_type": "expense",
        "subtypes": ["Insurance", "Rego", "Running"],
    },
    {
        "name": "Health",
        "flow_type": "expense",
        "subtypes": ["Insurance", "Medical", "Dental", "Optical", "Pharmacy", "Physio"],
    },
    {
        "name": "Household",
        "flow_type": "expense",
        "subtypes": ["Groceries", "Refreshments", "Uncategorised"],
    },
    {
        "name": "Entertainment",
        "flow_type": "expense",
        "subtypes": ["Coffee", "Dining Out", "Lotto"],
    },
    {
        "name": "Travel",
        "flow_type": "expense",
        "subtypes": ["Overseas", "Short Trips", "Sydney", "NZ"],
    },
    {
        "name": "Gifts",
        "flow_type": "expense",
        "subtypes": ["Christmas", "Birthdays", "Other"],
    },
    {
        "name": "Capital Purchases",
        "flow_type": "expense",
        "subtypes": ["Household Items", "Carport", "Car"],
    },
    {
        "name": "Joffre St",
        "flow_type": "expense",
        "subtypes": ["Insurance", "R&M"],
    },
]


def ensure_uncategorised_category():
    """Ensure the Uncategorised subcategory exists — safe to call on existing databases."""
    session = get_session()
    try:
        existing = session.query(Category).filter(
            Category.name == "Uncategorised", Category.flow_type == "expense"
        ).first()
        if not existing:
            household = session.query(Category).filter(
                Category.name == "Household",
                Category.flow_type == "expense",
                Category.parent_id.is_(None),
            ).first()
            if household:
                session.add(Category(name="Uncategorised", flow_type="expense", parent_id=household.id))
                session.commit()
    finally:
        session.close()


def seed_categories():
    session = get_session()
    try:
        if session.query(Category).count() > 0:
            return
        for item in SEED_DATA:
            parent = Category(name=item["name"], flow_type=item["flow_type"], parent_id=None)
            session.add(parent)
            session.flush()
            for sub_name in item["subtypes"]:
                session.add(
                    Category(name=sub_name, flow_type=item["flow_type"], parent_id=parent.id)
                )
        session.commit()
    finally:
        session.close()


def _do_migrate():
    """Replace old generic categories with the custom category structure."""
    session = get_session()
    try:
        # 1. Wipe budgets and recurring transactions
        session.query(Budget).delete()
        session.query(RecurringTransaction).delete()
        session.flush()

        # 2. Delete all old categories (SQLite doesn't enforce FKs by default)
        session.query(Category).delete()
        session.flush()

        # 3. Seed new categories
        for item in SEED_DATA:
            parent = Category(name=item["name"], flow_type=item["flow_type"], parent_id=None)
            session.add(parent)
            session.flush()
            for sub_name in item["subtypes"]:
                session.add(
                    Category(name=sub_name, flow_type=item["flow_type"], parent_id=parent.id)
                )
        session.flush()

        # 4. Get new fallback category IDs
        household = session.query(Category).filter(
            Category.name == "Household", Category.parent_id.is_(None)
        ).first()
        new_uncat = session.query(Category).filter(
            Category.name == "Uncategorised",
            Category.parent_id == household.id,
        ).first() if household else None

        income_parent = session.query(Category).filter(
            Category.name == "Income", Category.parent_id.is_(None)
        ).first()
        income_other = session.query(Category).filter(
            Category.name == "Other",
            Category.parent_id == income_parent.id,
        ).first() if income_parent else None

        # 5. Reassign all existing transactions to fallback categories
        if new_uncat:
            session.query(Transaction).filter(
                Transaction.flow_type == "expense"
            ).update({"category_id": new_uncat.id}, synchronize_session=False)
            session.query(Transaction).filter(
                Transaction.flow_type.is_(None)
            ).update({"category_id": new_uncat.id}, synchronize_session=False)

        if income_other:
            session.query(Transaction).filter(
                Transaction.flow_type == "income"
            ).update({"category_id": income_other.id}, synchronize_session=False)

        session.commit()
    finally:
        session.close()


def run_migrations():
    """Run one-time category migration if the old generic categories are detected."""
    session = get_session()
    try:
        # If no categories exist yet, seed_categories() will handle it — nothing to migrate
        if session.query(Category).count() == 0:
            return
        # If "Joffre St" parent already exists, new structure is in place
        joffre = session.query(Category).filter(
            Category.name == "Joffre St",
            Category.parent_id.is_(None),
        ).first()
        if joffre:
            return
    finally:
        session.close()

    # Old categories detected — migrate to new structure
    _do_migrate()
