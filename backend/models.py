from sqlalchemy import ForeignKey
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date



class BookTitle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True)
    category: str = "Unknown"

class BookBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    book_title: str = Field(foreign_key="booktitle.title")
    MRP: float
    entrydate: date = Field(default=date.today())

class BookInventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="bookbatch.id")
    title: str = Field(foreign_key=  "booktitle.title")
    status: str = Field(default="Unsold")
    assigned_volunteer_id: Optional[int] = Field(default=None, foreign_key="volunteers.id")
    sold_date: Optional[date] = None
    selling_price: Optional[float] = None
    stall_id: Optional[int] = Field(default=None, foreign_key="stalls.id")

class Volunteers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vol_name: str
    vol_join_date: date
    is_lead: bool = Field(default=False)

class Stalls(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    stall_location: str
    stall_date: date
    volunteer_lead_id: int = Field(foreign_key="volunteers.id")

class StallVolunteers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    volunteer_id: int = Field(foreign_key="volunteers.id")
    stall_id: int = Field(foreign_key="stalls.id")
