from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    flow_type = Column(String(10), nullable=False)  # 'income' or 'expense'

    parent = relationship("Category", remote_side=[id], backref="subtypes")
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(200), default="")
    notes = Column(Text, default="")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    source = Column(String(20), default="manual")  # 'manual' or 'import'
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, unique=True)
    monthly_amount = Column(Float, nullable=False)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category")


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    description = Column(String(200), default="")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    notes = Column(Text, default="")
    frequency = Column(String(20), nullable=False)  # Weekly/Fortnightly/Monthly/Quarterly/Annually
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)       # None = runs indefinitely
    next_run_date = Column(DateTime, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category")
