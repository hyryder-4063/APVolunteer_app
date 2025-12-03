from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Field
from pydantic import BaseModel
from datetime import date
from backend.database import engine, Session
from backend.models import BookInventory, BookTitle, Volunteers, BookBatch
from collections import Counter

# ----- FastAPI setup -----
router = APIRouter(prefix="/books")


# --------------------------------------------------------
#               ADD NEW BOOK TITLE
# --------------------------------------------------------
class AddNewTitleRequest(BaseModel):
    title: str
    category: str


@router.post("/add-new-title")
def add_new_title(request: AddNewTitleRequest):
    with Session(engine) as session:
        existing = session.exec(select(BookTitle).where(BookTitle.title == request.title)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Book title already exists")

        book_title = BookTitle(title=request.title, category=request.category)
        session.add(book_title)
        session.commit()
        session.refresh(book_title)

        return {"message": f"Book title '{request.title}' added successfully"}


# --------------------------------------------------------
#               ADD BOOKS TO INVENTORY
# --------------------------------------------------------
class AddBookRequest(BaseModel):
    batch_id: Optional[int] = Field(default=None)
    title: str
    units: int
    MRP: float
    entrydate: date = Field(default=date.today())
    category: Optional[str] = None


@router.post("/add-book")
def add_books(request: AddBookRequest):
    with Session(engine) as session:

        # -----------------------------
        # CASE 1: Existing batch
        # -----------------------------
        if request.batch_id is not None:
            batch = session.get(BookBatch, request.batch_id)
            if not batch:
                raise HTTPException(status_code=400, detail="Batch not found")

            # DO NOT touch entrydate or MRP
            # Just add units
            for _ in range(request.units):
                book = BookInventory(
                    batch_id=batch.id,
                    title=request.title,
                )
                session.add(book)

            session.commit()
            return {
                "message": f"{request.units} books added to existing batch {batch.id}"
            }

        # -----------------------------
        # CASE 2: Create NEW batch
        # -----------------------------
        else:
            batch = BookBatch(
                book_title=request.title,
                MRP=request.MRP,
                entrydate=request.entrydate,
            )
            session.add(batch)
            session.commit()
            session.refresh(batch)

        # Ensure title exists
        book_title = session.exec(
            select(BookTitle).where(BookTitle.title == request.title)
        ).first()

        if not book_title:
            if not request.category:
                raise HTTPException(status_code=400, detail="Category must be provided for a new title")

            book_title = BookTitle(title=request.title, category=request.category)
            session.add(book_title)
            session.commit()
            session.refresh(book_title)

        # Add units
        for _ in range(request.units):
            book = BookInventory(
                batch_id=batch.id,
                title=request.title,
            )
            session.add(book)

        session.commit()
        return {"message": f"{request.units} books of '{request.title}' added successfully"}


# --------------------------------------------------------
#               LIST TITLES
# --------------------------------------------------------
@router.get("/list-titles")
def list_titles():
    with Session(engine) as session:
        titles = session.exec(select(BookTitle.title)).all()
        return sorted(set(titles))


# --------------------------------------------------------
#               **NEW** LIST BATCHES FOR A TITLE
# --------------------------------------------------------
@router.get("/list-batches")
def list_batches(title: str):
    with Session(engine) as session:
        batches = (
            session.exec(select(BookBatch).where(BookBatch.book_title == title))
            .all()
        )

        return [
            {
                "id": b.id,
                "MRP": b.MRP,
                "entrydate": b.entrydate.isoformat() if b.entrydate else None
            }
            for b in batches
        ]


# --------------------------------------------------------
#           ASSIGN BOOKS TO LEAD VOLUNTEER
# --------------------------------------------------------
class AssignBooksRequest(BaseModel):
    volunteer_id: int
    book_title: str
    units: int


@router.post("/assign-books")
def assign_books(request: AssignBooksRequest):
    with Session(engine) as session:
        vol = session.exec(select(Volunteers).where(Volunteers.id == request.volunteer_id)).first()
        if not vol:
            raise HTTPException(status_code=404, detail="Volunteer not found")
        if not vol.is_lead:
            raise HTTPException(status_code=403, detail="Volunteer is not a lead volunteer")

        unsold_books = session.exec(
            select(BookInventory).where(
                BookInventory.status == "Unsold",
                BookInventory.title == request.book_title
            )
        ).all()

        available = len(unsold_books)
        if available == 0:
            raise HTTPException(status_code=400, detail="No unsold copies available for this title")

        books_to_assign = unsold_books[:min(available, request.units)]
        for book in books_to_assign:
            book.status = "Assigned"
            book.assigned_volunteer_id = request.volunteer_id

        session.commit()
        return {
            "message": f"{len(books_to_assign)} copies of '{request.book_title}' assigned to volunteer {request.volunteer_id}"
        }


# --------------------------------------------------------
#           VIEW ASSIGNED BOOKS
# --------------------------------------------------------
@router.get("/assigned_books")
def assigned_books(volunteer_id: int):
    with Session(engine) as session:
        assigned_books = session.exec(
            select(BookInventory)
            .where(BookInventory.status == "Assigned")
            .where(BookInventory.assigned_volunteer_id == volunteer_id)
        ).all()
        return {book.id: book.title for book in assigned_books}


# --------------------------------------------------------
#           UNSOLD INVENTORY
# --------------------------------------------------------
@router.get("/unsold_inventory")
def get_unsold_inventory():
    with Session(engine) as session:
        rows = session.exec(
            select(BookInventory.title)
            .where(BookInventory.status == "Unsold")
        ).all()

        inventory_count = Counter(rows)
        return dict(inventory_count)
