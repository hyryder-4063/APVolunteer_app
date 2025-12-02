from fastapi import APIRouter, HTTPException
from sqlmodel import select
from datetime import date
from collections import defaultdict
from calendar import monthrange
from sqlalchemy import cast, Date
from sqlalchemy import and_

from backend.models import Stalls, Volunteers, BookInventory, StallVolunteers
from backend.database import Session, engine

router = APIRouter(prefix="/reports")


#View Inventory summary
@router.get("/inventory_summary")
def inventory_summary():
    session = Session(engine)
    books = session.exec(select(BookInventory)).all()

    inventory_summary = defaultdict(lambda: {"Unsold": 0, "Assigned": 0, "Sold": 0})

    for book in books:
        inventory_summary[book.title][book.status] += 1
    return inventory_summary

#View admin monthly dashboard
@router.get("/admin-monthly-performance")
def monthly_performance(month: str):
    try:
        year, mon = map(int, month.split("-"))
        start_date = date(year, mon, 1)
        end_date = date(year, mon, monthrange(year, mon)[1])
    except:
        raise HTTPException(status_code=404, detail="Month must be in format YYYY-MM")

    with Session(engine) as session:

        #1. Fetch stalls in that month
        stalls = session.exec(
            select(Stalls).where(Stalls.stall_date.between(start_date, end_date)
            )
        ).all()
        if not stalls:
            raise HTTPException(status_code=404, detail=f"no Stall found in month {month}")

        stall_bookcount = {}
        stall_revenue = {}
        monthly_revenue = 0.0
        total_books_sold = 0

        # 2. Count books sold in each stall
        for stall in stalls:

            stall_books = session.exec(
                select(BookInventory).where(
                    and_(
                        BookInventory.stall_id == stall.id,
                        BookInventory.status == "Sold"
                    )
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
            "monthly_revenue": monthly_revenue,
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
