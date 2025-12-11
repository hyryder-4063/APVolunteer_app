from fastapi import APIRouter
from sqlmodel import select
from sqlalchemy import func
from collections import defaultdict

from backend.models import (
    Stalls, Volunteers, StallVolunteers,
    InventoryMovement, MovementType, Title, Location
)
from backend.database import Session, engine
from backend.routers.stalls import stall_performance

router = APIRouter(prefix="/reports")

from fastapi import APIRouter, Query
from sqlmodel import select
from sqlalchemy import func
from collections import defaultdict
from backend.models import Stalls, StallVolunteers
from backend.database import Session, engine

router = APIRouter(prefix="/reports")


# ============================================================
# 1️⃣ VOLUNTEER ATTENDANCE REPORT
# ============================================================

def get_volunteer_stall_attendance(session, volunteer_id=None, months=None):
    """
    Returns month-wise stalls attended by a volunteer.
    'months' should be a list of YYYY-MM strings.
    """

    # Base query: month + volunteer + count
    stmt = (
        select(
            func.strftime("%Y-%m", Stalls.date).label("month"),
            StallVolunteers.volunteer_id,
            func.count(Stalls.id).label("stalls")
        )
        .join(StallVolunteers, StallVolunteers.stall_id == Stalls.id)
        .group_by("month", StallVolunteers.volunteer_id)
    )

    # Apply filters
    if volunteer_id:
        stmt = stmt.where(StallVolunteers.volunteer_id == volunteer_id)

    if months:
        if isinstance(months, str):
            months = [months]  # single month → list
        stmt = stmt.where(func.strftime("%Y-%m", Stalls.date).in_(months))

    # Execute query
    rows = session.exec(stmt).all()

    # Build month-wise totals
    month_map = defaultdict(int)
    for r in rows:
        month_map[r.month] += r.stalls

    # No data
    if not month_map:
        return {
            "volunteer_id": volunteer_id,
            "months": months or [],
            "stalls_attended": 0,
            "mom": []
        }

    # Month-wise breakdown
    mom = [{"month": m, "stalls_attended": c} for m, c in sorted(month_map.items())]

    return {
        "volunteer_id": volunteer_id,
        "months": months or [],
        "stalls_attended": sum(month_map.values()),
        "mom": mom
    }


# ============================================================
# Clean API route
# ============================================================

@router.get("/volunteer-attendance")
def api_volunteer_attendance(
    volunteer_id: int = None,
    month: list[str] = Query(None)  # <-- accepts multiple months
):
    with Session(engine) as session:
        return get_volunteer_stall_attendance(session, volunteer_id, month)

# ============================================================
# 2️⃣ LEAD PERFORMANCE REPORT
# ============================================================

def get_lead_performance(session, lead_id=None, months: list[str] = None):
    """
    Returns lead performance per month.
    'months' can be a list of YYYY-MM strings.
    """

    # Fetch only leads
    lead_ids = {v.id for v in session.exec(select(Volunteers).where(Volunteers.is_lead == True))}

    # -----------------------------------------------
    # 1. Stalls led per month
    # -----------------------------------------------
    stalls_stmt = (
        select(
            func.strftime("%Y-%m", Stalls.date).label("month"),
            Stalls.lead_id,
            func.count(Stalls.id)
        )
        .where(Stalls.lead_id.in_(lead_ids))
        .group_by("month", Stalls.lead_id)
    )

    stall_rows = session.exec(stalls_stmt).all()

    # -----------------------------------------------
    # 2. Books sold per month per lead
    # -----------------------------------------------
    sales_stmt = (
        select(
            func.strftime("%Y-%m", InventoryMovement.movement_date).label("month"),
            InventoryMovement.volunteer_id,   # == lead_id
            InventoryMovement.batch_id,
            InventoryMovement.copies_moved,
            InventoryMovement.selling_price_per_copy
        )
        .where(InventoryMovement.movement_type == MovementType.SOLD)
        .where(InventoryMovement.volunteer_id.in_(lead_ids))
    )

    sales_rows = session.exec(sales_stmt).all()

    # -----------------------------------------------
    # COMBINE DATA
    # -----------------------------------------------
    stalls_map = defaultdict(int)
    books_map = defaultdict(int)
    revenue_map = defaultdict(float)
    title_wise_map = defaultdict(lambda: defaultdict(lambda: {"sold": 0, "revenue": 0.0}))

    for m, lid, count in stall_rows:
        if months and m not in months:
            continue
        stalls_map[(m, lid)] += count

    for row in sales_rows:
        m, lid, batch, copies, price = row
        if months and m not in months:
            continue
        books_map[(m, lid)] += copies
        revenue_map[(m, lid)] += copies * price

        # Get title name
        title_name = session.exec(select(Title.title).where(Title.id == batch)).first()
        if title_name:
            title_wise_map[(m, lid)][title_name]["sold"] += copies
            title_wise_map[(m, lid)][title_name]["revenue"] += copies * price

    # -----------------------------------------------
    # APPLY FILTERS
    # -----------------------------------------------
    all_keys = set(stalls_map.keys()) | set(books_map.keys()) | set(revenue_map.keys())

    if lead_id:
        all_keys = {k for k in all_keys if k[1] == lead_id}

    # -----------------------------------------------
    # BUILD OUTPUT
    # -----------------------------------------------
    out = []
    for (m, lid) in sorted(all_keys):
        lid_name = session.get(Volunteers, lid).name if lid else None
        titles = []
        if (m, lid) in title_wise_map:
            for tname, vals in title_wise_map[(m, lid)].items():
                titles.append({"title": tname, "sold": vals["sold"], "revenue": vals["revenue"]})

        out.append({
            "month": m,
            "lead_id": lid,
            "lead_name": lid_name,
            "stalls_led": stalls_map.get((m, lid), 0),
            "books_sold_total": books_map.get((m, lid), 0),
            "revenue_total": revenue_map.get((m, lid), 0),
            "title_wise": titles
        })

    return out

@router.get("/lead-performance")
def api_lead_performance(lead_id: int = None, month: str = None):
    with Session(engine) as session:
        return get_lead_performance(session, lead_id, month)

# ============================================================
# 3️⃣ ADMIN PERFORMANCE REPORT
# ============================================================

def get_admin_performance(session, months: list[str] = None):
    """
    Aggregates all lead performance to produce admin-level summary.
    'months' can be a list of YYYY-MM strings to allow user to select multiple months.
    """

    all_lead_data = get_lead_performance(session)

    month_totals = defaultdict(lambda: {"total_stalls": 0, "books_sold": 0, "revenue": 0})
    titles = defaultdict(lambda: defaultdict(lambda: {"sold": 0, "revenue": 0.0 }))


    for row in all_lead_data:
        m = row["month"]
        if months and m not in months:
            continue
        month_totals[m]["total_stalls"] += row.get("stalls_led", 0)
        month_totals[m]["books_sold"] += row.get("books_sold_total", 0)
        month_totals[m]["revenue"] += row.get("revenue_total", 0)

        #Title level aggregation
        title_list = row.get("title_wise", [])

        for t in title_list:
            t_name = t["title"]
            titles[m][t_name]["sold"] += t.get("sold", 0)
            titles[m][t_name]["revenue"] += t.get("revenue", 0.0)

    # ---- Convert nested titles into list for frontend ----

    def convert_titles(month):
        return [
            {"title": name, "sold": stats["sold"], "revenue": stats["revenue"]}
            for name, stats in titles[month].items()
        ]


    # ---- Converter for aggregated titles across ALL selected months ----
    def convert_titles_total():
        total_map = defaultdict(lambda: {"sold": 0, "revenue": 0.0})

        # aggregate across each selected month (or all months)
        for m, tdict in titles.items():
            for name, stats in tdict.items():
                total_map[name]["sold"] += stats["sold"]
                total_map[name]["revenue"] += stats["revenue"]

        return [
            {"title": name, "sold": vals["sold"], "revenue": vals["revenue"]}
            for name, vals in total_map.items()
        ]

    # If filtering for a single month
    if months and len(months) == 1:
        m = months[0]
        return {
            "month": m,
            **month_totals.get(m, {"total_stalls":0,"books_sold":0,"revenue":0}),
            "titles": convert_titles(),
            "mom": []
        }

    # Full MoM or filtered months
    mom = []
    for m in sorted(month_totals.keys()):
        mom.append({"month": m, **month_totals[m]})

    return {
        "month": "ALL",
        "total_stalls": sum(v["total_stalls"] for v in month_totals.values()),
        "books_sold": sum(v["books_sold"] for v in month_totals.values()),
        "revenue": sum(v["revenue"] for v in month_totals.values()),
        "titles": convert_titles_total(),
        "mom": mom
    }

@router.get("/admin-performance")
def api_admin_performance(month: list[str] = None):
    with Session(engine) as session:
        return get_admin_performance(session, month)


def get_location_performance(session, months: list[str] = None):
    #1.get all the locations
    location_dict = defaultdict(lambda: {"stalls": 0, "sold": 0, "revenue": 0})
    stalls = session.exec(select(Stalls)).all()
    for stall in stalls:
        stall_month = stall.date.strftime("%Y-%m")
        if months and stall_month not in months:
            continue

        perf = stall_performance(stall.id)
        if perf:
            loc_obj = session.get(Location, stall.location_id)
            if not loc_obj:
                continue
            location = loc_obj.area

            location_dict[location]["stalls"] += 1
            total_sold = sum(row["Sold"] for row in perf["performance"])
            total_revenue = sum(row["Revenue"] for row in perf["performance"])

            location_dict[location]["sold"] += total_sold
            location_dict[location]["revenue"] += total_revenue

            


    #Convert to list of dict for front end
    output = []
    for key, value in location_dict.items():
        location = key
        stalls = value["stalls"]
        sold = value["sold"]
        revenue = value["revenue"]
        output.append({"location": location,"stalls": stalls, "sold": sold, "revenue": revenue})

    return output

@router.get("/location-performance")
def api_location_performance(month: list[str] = None):
    with Session(engine) as session:
        return get_location_performance(session, month)







