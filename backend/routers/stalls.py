from collections import defaultdict
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from pydantic import BaseModel
from typing import List
from datetime import date

from backend.models import Stalls, Volunteers, BookInventory, StallVolunteers
from backend.database import Session, engine

router = APIRouter(prefix="/stalls")


class SoldBook(BaseModel):
    book_id: int
    book_selling_price: float


class StallRequest(BaseModel):
    stall_location: str
    stall_date: date
    volunteer_ids: List[int]
    volunteer_lead_id: int
    sold_books: List[SoldBook]


@router.post("/add-close-stall")
def add_close_stall(request: StallRequest):

    with Session(engine) as session:

        # -------------------------
        # 1. Validate volunteer IDs
        # -------------------------
        valid_vol_ids = session.exec(
            select(Volunteers.id).where(Volunteers.id.in_(request.volunteer_ids))
        ).all()

        if len(valid_vol_ids) != len(request.volunteer_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more volunteer IDs do not exist"
            )

        # Check lead volunteer exists
        lead = session.get(Volunteers, request.volunteer_lead_id)
        if not lead:
            raise HTTPException(
                status_code=404,
                detail="Lead volunteer ID does not exist"
            )

        # -------------------------
        # 2. Create stall entry
        # -------------------------
        stall = Stalls(
            stall_location=request.stall_location,
            stall_date=request.stall_date,
            volunteer_lead_id=request.volunteer_lead_id
        )
        session.add(stall)
        session.flush()

        # -------------------------
        # 3. Add volunteers to junction table
        # -------------------------
        for volunteer in request.volunteer_ids:
            link = StallVolunteers(stall_id=stall.id, volunteer_id=volunteer)
            session.add(link)

        # -------------------------
        # 4. Update sold books
        # -------------------------
        sold_books_details = []

        for b in request.sold_books:
            book = session.get(BookInventory, b.book_id)
            if not book:
                raise HTTPException(status_code=404, detail=f"Book ID {b.book_id} not found")

            book.status = "Sold"
            book.stall_id = stall.id
            book.sold_date = stall.stall_date
            book.selling_price = b.book_selling_price


            sold_books_details.append(
                {
                    "book_id": b.book_id,
                    "title": book.title,
                    "selling_price": float(b.book_selling_price)
                }
            )

        session.commit()
        session.refresh(stall)

    return {
        "message": "Stall added and closed successfully",
        "stall_id": stall.id,
        "location": stall.stall_location,
        "date": stall.stall_date,
        "lead_volunteer_id": stall.volunteer_lead_id,
        "volunteers": request.volunteer_ids,
        "sold_books": sold_books_details
    }


#View single stall performance
@router.get("/stall-performance")
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

