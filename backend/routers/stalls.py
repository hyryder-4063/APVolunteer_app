from collections import defaultdict
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from pydantic import BaseModel
from typing import List
from datetime import date

from backend.models import Stalls, Volunteers, Inventory, StallVolunteers, InventoryMovement, MovementType, Title
from backend.database import Session, engine

router = APIRouter(prefix="/stalls")


class StallRequest(BaseModel):
    stall_location: str
    stall_date: date
    volunteer_ids: List[int]
    volunteer_lead_id: int



@router.post("/create")
def create_stall(request: StallRequest):

    with (Session(engine) as session):

        # -------------------------
        # 1. Validate volunteer IDs
        # -------------------------
        volunteer_names = []
        valid_vol_ids = session.exec(
            select(Volunteers).where(Volunteers.id.in_(request.volunteer_ids))
        ).all()


        if len(valid_vol_ids) != len(request.volunteer_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more volunteer IDs do not exist"
            )
        for v in valid_vol_ids:
            volunteer_names.append(v.name)

        # 2.Check lead volunteer exists
        lead = session.get(Volunteers, request.volunteer_lead_id)
        if not lead:
            raise HTTPException(
                status_code=404,
                detail="Lead volunteer ID does not exist"
            )

        # -------------------------
        # 3. Create stall entry
        # -------------------------
        stall = Stalls(
            location=request.stall_location,
            date=request.stall_date,
            lead_id=request.volunteer_lead_id
        )
        session.add(stall)
        session.flush()


        # -------------------------
        # 4. Add volunteers to junction table
        # -------------------------
        for volunteer in request.volunteer_ids:
            link = StallVolunteers(stall_id=stall.id, volunteer_id=volunteer)
            session.add(link)

        session.commit()
        session.refresh(stall)

        return {
            "message": "Stall created",
            "stall_id": stall.id,
            "stall_location": stall.location,
            "stall_date": stall.date,
            "volunteer_ids": request.volunteer_ids,
            "volunteer names": volunteer_names,
        }

class SoldBook(BaseModel):
    title: str
    batch_id: int
    copies_sold: int
    book_selling_price_per_copy: float

class AddSales(BaseModel):
    stall_id: int
    sold_books: List[SoldBook]

@router.post("/{stall_id}/add-sales")
def add_sales(request: AddSales):
    with (Session(engine) as session):



        # 1. Check stall exists
        stall = session.get(Stalls, request.stall_id)
        if not stall:
            raise HTTPException(404, "Stall not found")
        if stall.is_closed:
            raise HTTPException(400, "Stall already closed.")

        # 2. Prevent updates after close
        if stall.is_closed:
            raise HTTPException(400, "Stall already closed. No further sales allowed.")

        lead_id = stall.lead_id

        # -------------------------
        # 5. Update sold books
        # -------------------------
        sold_books_details = []

        for b in request.sold_books:

            if b.copies_sold <= 0:
                raise HTTPException(400, "copies_sold must be positive")

            #5.1 Validate batch exists in inventory

            batch = session.get(Inventory, b.batch_id)
            if not batch:
                raise HTTPException(status_code=404, detail=f"Batch ID {b.batch_id} not found")

            #5.2 Check if title matches batch

            title_obj = session.get(Title, batch.title_id)

            if not title_obj:
                raise HTTPException(status_code=400,
                    detail=f"No titles found for this batch ID: {b.batch_id}")
            title = title_obj.title
            if title != b.title:
                raise HTTPException(status_code=400,
                    detail=f"Book {b.title} does not match with batch ID {b.batch_id}")

            # 5.3 Fetch movements for this batch_id and volunteer lead (this can include multiple ledger entries for assign, sold, return)
            movements = session.exec(
                select(InventoryMovement).where(
                    (InventoryMovement.batch_id == b.batch_id) &
                    (InventoryMovement.volunteer_id == lead_id)
                )
            ).all()

            if not movements:
                raise HTTPException(
                    status_code=400,
                    detail=f"Book {b.batch_id} was never assigned to lead volunteer {lead_id}"
                )

            # 5.4 Fetch #copies assigned to the volunteer lead of the stall
            found = 0
            final_sold = 0
            assigned = 0
            returned = 0
            sold = 0
            for m in movements:
                if m.movement_type == MovementType.ASSIGN:
                    assigned += m.copies_moved
                elif m.movement_type == MovementType.SOLD:
                    sold += m.copies_moved
                elif m.movement_type == MovementType.RETURN:
                    returned += m.copies_moved

            available = assigned-sold-returned
            final_sold = min(available, b.copies_sold)


            # 5.5 Record new sale entry in ledger

            if available <= 0:
                raise HTTPException(status_code=404,
                                    detail=f"No copies of batch ID {b.batch_id} currently available for sale (Assigned: {assigned}, Sold: {sold}), Returned: {returned} ")


            move = InventoryMovement(
                batch_id = b.batch_id,
                volunteer_id = stall.lead_id,
                stall_id = stall.id,
                movement_type = MovementType.SOLD,
                copies_moved =  final_sold,
                movement_date = stall.date,
                selling_price_per_copy = b.book_selling_price_per_copy
            )
            session.add(move)

            #Allow partial sale but give a message
            if available < b.copies_sold:
                sale_message = f"Partial sale recorded: Only {available} assigned currently for sale whereas {b.copies_sold} requested for Sale entry. {available} marked as sold"
            else:
                sale_message = f"Sale recorded:  {b.copies_sold} marked as sold"


            sold_books_details.append({
                    "title": b.title,
                    "batch_id": b.batch_id,
                    "copies": final_sold,
                    "selling_price_per_copy": float(b.book_selling_price_per_copy),
                    "message": sale_message
                })

        session.commit()
        session.refresh(stall)

    return {
        "message": "Sale entry updated successfully",
        "stall_id": request.stall_id,
        "sold_books": sold_books_details
    }

@router.post("/{stall_id}/close")
def close_stall(stall_id: int):
    with Session(engine) as session:
        stall = session.get(Stalls, stall_id)
        if not stall:
            raise HTTPException(404, "Stall not found")
        if stall.is_closed:
            return {"message": "Stall is already closed."}

        stall.is_closed = True
        session.add(stall)
        session.commit()
        return {"message": f"Stall {stall_id} closed successfully."}



@router.get("/monthly-stall-list")
def monthly_stall_list():
    with Session(engine) as session:
        stalls = session.exec(select(Stalls)).all()

        monthly_map = {}

        for s in stalls:
            month_key = s.date.strftime("%B %Y")  # e.g., "January 2025"

            if month_key not in monthly_map:
                monthly_map[month_key] = []

            monthly_map[month_key].append({
                "stall_id": s.id,
                "stall_location": s.location,
                "stall_date": str(s.date),
                "lead_volunteer_id": s.lead_id,
            })

        return monthly_map


from collections import defaultdict

@router.get("/stall-performance")
def stall_performance(stall_id: int):
    with Session(engine) as session:

        # 1. Fetch stall
        stall = session.get(Stalls, stall_id)
        if not stall:
            raise HTTPException(status_code=404, detail="Stall not found")

        # 2. Fetch volunteers
        vol = session.exec(
            select(Volunteers)
            .join(StallVolunteers, StallVolunteers.volunteer_id == Volunteers.id)
            .where(StallVolunteers.stall_id == stall_id)
        ).all()
        volunteer_names = [v.name for v in vol]

        # 3. Fetch inventory movements for this stall
        movements = session.exec(
            select(InventoryMovement)
            .where(InventoryMovement.stall_id == stall_id)
        ).all()

        # 4. Aggregate by title + batch
        table = []
        for m in movements:
            if m.movement_type != MovementType.SOLD:
                continue  # only count sold copies

            batch = session.get(Inventory, m.batch_id)
            title_obj = session.get(Title, batch.title_id)
            title_name = title_obj.title if title_obj else "Unknown Title"

            table.append({
                "Title": title_name,
                "Batch ID": batch.id,
                "Sold": m.copies_moved,
                "Revenue": round(m.copies_moved * m.selling_price_per_copy, 2)
            })

        # Optional: combine multiple sales of same batch
        combined = defaultdict(lambda: {"Sold": 0, "Revenue": 0})
        for row in table:
            key = (row["Title"], row["Batch ID"])
            combined[key]["Sold"] += row["Sold"]
            combined[key]["Revenue"] += row["Revenue"]

        final_table = [
            {"Title": k[0], "Batch ID": k[1], "Sold": v["Sold"], "Revenue": v["Revenue"]}
            for k, v in combined.items()
        ]

        return {
            "stall": {
                "stall_id": stall.id,
                "stall_location": stall.location,
                "stall_date": str(stall.date),
                "volunteers": volunteer_names
            },
            "performance": final_table
        }
