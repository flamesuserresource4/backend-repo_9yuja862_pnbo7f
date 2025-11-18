import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Category, Budget, Expense, Allocation

app = FastAPI(title="Budget Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to convert ObjectId to str in responses

def serialize_doc(doc: Dict[str, Any]):
    if not doc:
        return doc
    if doc.get("_id"):
        doc["id"] = str(doc.pop("_id"))
    return doc


@app.get("/")
def read_root():
    return {"message": "Budget Tracker Backend is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Categories
@app.post("/api/categories")
def create_category(category: Category):
    category_dict = category.model_dump()
    inserted_id = create_document("category", category_dict)
    doc = db["category"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)

@app.get("/api/categories")
def list_categories():
    docs = get_documents("category")
    return [serialize_doc(d) for d in docs]


# Budgets
class BudgetCreate(BaseModel):
    month: str
    income: float
    allocations: List[Allocation]

@app.post("/api/budgets")
def create_budget(budget: BudgetCreate):
    # Upsert by month: replace existing budget for that month
    month = budget.month
    db["budget"].delete_many({"month": month})
    inserted_id = create_document("budget", budget.model_dump())
    doc = db["budget"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)

@app.get("/api/budgets/{month}")
def get_budget(month: str):
    doc = db["budget"].find_one({"month": month})
    if not doc:
        raise HTTPException(status_code=404, detail="Budget not found for month")
    return serialize_doc(doc)


# Expenses
class ExpenseCreate(BaseModel):
    month: str
    category_id: str
    amount: float
    note: Optional[str] = None

@app.post("/api/expenses")
def add_expense(expense: ExpenseCreate):
    inserted_id = create_document("expense", expense.model_dump())
    doc = db["expense"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)

@app.get("/api/expenses/{month}")
def list_expenses(month: str):
    docs = db["expense"].find({"month": month})
    return [serialize_doc(d) for d in docs]


# Summary endpoint
@app.get("/api/summary/{month}")
def summary(month: str):
    budget_doc = db["budget"].find_one({"month": month})
    allocations_map: Dict[str, float] = {}
    income = 0.0
    if budget_doc:
        income = float(budget_doc.get("income", 0))
        for alloc in budget_doc.get("allocations", []):
            allocations_map[alloc.get("category_id")] = float(alloc.get("target", 0))

    # Sum expenses by category
    pipeline = [
        {"$match": {"month": month}},
        {"$group": {"_id": "$category_id", "spent": {"$sum": "$amount"}}}
    ]
    spent_by_cat = {d["_id"]: float(d["spent"]) for d in db["expense"].aggregate(pipeline)}

    # Attach category details
    categories = {str(c["_id"]): c for c in db["category"].find()}

    categories_summary = []
    for cat_id, cat in categories.items():
        target = allocations_map.get(cat_id, 0.0)
        spent = spent_by_cat.get(cat_id, 0.0)
        categories_summary.append({
            "id": cat_id,
            "name": cat.get("name"),
            "emoji": cat.get("emoji"),
            "target": target,
            "spent": spent,
            "progress": (spent / target * 100) if target > 0 else None
        })

    total_target = sum(allocations_map.values())
    total_spent = sum(spent_by_cat.values())

    return {
        "month": month,
        "income": income,
        "total_target": total_target,
        "total_spent": total_spent,
        "remaining": max(income - total_spent, 0.0),
        "categories": categories_summary
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
