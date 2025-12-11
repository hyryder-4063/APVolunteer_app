from collections import defaultdict
from fastapi import APIRouter
from sqlalchemy import func
from sqlmodel import select
from backend.models import Stalls, Volunteers, Inventory, StallVolunteers, InventoryMovement, MovementType, Title, Location
from backend.database import Session, engine

router = APIRouter(prefix="/inventory")

@router.get("/unsold_inventory")
def unsold_inventory():
    with Session(engine) as session:
        batches = session.exec(select(Inventory)).all()
        respond = []

        for batch in batches:
            total_copies = batch.copies_total or 0

            # sum assigned for this batch
            assigned_sum = session.exec(
                select(func.sum(InventoryMovement.copies_moved))
                .where(
                    InventoryMovement.batch_id == batch.id,
                    InventoryMovement.movement_type == MovementType.ASSIGN
                )
            ).first() or 0
            # ----- Get all volunteers who assigned books to this batch -----
            assign_rows = session.exec(
                select(
                    InventoryMovement.volunteer_id,
                    func.sum(InventoryMovement.copies_moved)
                )
                .where(
                    InventoryMovement.batch_id == batch.id,
                    InventoryMovement.movement_type == MovementType.ASSIGN
                )
                .group_by(InventoryMovement.volunteer_id)
            ).all()

            assigned_volunteers = []

            for vol_id, copies_assigned in assign_rows:
                vol_name = session.exec(
                    select(Volunteers.name).where(Volunteers.id == vol_id)
                ).first()

                assigned_volunteers = "\n".join(
                    f"Name: {session.get(Volunteers, vol_id).name}, ID: {vol_id}, Assigned Copies: {int(copies_assigned)}"
                    for vol_id, copies_assigned in assign_rows
                )



            # sum returns for this batch (returns add back to warehouse)
            returned_sum = session.exec(
                select(func.sum(InventoryMovement.copies_moved))
                .where(
                    InventoryMovement.batch_id == batch.id,
                    InventoryMovement.movement_type == MovementType.RETURN
                )
            ).first() or 0

            # sum sold for this batch (part of assigns just for reporting)
            sold_sum = session.exec(
                select(func.sum(InventoryMovement.copies_moved))
                .where(
                    InventoryMovement.batch_id == batch.id,
                    InventoryMovement.movement_type == MovementType.SOLD
                )
            ).first() or 0

            # available in warehouse = total - (assigned - returned)
            available = total_copies - (assigned_sum - returned_sum)


            # skip if nothing available
            if available <= 0:
                continue

            title_obj = session.get(Title, batch.title_id)
            title_name = title_obj.title if title_obj else "Unknown Title"

            respond.append({
                "title": title_name,
                "batch_id": batch.id,
                "total": total_copies,
                "available": int(available),
                "assigned": int(assigned_sum),
                "returned": int(returned_sum),
                "sold": int(sold_sum),
                "lead_volunteer": assigned_volunteers
            })

        return respond


#View Admin Inventory summary
@router.get("/inventory_summary")
def inventory_summary():
    with Session(engine) as session:
        movements = session.exec(select(InventoryMovement)).all()
        inventories = session.exec(select(Inventory)).all()

        stats = defaultdict(lambda: {"Total": 0, "Assign": 0, "Sold": 0, "Return": 0, "Revenue": 0})

        # Total copies per title
        for i in inventories:
            title_obj = session.get(Title, i.title_id)
            if not title_obj:
                continue
            title = title_obj.title
            stats[title]["Total"] += i.copies_total

        # Process movements
        for m in movements:
            batch = session.get(Inventory, m.batch_id)
            if not batch:
                continue
            title_obj = session.get(Title, batch.title_id)
            if not title_obj:
                continue
            title = title_obj.title

            if m.movement_type == MovementType.ASSIGN:
                stats[title]["Assign"] += m.copies_moved
            elif m.movement_type == MovementType.SOLD:
                stats[title]["Sold"] += m.copies_moved
                stats[title]["Revenue"] += m.copies_moved * m.selling_price_per_copy
            elif m.movement_type == MovementType.RETURN:
                stats[title]["Return"] += m.copies_moved

        # Build table
        table = [
            {
                "Title": title,
                "Total": values["Total"],
                "Assign": values["Assign"],
                "Return": values["Return"],
                "Sold": values["Sold"],
                "Available": values["Total"] - (values["Assign"] -values["Return"]),
                "Revenue": round(values["Revenue"], 2)
            }
            for title, values in stats.items()
        ]

        return table


# --------------------------------------------------------
#           VIEW AVAILABLE INVENTORY (Per Volunteer)
# --------------------------------------------------------
@router.get("/volunteer_inventory")
def volunteer_inventory(volunteer_id: int):
    with (Session(engine) as session):

        #1. get all movements for this volunteer
        movements = session.exec(
            select(InventoryMovement).where(
                InventoryMovement.volunteer_id == volunteer_id
            )
        ).all()

        #2. Aggregate batch data
        batch_data = {}

        for move in movements:
            batch_id = move.batch_id

            if batch_id not in batch_data:
                batch_data[batch_id] = {
                    "assign": 0,
                    "sold": 0,
                    "return": 0
                }

            if move.movement_type == MovementType.ASSIGN:
                batch_data[batch_id]["assign"] += move.copies_moved
            if move.movement_type == MovementType.SOLD:
                batch_data[batch_id]["sold"] += move.copies_moved
            if move.movement_type == MovementType.RETURN:
                batch_data[batch_id]["return"] += move.copies_moved

        #3. Build final result
        result = []

        for batch_id, data in batch_data.items():
            available = data["assign"] - data["sold"] - data["return"]

            if available <= 0:
                continue

            batch = session.get(Inventory, batch_id)
            title_obj = session.get(Title, batch.title_id)

            result.append({
                "batch_id": batch_id,
                "title": title_obj.title,
                "assigned": data["assign"],
                "sold": data["sold"],
                "returned": data["return"],
                "available": available,
                "volunteer_id": volunteer_id
            })

        return result


