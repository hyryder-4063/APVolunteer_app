from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field, create_engine, Session, select
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from typing import List
from collections import defaultdict

#Category mapping
Category_dict = {"TWA": "Truth",
                 "Fear": "Fear",
                 "Infinite Potential, Unlimited Success": "Youth",
                 "Stupidity": "Clarity"
}

#Database model

class BookInventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key = True)
    title: str
    category: str
    MRP: float
    entrydate: date
    status: str = Field(default = "Unsold")
    assigned_volunteer_id: Optional[int] = None
    sold_date: Optional[date] = None
    selling_price: Optional[float] = None
    stall_id: Optional[int] = None

class Stalls(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key = True)
    stall_location: str
    stall_date: date

class Volunteers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key = True)
    vol_name: str
    vol_join_date: date

class StallVolunteers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key = True)
    volunteer_id: int = Field(foreign_key="volunteers.id")
    stall_id: int = Field(foreign_key="stalls.id")

#Database engine
engine = create_engine('sqlite:///books.db')
SQLModel.metadata.create_all(engine)

#FastAPI setup

app = FastAPI()

#Homepage route
@app.get("/")
def home():
    return {"message": "Book Inventory API is running"}

#API: Add books
class AddBookRequest(BaseModel):
    title: str
    units: int
    MRP: float

@app.post("/add-book")
def add_books(request: AddBookRequest):
    category = Category_dict.get(request.title, "Unknown")
    with Session(engine) as session:
        for i in range(request.units):
            book = BookInventory(title = request.title, MRP = request.MRP, category = category, entrydate = date.today())
            session.add(book)
        session.commit()

    return {"message": f" {request.units} books added"}

#API: Add New Volunteer
@app.post("/add-volunteer")
def add_volunteer(vol_name: str, vol_join_date: date):

    with Session(engine) as session:
        vol = Volunteers(vol_name = vol_name, vol_join_date = vol_join_date)
        session.add(vol)
        session.commit()
        session.refresh(vol)

    return {"message": f" {vol_name} added, volunteer ID is {vol.id}"}

#API: Add stall
class StallRequest(BaseModel):
    stall_location: str
    stall_date: date


@app.post("/add-stall")
def add_stalls(request: StallRequest):
    with Session(engine) as session:
        stall = Stalls(stall_location = request.stall_location, stall_date = request.stall_date)
        session.add(stall)
        session.commit()
        session.refresh(stall)
    return {"message": f" stall id: {stall.id} at {stall.stall_location} on {stall.stall_date} added"}

#API: Assign volunteers to a stall

class Assign_VolunteerRequest(BaseModel):
    stall_id: int
    volunteer_ids: List[int]

@app.post("/assign-volunteer")
def assign_volunteer(request: Assign_VolunteerRequest):
    with Session(engine) as session:
        stall = session.get(Stalls, request.stall_id)
        if not stall:
            raise HTTPException(status_code=404, detail="stall ID not found")

        for volunteer in  request.volunteer_ids:
            link = StallVolunteers(stall_id = request.stall_id, volunteer_id = volunteer)
            session.add(link)

        session.commit()
    return {"message": f" Volunteer: {request.volunteer_ids} added to Stall {request.stall_id}"}


class AssignBooksRequest(BaseModel):
    volunteer_id: int
    book_title: str
    units: int

@app.post("/assign-books")
def assign_books(request: AssignBooksRequest):
    session = Session(engine)
    #Check how many unsold copies of that title are there
    unsold_books = session.exec(
        select(BookInventory).where(BookInventory.status == "Unsold"). where(BookInventory.title == request.book_title)).all()
    available = len(unsold_books)

    books_to_assign = unsold_books[:min(available, request.units)]

    for book in books_to_assign:
        book.status = "Assigned" #assign units to volunteer
        book.assigned_volunteer_id = request.volunteer_id

    session.commit()
    return {"message": f" {min(request.units, available)} units of {request.book_title} were available and have been assigned to you"}


class SoldBooksRequest(BaseModel):
    stall_id: int
    book_id: int
    selling_price: float

#Sold books
@app.post("/sold-books")
def sold_books(request: SoldBooksRequest):
    with Session(engine) as session:
        #Check stall exists
        stall = session.get(Stalls, request.stall_id)
        if not stall:
            raise HTTPException(status_code=404, detail="Stall not found")

        #fetch book
        book = session.get(BookInventory, request.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book ID not found")

        #update book
        book.status = "Sold"
        book.stall_id = stall.id
        book.sold_date = stall.stall_date
        book.selling_price = request.selling_price

        session.commit()

    return {"message": f" Stall {request.stall_id} sold Book ID {(request.book_id)} of title: {book.title}"}

#Inventory summary
@app.get("/inventory_summary")
def inventory_summary():
    session = Session(engine)
    books = session.exec(select(BookInventory)).all()

    inventory_summary = defaultdict(lambda: {"Unsold": 0, "Assigned": 0, "Sold": 0})

    for book in books:
        inventory_summary[book.title][book.status] += 1
    return inventory_summary















