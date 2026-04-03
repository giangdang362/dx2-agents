import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from open_webui.models.demo.meeting_rooms import (
    BookingForm,
    BookingModel,
    BookingPatchForm,
    Bookings,
)

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Inlined mock reference data
# ---------------------------------------------------------------------------

MEETING_ROOMS = [
    {"id": "rose", "name": "Rose", "code": "HCM", "building": "Creative Space", "floor": 4, "capacity": 8, "equipment": ["projector", "whiteboard", "sound"], "available": True},
    {"id": "daisy", "name": "Daisy", "code": "HCM", "building": "Creative Space", "floor": 2, "capacity": 10, "equipment": ["tv", "video_conf", "ac"], "available": True},
    {"id": "blossom", "name": "Blossom", "code": "HCM", "building": "Creative Space", "floor": 5, "capacity": 15, "equipment": ["projector", "whiteboard", "ac"], "available": True},
    {"id": "sunflower", "name": "Sun Flower", "code": "HCM", "building": "Creative Space", "floor": 3, "capacity": 20, "equipment": ["projector", "tv", "video_conf", "phone"], "available": True},
    {"id": "orchid", "name": "Orchid", "code": "HN", "building": "789 Tower", "floor": 8, "capacity": 18, "equipment": ["projector", "tv", "video_conf", "ac"], "available": True},
    {"id": "lotus", "name": "Lotus", "code": "HN", "building": "CMC Tower", "floor": 6, "capacity": 25, "equipment": ["projector", "tv", "video_conf", "phone", "mic"], "available": True},
    {"id": "jasmine", "name": "Jasmine", "code": "DN", "building": "G8", "floor": 3, "capacity": 12, "equipment": ["projector", "tv", "video_conf"], "available": True},
    {"id": "tulip", "name": "Tulip", "code": "DN", "building": "G8", "floor": 5, "capacity": 16, "equipment": ["projector", "whiteboard", "ac", "sound"], "available": True},
]

ADMINS = [
    {"id": "admin-hn", "name": "Le Thuy Loan", "email": "ltloan@cmcglobal.vn", "role": "Admin Van phong Ha Noi", "department_code": "HN", "floor": 6},
    {"id": "admin-dn", "name": "Nguyen Thi Tinh Yen", "email": "nttyen@cmcglobal.vn", "role": "Admin Van phong Da Nang", "department_code": "DN", "floor": 3},
    {"id": "admin-hcm", "name": "Le Thi Tuyet Hao", "email": "ltthao1@cmcglobal.vn", "role": "Admin Van phong TP.HCM", "department_code": "HCM", "floor": 3},
]

CATERING_OPTIONS = [
    {"id": "tea-coffee", "name": "Tra + Ca phe + Banh", "price": 35000, "per_person": True, "icon": "coffee"},
    {"id": "coffee", "name": "Ca phe + Banh", "price": 30000, "per_person": True, "icon": "pastry"},
    {"id": "water", "name": "Nuoc suoi", "price": 10000, "per_person": True, "icon": "water"},
    {"id": "buffet", "name": "Buffet Trua", "price": 150000, "per_person": True, "icon": "buffet"},
    {"id": "lunch-box", "name": "Com hop", "price": 50000, "per_person": True, "icon": "lunchbox"},
    {"id": "fruit", "name": "Trai cay", "price": 25000, "per_person": True, "icon": "fruit"},
]

DEPARTMENTS = [
    {"id": "dept-hno-1", "name": "Phong Ky Thuat", "code": "HNO", "floor": 1, "admin_id": "admin-hno"},
    {"id": "dept-hno-2", "name": "Phong Kinh Doanh", "code": "HNO", "floor": 1, "admin_id": "admin-hno"},
    {"id": "dept-hno-3", "name": "Phong Marketing", "code": "HNO", "floor": 1, "admin_id": "admin-hno"},
    {"id": "dept-dno-1", "name": "Phong Marketing", "code": "DNO", "floor": 2, "admin_id": "admin-dno"},
    {"id": "dept-dno-2", "name": "Phong HR", "code": "DNO", "floor": 2, "admin_id": "admin-dno"},
    {"id": "dept-dno-3", "name": "Phong Sale", "code": "DNO", "floor": 2, "admin_id": "admin-dno"},
    {"id": "dept-hcmo-1", "name": "Phong Tai Chinh", "code": "HCMO", "floor": 3, "admin_id": "admin-hcmo"},
    {"id": "dept-hcmo-2", "name": "Phong Phap ly", "code": "HCMO", "floor": 3, "admin_id": "admin-hcmo"},
    {"id": "dept-hcmo-3", "name": "Phong Doi ngoai", "code": "HCMO", "floor": 3, "admin_id": "admin-hcmo"},
]


# ---------------------------------------------------------------------------
# Reference data endpoints (read-only, from inlined constants)
# ---------------------------------------------------------------------------


@router.get("/rooms")
async def list_rooms():
    return MEETING_ROOMS


@router.get("/admins")
async def list_admins():
    return ADMINS


@router.get("/departments")
async def list_departments():
    return DEPARTMENTS


@router.get("/catering-options")
async def list_catering_options():
    return CATERING_OPTIONS


# ---------------------------------------------------------------------------
# Booking CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("/bookings")
async def list_bookings():
    return Bookings.get_bookings()


@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    booking = Bookings.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/bookings")
async def save_booking(form: BookingForm):
    result = Bookings.insert_or_update(form)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to save booking")
    return {"ok": True}


@router.patch("/bookings/{booking_id}")
async def patch_booking(booking_id: str, form: BookingPatchForm):
    result = Bookings.patch_booking(booking_id, form)
    if not result:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"ok": True}


@router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str):
    success = Bookings.delete_booking_by_id(booking_id)
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Room availability
# ---------------------------------------------------------------------------


@router.get("/availability")
async def check_availability(
    date: str = Query(""),
    start_time: str = Query(""),
    end_time: str = Query(""),
    exclude_id: Optional[str] = Query(None),
):
    if not date or not start_time or not end_time:
        return {"occupied": []}
    occupied = Bookings.get_bookings_for_availability(
        date, start_time, end_time, exclude_id
    )
    return {"occupied": occupied}
