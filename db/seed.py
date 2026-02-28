from .database import get_session
from .models import Category

SEED_DATA = [
    {
        "name": "Income",
        "flow_type": "income",
        "subtypes": ["Salary / Wages", "Investment Income", "Pension / Benefits", "Other Income"],
    },
    {
        "name": "Housing",
        "flow_type": "expense",
        "subtypes": ["Rent", "Mortgage", "Council Tax", "Home Insurance", "Repairs & Maintenance"],
    },
    {
        "name": "Food",
        "flow_type": "expense",
        "subtypes": ["Groceries", "Dining Out", "Takeaways"],
    },
    {
        "name": "Transport",
        "flow_type": "expense",
        "subtypes": ["Fuel", "Public Transport", "Parking", "Car Insurance", "Car Maintenance"],
    },
    {
        "name": "Utilities",
        "flow_type": "expense",
        "subtypes": ["Electricity", "Gas", "Water", "Internet", "Phone / Mobile"],
    },
    {
        "name": "Healthcare",
        "flow_type": "expense",
        "subtypes": ["GP / Prescriptions", "Dental", "Optician", "Health Insurance"],
    },
    {
        "name": "Entertainment",
        "flow_type": "expense",
        "subtypes": ["Streaming Services", "Events & Cinema", "Hobbies", "Subscriptions"],
    },
    {
        "name": "Personal",
        "flow_type": "expense",
        "subtypes": ["Clothing", "Personal Care", "Gifts"],
    },
    {
        "name": "Financial",
        "flow_type": "expense",
        "subtypes": ["Savings Transfer", "Loan Repayment", "Credit Card Payment"],
    },
    {
        "name": "Other",
        "flow_type": "expense",
        "subtypes": ["Miscellaneous", "Uncategorised"],
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
            other = session.query(Category).filter(
                Category.name == "Other",
                Category.flow_type == "expense",
                Category.parent_id.is_(None),
            ).first()
            if other:
                session.add(Category(name="Uncategorised", flow_type="expense", parent_id=other.id))
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
