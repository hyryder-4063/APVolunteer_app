from typing import Optional
from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlmodel import select, Field
from pydantic import BaseModel
from datetime import date
from backend.database import engine, Session
from backend.models import Inventory, Title, Volunteers, InventoryMovement, MovementType

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
        existing = session.exec(
            select(Title).where(Title.title == request.title)
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Book title already exists")

        book_title = Title(title=request.title, category=request.category)
        session.add(book_title)
        session.commit()


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

        #1. Ensure title exists or create new title
        book_title = session.exec(
            select(Title).where(Title.title == request.title)
        ).first()

        if not book_title:
            if not request.category:
                raise HTTPException(status_code=400, detail="Category must be provided for a new title")

            book_title = Title(title=request.title, category=request.category)
            session.add(book_title)
            session.commit()
            session.refresh(book_title)


        # -----------------------------
        # CASE 1: Add copies to Existing batch
        # -----------------------------
        if request.batch_id is not None:
            batch = session.get(Inventory, request.batch_id)
            if not batch:
                raise HTTPException(status_code=400, detail="Batch not found")

            # DO NOT touch entrydate or MRP for existing batch
            # Just add units
            batch.copies_total += request.units
            session.flush(batch)
            session.commit()
            return {
                "message": f"{request.units} books added to existing batch {batch.id}"
            }

        # -----------------------------
        # CASE 2: Create NEW batch and add copies
        # -----------------------------

        new_batch = Inventory(
            title_id = book_title.id,
            MRP = request.MRP,
            entrydate = request.entrydate,
            copies_total = request.units
        )
        session.add(new_batch)
        session.commit()

        return {"message": f"{request.units} books of '{request.title}' added successfully, batch: {new_batch.id}"}


# --------------------------------------------------------
#               LIST TITLES
# --------------------------------------------------------
@router.get("/list-titles")
def list_titles():
    with Session(engine) as session:
        titles = session.exec(select(Title.title)).all()
        return sorted(set(titles))


# --------------------------------------------------------
#               **NEW** LIST BATCHES FOR A TITLE
# --------------------------------------------------------
@router.get("/list-batches")
def list_batches(title: str):
    with Session(engine) as session:
        book_title = session.exec(
            select(Title).
            where(Title.title == title)
        ).first()


        if not book_title:
            raise HTTPException(status_code=400, detail="Title not found")

        batches = (
            session.exec(select(Inventory).where(Inventory.title_id == book_title.id))
            .all()
        )

        return [
            {
                "id": b.id,
                "MRP": b.MRP,
                "entrydate": b.entrydate.isoformat() if b.entrydate else None,
                "copies_total": b.copies_total
            }
            for b in batches
        ]


# --------------------------------------------------------
#           ASSIGN BOOKS TO LEAD VOLUNTEER
# --------------------------------------------------------
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from backend.database import engine
from backend.models import Inventory, Volunteers, InventoryMovement, MovementType

router = APIRouter(prefix="/books")


class AssignBooksRequest(BaseModel):
    volunteer_id: int
    batch_id: int
    units: int


@router.post("/assign-books")
def assign_books(request: AssignBooksRequest):
    with Session(engine) as session:

        # 1. Validate volunteer exists
        volunteer = session.get(Volunteers, request.volunteer_id)
        if not volunteer:
            raise HTTPException(status_code=404, detail="Volunteer not found")

        # 2. Validate batch exists
        batch = session.get(Inventory, request.batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch ID {request.batch_id} not found")

        # 3. Check available copies
        assigned = sum(
            m.copies_moved for m in session.exec(
                select(InventoryMovement)
                .where(InventoryMovement.batch_id == request.batch_id)
                .where(InventoryMovement.movement_type == MovementType.ASSIGN)
            ).all()
        )
        available = batch.copies_total - assigned
        if request.units > available:
            raise HTTPException(status_code=400, detail=f"Only {available} copies available to assign")

        # 4. Record assignment
        move = InventoryMovement(
            batch_id=request.batch_id,
            volunteer_id=request.volunteer_id,
            movement_type=MovementType.ASSIGN,
            copies_moved=request.units
        )
        session.add(move)
        session.commit()

    return {
        "message": f"{request.units} copies assigned successfully",
        "volunteer_id": request.volunteer_id,
        "batch_id": request.batch_id,
        "assigned_units": request.units
    }


# --------------------------------------------------------
#           LEAD VOLUNTEER TO RETURN BOOKS
# --------------------------------------------------------
class ReturnBooksRequest(BaseModel):
    volunteer_id: int
    title: str
    batch_id: int
    copies_return: int

@router.post("/return-books")
def return_books(request: AssignBooksRequest):

    with (Session(engine) as session):

        #1. Validate volunteer
        vol = session.exec(select(Volunteers).where(Volunteers.id == request.volunteer_id)).first()
        if not vol:
            raise HTTPException(status_code=404, detail="Volunteer not found")
        if not vol.is_lead:
            raise HTTPException(status_code=403, detail="Volunteer is not a lead volunteer")

        #2. Validate batch, title, fetch title id
        inv = session.get(Inventory, request.batch_id)
        if inv is None:
            raise HTTPException(status_code=404, detail="Batch not found, enter a valid batch id")
        book_title = session.exec(select(Title).where(Title.title == request.title)).first()

        if not book_title:
            raise HTTPException(status_code=404, detail="Title not found")

        if inv.title_id != book_title.id:
            raise HTTPException(status_code=404, detail="Title does not match batch ID")


        #3. Fetch copies assigned for this batch to the volunteer


        assigned_copies = session.exec(select(func.sum(InventoryMovement.copies_moved)).where(
            InventoryMovement.batch_id == request.batch_id, InventoryMovement.movement_type == MovementType.ASSIGN, InventoryMovement.volunteer_id == request.volunteer_id)
        ).first() or 0

        if assigned_copies == 0:
            raise HTTPException(status_code=400, detail="No copies were assigned for this title")

        return_copies = session.exec(select(func.sum(InventoryMovement.copies_moved)).where(
            InventoryMovement.batch_id == request.batch_id, InventoryMovement.movement_type == MovementType.RETURN, InventoryMovement.volunteer_id == request.volunteer_id)
        ).first() or 0

        sold_copies = session.exec(select(func.sum(InventoryMovement.copies_moved)).where(
            InventoryMovement.batch_id == request.batch_id, InventoryMovement.movement_type == MovementType.SOLD,
            InventoryMovement.volunteer_id == request.volunteer_id)
        ).first() or 0

        available = assigned_copies - return_copies - sold_copies
        if available <= 0:
            raise HTTPException(
                status_code=400,
                detail="Volunteer has no copies left to return"
            )

        to_be_returned = min(request.copies_return, available)
        if to_be_returned <= 0:
            raise HTTPException(
                status_code=400,
                detail="No valid copies to return"
            )

        #5. Create Return movement entry
        movement = InventoryMovement(
           batch_id = request.batch_id,
           movement_type = MovementType.RETURN,
           volunteer_id = request.volunteer_id,
           copies_moved = to_be_returned,
           movement_date = date.today()
        )

        session.add(movement)
        session.commit()
        return {
            "message": f"{to_be_returned} copies of '{request.title}' returned by volunteer {request.volunteer_id}",
            "assigned": assigned_copies,
            "sold": sold_copies,
            "returned_before": return_copies,
            "returned_now": to_be_returned,
            "remaining_after": available - to_be_returned
        }





# --------------------------------------------------------
#           VIEW ASSIGNED INVENTORY
# --------------------------------------------------------
@router.get("/assigned_books")
def assigned_books(volunteer_id: int):
    with (Session(engine) as session):

        movements = session.exec(select(InventoryMovement).where(
            (InventoryMovement.volunteer_id == volunteer_id) &
            (InventoryMovement.movement_type ==  MovementType.ASSIGN))
        ).all()


        result = []
        for move in movements:
            batch = session.exec(select(Inventory).where(Inventory.id == move.batch_id)).first()
            title = session.exec(select(Title).where(Title.id == batch.title_id)).first()
            result.append({
                "batch_id": batch.id,
                "title": title.title,
                "copies_assigned": move.copies_moved,
                "volunteer_id": volunteer_id,
            })

        return result


# --------------------------------------------------------
#           UNSOLD INVENTORY
# --------------------------------------------------------


@router.get("/unsold_inventory")
def get_unsold_inventory():
    with Session(engine) as session:
        batches = session.exec(select(Inventory)).all()
        respond = []

        for batch in batches:
            total_copies = batch.copies_total

            moved_copies = session.exec(
                select(func.sum(InventoryMovement.copies_moved))
                .where(
                    InventoryMovement.batch_id == batch.id,
                    InventoryMovement.movement_type.in_([MovementType.ASSIGN, MovementType.SOLD])
                )
            ).first() or 0

            title_obj = session.get(Title, batch.title_id)
            title_name = title_obj.title if title_obj else "Unknown Title"

            available = total_copies - (moved_copies or 0)
            if available <= 0:
                continue  # skip batches with no available copies

            respond.append({
                "title": title_name,
                "batch_id": batch.id,
                "available": available
            })

        return respond
