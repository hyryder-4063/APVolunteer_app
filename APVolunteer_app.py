from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field, create_engine, Session, select, between
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from typing import List
from collections import defaultdict
from collections import Counter
from calendar import monthrange
from datetime import datetime, date

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
    volunteer_lead_id: int = Field(foreign_key="volunteers.id")

class Volunteers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key = True)
    vol_name: str
    vol_join_date: date
    is_lead: bool = Field(default=False)

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

    return {"message": f" {vol.vol_name} added, volunteer ID is {vol.id}"}

#API: Make Volunteer A Lead
@app.post("/make-volunteer-lead")
def make_volunteer_lead(volunteer_id: int):
    with Session(engine) as session:
        vol = session.get(Volunteers, volunteer_id)

        if not vol:
            raise HTTPException(status_code=404, detail="Volunteer ID not found")

        vol.is_lead = True
        session.commit()
        session.refresh(vol)

    return {"message": f"Volunteer {vol.vol_name} (ID {vol.id}) is now a Lead Volunteer"}

#API: Assign books to lead
class AssignBooksRequest(BaseModel):
    volunteer_id: int
    book_title: str
    units: int

@app.post("/assign-books")
def assign_books(request: AssignBooksRequest):
    with Session(engine) as session:
        #Check if volunteer is a lead volunteer
        vol = session.exec(select(Volunteers).where(Volunteers.id == request.volunteer_id)).first()
        if not vol:
            raise HTTPException(status_code=404, detail="Volunteer not found")
        if vol.is_lead == False:
             raise HTTPException(status_code=403, detail="Volunteer is not  lead volunteer and books can only be assigned to a lead volunteer")
        else:
            # Check how many unsold copies of that title are there
            unsold_books = session.exec(
                select(BookInventory).where(BookInventory.status == "Unsold",
                                            BookInventory.title == request.book_title)).all()
            available = len(unsold_books)

            if available == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No unsold copies available for this title"
                )

            books_to_assign = unsold_books[:min(available, request.units)]
            for book in books_to_assign:
                book.status = "Assigned" #assign units to volunteer
                book.assigned_volunteer_id = request.volunteer_id

        session.commit()
        return {"message": f" {len(books_to_assign)} copies of {request.book_title} were available and have been assigned to volunteer {request.volunteer_id}"}

#API: Add and close a stall
class SoldBook(BaseModel):
    book_id: int
    book_selling_price: float

class StallRequest(BaseModel):
    stall_location: str
    stall_date: date
    volunteer_ids: List[int]
    volunteer_lead_id : int
    sold_books: List[SoldBook]

@app.post("/add-close-stall")
def add_close_stall(request: StallRequest):
    with Session(engine) as session:

        # 1. Validate volunteers exist
        valid_vol_ids = session.exec(
            select(Volunteers.volunteer_id)
            .where(Volunteers.volunteer_id.in_(request.volunteer_ids))
        ).all()

        if len(valid_vol_ids) != len(request.volunteer_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more volunteer IDs do not exist"
            )

        #2. Create a new stall

        stall = Stalls(stall_location = request.stall_location, stall_date = request.stall_date)
        session.add(stall)
        session.flush()

        #3. Add volunteers
        for volunteer in  request.volunteer_ids:
            link = StallVolunteers(stall_id = stall.id, volunteer_id = volunteer)
            session.add(link)

        stall.volunteer_lead_id = request.volunteer_lead_id

        #4. Update books sold at the stall
        sold_books_details = []
        for b in request.sold_books:
            book = session.get(BookInventory, b.book_id)
            if not book:
                raise HTTPException(status_code=404, detail="Book ID not found")

            #update book inventory row
            book.status = "Sold"
            book.stall_id = stall.id
            book.sold_date = stall.stall_date
            book.selling_price = b.book_selling_price
            sold_books_details.append({"book_id": b.book_id, "book title": book.title, "book selling price": book.selling_price})

        session.commit()
        session.refresh(stall)

    return {
        "message": "Stall added and closed succesffuly",
        "stall id": stall.id,
        "stall location": stall.stall_location,
        "stall date": stall.stall_date,
        "lead volunteer": stall.volunteer_lead_id,
        "volunteers": request.volunteer_ids,
        "sold books": sold_books_details
    }

#Inventory summary
@app.get("/inventory_summary")
def inventory_summary():
    session = Session(engine)
    books = session.exec(select(BookInventory)).all()

    inventory_summary = defaultdict(lambda: {"Unsold": 0, "Assigned": 0, "Sold": 0})

    for book in books:
        inventory_summary[book.title][book.status] += 1
    return inventory_summary


#View assigned books
@app.get("/assigned_books")
def assigned_books(volunteer_id: int):
    with Session(engine) as session:
        assigned_books = session.exec(
            select(BookInventory)
            .where(BookInventory.status == "Assigned")
            .where(BookInventory.assigned_volunteer_id == volunteer_id)
            ).all()

    summary = Counter()

    for book in assigned_books:
        summary[book.title] += 1
    return dict(summary)

#View single stall performance
@app.get("/stall-performance")
def stall_performance(stall_id: int):
    with Session(engine) as session:
        #1. Fetch stall
        stall = session.get(Stalls, stall_id)
        if not stall:
            raise HTTPException(status_code=404, detail="Stall not found")

        #2. Fetch all books assigned to this stall
        stall_books = session.exec(
            select(BookInventory)
            .where(BookInventory.stall_id == stall_id)
        ).all()

        #3. Get performance
        summary = defaultdict(lambda: {"Assigned": 0, "Sold": 0, "Revenue": 0})

        for book in stall_books:
            summary[book.title]["Assigned"] += 1

            if book.status == "Sold":
                summary[book.title]["Sold"] +=1
                summary[book.title]["Revenue"] += (book.selling_price or 0)

        stall_volunteers = session.exec(
            select(StallVolunteers)
            .where(StallVolunteers.stall_id == stall_id)
        ).all()

        volunteer_ids = [sv.volunteer_id for sv in stall_volunteers]
        volunteers = session.exec(
            select(Volunteers) .where(Volunteers.id.in_(volunteer_ids))).all()

        volunteer_names = [v.vol_name for v in volunteers]


        stall_info = {"stall_id": stall.id, "stall_location": stall.stall_location, "stall_date": stall.stall_date}
        return {"stall_info": stall_info, "volunteers": volunteer_names, "performance:": summary}

#View admin monthly dashboard
@app.get("/admin-monthly-performance")
def monthly_performance(month: str):
    try:
        year, mon = map(int, month.split("-"))
        start_date = date(year, mon, 1)
        end_date = date(year, mon, monthrange(year, mon)[1])
    except:
        raise HTTPException(status_code=404, detail="Month must be in format YYYY-MM")

    with Session(engine) as session:

        #1. Fetch stalls in that month
        stalls = session.exec(select(Stalls).where(Stalls.stall_date.between(start_date, end_date))).all()
        if not stalls:
            raise HTTPException(status_code=404, detail=f"no Stall found in month {month}")

        stall_bookcount = {}
        stall_revenue = {}
        monthly_revenue = 0.0
        total_books_sold = 0

        # 2. Count books sold in each stall
        for stall in stalls:


            stall_books = session.exec(
                select(BookInventory)
                .where(
                    (BookInventory.stall_id == stall.id) &
                    (BookInventory.status == "Sold")
                )
            ).all()

            stall_bookcount [stall.id] = len(stall_books)
            total_books_sold += len(stall_books)
            stall_revenue[stall.id] = 0.0

            for stall_book in stall_books:
                stall_revenue [stall.id] += stall_book.selling_price or 0
                monthly_revenue += stall_book.selling_price or 0


        # 3. Categorize stalls by books sold and revenue

        count1 = sum(1 for v in stall_bookcount.values() if v < 10)
        count2 = sum(1 for v in stall_bookcount.values() if 10 <= v <= 20)
        count3 = sum(1 for v in stall_bookcount.values() if v > 20)

        countrev1 = sum(1 for v in stall_revenue.values() if v < 2000)
        countrev2 = sum(1 for v in stall_revenue.values() if 2000 <= v <= 5000)
        countrev3 = sum(1 for v in stall_revenue.values() if v > 5000)


        # 4. Volunteer stats for the month

        vol_month = defaultdict(int)
        stall_volunteers = session.exec(
            select(StallVolunteers).where(
                StallVolunteers.stall_id.in_([s.id for s in stalls])
            )
        ).all()

        for sv in stall_volunteers:
            vol_month[sv.volunteer_id] += 1

        vol_bucket_1 = sum(1 for c in vol_month.values() if c == 1)
        vol_bucket_2_3 = sum(1 for c in vol_month.values() if 2 <= c <= 3)
        vol_bucket_3plus = sum(1 for c in vol_month.values() if c > 3)

        # 5. Final output

        return {
            "month": month,
            "total_stalls": len(stalls),
            "total_books_sold": total_books_sold,
            "stall_bookssoldcat": {
                "<10 books": count1,
                "10-20 books": count2,
                ">20 books": count3
            },
            "stall_revcat": {
                "<2K": countrev1,
                "2-5K": countrev2,
                ">5K": countrev3,
            },
            "vol_attendance": {
                "1": vol_bucket_1,
                "2-3": vol_bucket_2_3,
                ">3": vol_bucket_3plus,
            }

        }










