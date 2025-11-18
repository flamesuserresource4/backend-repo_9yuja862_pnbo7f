"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# Budgeting app schemas

class Category(BaseModel):
    """
    Categories collection schema
    Collection name: "category"
    """
    name: str = Field(..., description="Category name, e.g., Rent, Food, Investment")
    emoji: Optional[str] = Field(None, description="Emoji/icon for the category, e.g., 🏠 🍔 💼")

class Allocation(BaseModel):
    category_id: str = Field(..., description="Reference to category _id as string")
    target: float = Field(..., ge=0, description="Target amount for the month")

class Budget(BaseModel):
    """
    Monthly budget plan
    Collection name: "budget"
    """
    month: str = Field(..., description="Month in YYYY-MM format")
    income: float = Field(..., ge=0, description="Planned monthly income")
    allocations: List[Allocation] = Field(default_factory=list, description="List of category targets")

class Expense(BaseModel):
    """
    Expense entries for tracking actual spending
    Collection name: "expense"
    """
    month: str = Field(..., description="Month in YYYY-MM format")
    category_id: str = Field(..., description="Reference to category _id as string")
    amount: float = Field(..., ge=0, description="Expense amount")
    note: Optional[str] = Field(None, description="Optional note/description")
    spent_on: Optional[date] = Field(None, description="Date of the expense")
