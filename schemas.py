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

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

# Funding discovery app schemas

class Fundingopportunity(BaseModel):
    """
    Funding opportunities collection
    Collection name: "fundingopportunity"
    """
    title: str = Field(..., description="Opportunity title")
    agency: str = Field(..., description="Issuing agency or funder")
    description: str = Field(..., description="Full text description of the opportunity")
    categories: List[str] = Field(default_factory=list, description="Tags/categories like AI, health, climate, education")
    eligibility: List[str] = Field(default_factory=list, description="Who is eligible: nonprofit, startup, small business, researcher, student, etc.")
    region: Optional[str] = Field(None, description="Geographic scope such as US, EU, Global, State-CA")
    deadline: Optional[str] = Field(None, description="Deadline date or cadence")
    amount: Optional[str] = Field(None, description="Funding amount or range")
    url: Optional[HttpUrl] = Field(None, description="Official link")

class Projectquery(BaseModel):
    """
    Saved user queries
    Collection name: "projectquery"
    """
    description: str = Field(..., description="Natural language project description from the user")
    sector: Optional[str] = Field(None, description="Optional sector hint")
    region: Optional[str] = Field(None, description="Optional region preference")

# Example schemas retained for reference (not used by the app)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
