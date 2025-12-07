from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date
from enum import Enum


#Master list of book titles
class Title(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True)
    category: str = "Unknown"

#Main Inventory for Admin by batch - each batch can have only 1 title and multiple copies
class Inventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True) #batch id
    title_id: int = Field(foreign_key="title.id")
    MRP: float
    copies_total: int
    entrydate: date = Field(default=date.today())


class Volunteers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    join_date: date = Field(default=date.today())
    is_lead: bool = Field(default=False)

class Stalls(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location: str
    date: date
    lead_id: int = Field(foreign_key="volunteers.id")
    is_closed: bool = Field(default=False)

#Table linking stall to volunteers - many to many
class StallVolunteers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    volunteer_id: int = Field(foreign_key="volunteers.id")
    stall_id: int = Field(foreign_key="stalls.id")

class MovementType(str, Enum):
    ASSIGN = "ASSIGN"
    RETURN = "RETURN"
    SOLD = "SOLD"

#Ledger entry for each movement
class InventoryMovement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="inventory.id")
    volunteer_id: int = Field(foreign_key="volunteers.id")
    stall_id: Optional[int] = Field(default=None, foreign_key="stalls.id")
    movement_type: MovementType = Field(default=MovementType.ASSIGN)
    copies_moved: int = Field(default = 0)
    movement_date: date = Field(default=date.today())
    selling_price_per_copy: float = Field(default=0.0)


