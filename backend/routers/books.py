from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from pydantic import BaseModel
from datetime import date
from backend.database import engine, Session
from backend.models import BookInventory, Volunteers
from collections import Counter


#FastAPI setup
router = APIRouter(prefix="/books")

#Category mapping
Category_dict = {"TWA": "Truth",
                 "Fear": "Fear",
                 "Infinite Potential, Unlimited Success": "Youth",
                 "Stupidity": "Clarity"
}

#API: Add books
class AddBookRequest(BaseModel):
    title: str
    units: int
    MRP: float

@router.post("/add-book")
def add_books(request: AddBookRequest):
    category = Category_dict.get(request.title, "Unknown")
    with Session(engine) as session:
        for i in range(request.units):
            book = BookInventory(title = request.title, MRP = request.MRP, category = category, entrydate = date.today())
            session.add(book)
        session.commit()

    return {"message": f" {request.units} books added"}

#API: Assign books to lead
class AssignBooksRequest(BaseModel):
    volunteer_id: int
    book_title: str
    units: int

@router.post("/assign-books")
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

#View assigned books
@router.get("/assigned_books")
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

