from fastapi import APIRouter
from sqlmodel import Session, select
from collections import defaultdict

from backend.models import (
    Stalls,
    StallVolunteers,
    InventoryMovement,
    MovementType,
    Title,
)
from backend.database import engine
from backend.routers.stalls import stall_performance

router = APIRouter(prefix="/analytics")


@router.get("/monthly_analytics")
def get_monthly_analytics(month: str):
    """
    Deep analytics for dashboards:
    - revenue buckets
    - books sold buckets
    - volunteer attendance buckets
    """
    with Session(engine) as session:

        # 1. Filter stalls for the month
        stalls = session.exec(
            select(Stalls).where(Stalls.date.like(f"{month}%"))
        ).all()

        if not stalls:
            return {"month": month, "message": "No stalls found"}

        number_of_stalls = 0
        monthly_revenue = defaultdict(float)
        total_books_sold = defaultdict(int)

        stall_revenue = defaultdict(float)
        stall_bookcount = defaultdict(int)

        location_books = defaultdict(int)
        location_revenue = defaultdict(float)

        # 2. Aggregate stall performance
        for stall in stalls:
            number_of_stalls += 1

            stall_total_revenue = 0.0
            stall_total_books_sold = 0

            perf = stall_performance(stall.id)

            for p in perf["performance"]:
                title = p["Title"]
                sold = p["Sold"]
                revenue = p["Revenue"]

                total_books_sold[title] += sold
                monthly_revenue[title] += revenue

                stall_total_books_sold += sold
                stall_total_revenue += revenue

            stall_revenue[stall.id] += stall_total_revenue
            stall_bookcount[stall.id] += stall_total_books_sold

            location_books[stall.location_id] += stall_total_books_sold
            location_revenue[stall.location_id] += stall_total_revenue

        # Totals
        total_monthly_units = sum(stall_bookcount.values())
        total_monthly_rev = sum(stall_revenue.values())

        # 3. Categorization buckets
        count1 = sum(1 for v in stall_bookcount.values() if v < 10)
        count2 = sum(1 for v in stall_bookcount.values() if 10 <= v <= 20)
        count3 = sum(1 for v in stall_bookcount.values() if v > 20)

        countrev1 = sum(1 for v in stall_revenue.values() if v < 2000)
        countrev2 = sum(1 for v in stall_revenue.values() if 2000 <= v <= 5000)
        countrev3 = sum(1 for v in stall_revenue.values() if v > 5000)

        loc1 = sum(1 for v in location_books.values() if v < 10)
        loc2 = sum(1 for v in location_books.values() if 10 <= v <= 20)
        loc3 = sum(1 for v in location_books.values() if v > 20)

        # 4. Volunteer attendance
        vol_month = defaultdict(int)
        stall_ids = [s.id for s in stalls]

        stall_volunteers = session.exec(
            select(StallVolunteers).where(
                StallVolunteers.stall_id.in_(stall_ids)
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

            "location_wise": [
                {
                    "location_id": loc_id,
                    "books_sold": location_books[loc_id],
                    "revenue": location_revenue[loc_id]
                }
                for loc_id in location_books.keys()
            ],

            "location_bookssoldcat": {
                "<10 books": loc1,
                "10-20 books": loc2,
                ">20 books": loc3
            },

            "stall_wise": [
                {
                    "stall_id": sid,
                    "books_sold": stall_bookcount[sid],
                    "revenue": round(stall_revenue[sid], 2)
                }
                for sid in stall_revenue
            ],

            "stall_bookssoldcat": {
                "<10 books": count1,
                "10-20 books": count2,
                ">20 books": count3
            },

            "stall_revenuecat": {
                "<INR 2K": countrev1,
                "INR 2-5K": countrev2,
                ">INR 5K": countrev3
            },

            "vol_attendance": {
                "1 stall": vol_bucket_1,
                "2-3 stalls": vol_bucket_2_3,
                ">3 stalls": vol_bucket_3plus,
            }
        }
