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

            #Check book exists in inventory
            if not book:
                raise HTTPException(status_code=404, detail=f"Book ID {b.book_id} not found")

            # Check book assigned to the volunteer lead of the stall
            if book.assigned_volunteer_id != request.volunteer_lead_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Book {b.book_id} is not assigned to lead volunteer {request.volunteer_lead_id}"
                )

            # Check book assigned to the volunteer lead of the stall
            if book.status != "Assigned":
                raise HTTPException(
                    status_code=400,
                    detail=f"Book {b.book_id} cannot be sold because status is {book.status}"
                )

            book.status = "Sold"
            book.stall_id = stall.id
            book.sold_date = stall.stall_date
            book.selling_price = float(b.book_selling_price)


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


@router.get("/monthly-list")
def monthly_stall_list():
    with Session(engine) as session:
        stalls = session.exec(select(Stalls)).all()

        monthly_map = {}

        for s in stalls:
            month_key = s.stall_date.strftime("%B %Y")  # e.g., "January 2025"

            if month_key not in monthly_map:
                monthly_map[month_key] = []

            monthly_map[month_key].append({
                "stall_id": s.id,
                "stall_location": s.stall_location,
                "stall_date": str(s.stall_date)
            })

        return monthly_map



@router.get("/stall-performance")
def stall_performance(stall_id: int):
    with Session(engine) as session:
        # 1. Fetch stall
        stall = session.exec(
            select(Stalls).where(Stalls.id == stall_id)
        ).first()

        if not stall:
            raise HTTPException(status_code=404, detail="Stall not found")

        # 2. Fetch volunteer links (always returns list of volunteer_ids)
        volunteer_links = session.exec(
            select(StallVolunteers.volunteer_id)
            .where(StallVolunteers.stall_id == stall.id)
        ).all()

        # Normalize volunteer_ids to a simple list of ints
        volunteer_ids = []
        for v in volunteer_links:
            if isinstance(v, int):
                volunteer_ids.append(v)
            elif isinstance(v, (list, tuple)) and len(v) > 0:
                # e.g. (5,) or [5]
                volunteer_ids.append(int(v[0]))
            else:
                # Unexpected shape — skip
                continue

        # 3. Fetch volunteer names cleanly
        volunteers = []
        if volunteer_ids:
            vol_rows = session.exec(
                select(Volunteers.vol_name)
                .where(Volunteers.id.in_(volunteer_ids))
            ).all()

            for vr in vol_rows:
                if isinstance(vr, str):
                    volunteers.append(vr)
                elif isinstance(vr, (list, tuple)) and len(vr) > 0:
                    volunteers.append(vr[0])
                else:
                    continue

        # 4. Fetch books related to this stall (either sold at this stall OR assigned to the lead)
        rows = session.exec(
            select(
                BookInventory.title,
                BookInventory.status,
                BookInventory.selling_price
            ).where(
                (BookInventory.stall_id == stall_id) |
                ((BookInventory.assigned_volunteer_id == stall.volunteer_lead_id) &
                 (BookInventory.status == "Assigned"))
            )
        ).all()

        # If no book rows, still return the stall info (so frontend can show stall details)
        if not rows:
            return {
                "stall": {
                    "stall_id": stall.id,
                    "stall_location": stall.stall_location,
                    "stall_date": str(stall.stall_date),
                    "volunteers": volunteers
                },
                "performance": []
            }

        # 5. Aggregate stats by title
        stats = {}
        for title, status, price in rows:
            if title not in stats:
                stats[title] = {"Assigned": 0, "Sold": 0, "Unsold": 0, "Revenue": 0.0}

            if status == "Assigned":
                stats[title]["Assigned"] += 1
            elif status == "Sold":
                stats[title]["Sold"] += 1
                stats[title]["Revenue"] += float(price or 0)
            elif status == "Unsold":
                stats[title]["Unsold"] += 1

        # 6. Build performance table (ensure keys present and types predictable)
        table = []
        for title, s in stats.items():
            assigned = s["Assigned"]
            sold = s["Sold"]
            unsold = s["Unsold"]
            revenue = round(float(s["Revenue"]), 2)
            table.append({
                "Title": title,
                "Assigned": assigned,
                "Sold": sold,
                "Unsold": unsold,
                "Remaining": assigned - sold,
                "Revenue": revenue
            })

        print("FINAL RETURNING → volunteers =", volunteers)

        # Final response uses the keys your frontend expects
        return {
            "stall": {
                "stall_id": stall.id,
                "stall_location": stall.stall_location,
                "stall_date": str(stall.stall_date),
                "volunteers": volunteers
            },
            "performance": table
        }
