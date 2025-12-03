from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Select, select
from backend.database import engine
from backend.models import Volunteers
from datetime import date
from pydantic import BaseModel
from sqlmodel import Session, select

router = APIRouter(prefix="/volunteers")

#API: Add New Volunteer

class VolunteerRequest(BaseModel):
    vol_name: str
    vol_join_date: date

@router.post("/add-volunteer")
def add_volunteer(request: VolunteerRequest):

    with Session(engine) as session:
        vol = Volunteers(vol_name = request.vol_name, vol_join_date = request.vol_join_date)
        session.add(vol)
        session.commit()
        session.refresh(vol)

    return {"message": f" {vol.vol_name} added, volunteer ID is {vol.id}"}

#API: Make Volunteer A Lead
@router.post("/make-volunteer-lead")
def make_volunteer_lead(volunteer_id: int):
    with Session(engine) as session:
        vol = session.get(Volunteers, volunteer_id)

        if not vol:
            raise HTTPException(status_code=404, detail="Volunteer ID not found")

        vol.is_lead = True
        session.commit()
        session.refresh(vol)

    return {"message": f"Volunteer {vol.vol_name} (ID {vol.id}) is now a Lead Volunteer"}

#API: Get leads list
@router.get("/list-leads")
def list_volunteer_leads():
    with (Session(engine) as session):
        leads = session.exec(
            select(Volunteers).where(Volunteers.is_lead == True)
        ).all()
        return [{"id": v.id,"vol_name": v.vol_name} for v in leads]


