from fastapi import APIRouter, HTTPException
from sqlmodel import select
from datetime import date
from collections import defaultdict
from calendar import monthrange
from backend.models import Stalls, Volunteers, Inventory, StallVolunteers, InventoryMovement, Title, MovementType
from backend.database import Session, engine
from backend.routers.stalls import stall_performance

router = APIRouter(prefix="/reports")


#View Inventory summary
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
                "Revenue": round(values["Revenue"], 2)
            }
            for title, values in stats.items()
        ]

        return table


#View admin monthly dashboard
@router.get("/admin-monthly-performance")
def monthly_performance(month: str):

    # Extract month cleanly
    try:
        year, mon = map(int, month.split("-"))
        start_date = date(year, mon, 1)
        end_date = date(year, mon, monthrange(year, mon)[1])
    except:
        raise HTTPException(status_code=404, detail="Month must be in format YYYY-MM")

    with Session(engine) as session:

        #1. Fetch stalls in that month
        stalls = session.exec(
            select(Stalls).where(Stalls.date.between(start_date, end_date)
            )
        ).all()
        if not stalls:
            raise HTTPException(status_code=404, detail=f"no Stall found in month {month}")


        number_of_stalls = 0
        monthly_revenue = defaultdict(float)
        total_books_sold = defaultdict(int)
        stall_revenue = defaultdict(float)  # total revenue per stall
        stall_bookcount = defaultdict(int)  # total books sold per stall
        total_monthly_units = 0
        total_monthly_rev = 0.0


        #2. Aggregate stall performance across each stall in the month
        for stall in stalls:
            stall_total_revenue = 0.0
            stall_total_books_sold = 0
            number_of_stalls += 1
            perf = stall_performance(stall.id)
            for p in perf["performance"]:

                title = p["Title"]
                sold = p["Sold"]
                revenue = p["Revenue"]

                #Title wise totals
                total_books_sold[title] += sold
                monthly_revenue[title] += revenue

                # Stall wise totals
                stall_total_books_sold += sold
                stall_total_revenue += revenue


            stall_revenue[stall.id] += stall_total_revenue
            stall_bookcount[stall.id] += stall_total_books_sold


        total_monthly_rev= sum(stall_revenue.values())
        total_monthly_units = sum(stall_bookcount.values())


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
            "total_stalls": number_of_stalls,
            "total_books_sold": total_monthly_units,
            "monthly_revenue": total_monthly_rev,
            "title_wise": [
                {
                    "title": title,
                    "total_sold": total_books_sold[title],
                    "total_revenue": round(monthly_revenue[title], 2)
                }
                for title in total_books_sold
            ],
            "stall_wise": [
                {
                    "stall_id": stall_id,
                    "books_sold": stall_bookcount[stall_id],
                    "revenue": round(stall_revenue[stall_id], 2)
                }
                for stall_id in stall_revenue
            ],
            "stall_bookssoldcat": {
                "<10 books": count1,
                "10-20 books": count2,
                ">20 books": count3
            },
            "stall_revcat": {
                "<INR 2K": countrev1,
                "INR 2-5K": countrev2,
                "INR >5K": countrev3,
            },
            "vol_attendance": {
                "1 stall": vol_bucket_1,
                "2-3 stalls": vol_bucket_2_3,
                ">3 stalls": vol_bucket_3plus,
            }

        }
