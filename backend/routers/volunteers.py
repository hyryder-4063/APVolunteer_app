from fastapi import APIRouter, Depends, HTTPException
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
    default_location_id: int

@router.post("/add-volunteer")
def add_volunteer(request: VolunteerRequest):

    with Session(engine) as session:
        vol = Volunteers(name = request.vol_name, join_date = request.vol_join_date, default_location_id = request.default_location_id)
        session.add(vol)
        session.commit()
        session.refresh(vol)

    return {"message": f" {vol.name} added, volunteer ID is {vol.id}"}

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

    return {"message": f"Volunteer {vol.name} (ID {vol.id}) is now a Lead Volunteer"}

#API: Get all volunteers list
@router.get("/volunteer-list")
def list_volunteers():
    with Session(engine) as session:
        vol = session.exec(
            select(Volunteers)
        ).all()
        return [{"id": v.id,"vol_name": v.name, "default_location": v.default_location_id} for v in vol]

#API: Get leads list
@router.get("/list-leads")
def list_volunteer_leads():
    with Session(engine) as session:
        leads = session.exec(
            select(Volunteers).where(Volunteers.is_lead == True)
        ).all()
        return [{"id": v.id,"vol_name": v.name, "default_location_id": v.default_location_id} for v in leads]


