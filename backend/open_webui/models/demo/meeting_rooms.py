import json
import logging
import time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text

from open_webui.internal.db import Base, JSONField, get_db

log = logging.getLogger(__name__)

####################
# Booking DB Schema
####################


class Booking(Base):
    __tablename__ = "booking"

    id = Column(String, primary_key=True)
    title = Column(Text, nullable=True)
    client = Column(Text, nullable=True)
    date = Column(String, nullable=True)
    start_time = Column(String, nullable=True)
    end_time = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    room_name = Column(String, nullable=True)
    room_code = Column(String, nullable=True)
    room_floor = Column(Integer, nullable=True)
    room_building = Column(String, nullable=True)
    room_equipment = Column(JSONField, nullable=True)
    requester = Column(Text, nullable=True)
    invitees = Column(JSONField, nullable=True)
    status = Column(String, default="draft")
    approver = Column(JSONField, nullable=True)
    admin_note = Column(Text, nullable=True)
    catering = Column(JSONField, nullable=True)
    email_sent = Column(Boolean, default=False)
    email_details = Column(JSONField, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class BookingModel(BaseModel):
    id: str
    title: Optional[str] = None
    client: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    capacity: Optional[int] = None
    location: Optional[str] = None
    room_name: Optional[str] = None
    room_code: Optional[str] = None
    room_floor: Optional[int] = None
    room_building: Optional[str] = None
    room_equipment: Optional[list] = None
    requester: Optional[str] = None
    invitees: Optional[list] = None
    status: str = "draft"
    approver: Optional[dict] = None
    admin_note: Optional[str] = None
    catering: Optional[dict] = None
    email_sent: bool = False
    email_details: Optional[dict] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class BookingForm(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    client: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    capacity: Optional[int] = None
    location: Optional[str] = None
    room_name: Optional[str] = None
    room_code: Optional[str] = None
    room_floor: Optional[int] = None
    room_building: Optional[str] = None
    room_equipment: Optional[list] = None
    requester: Optional[str] = None
    invitees: Optional[list] = None
    status: str = "draft"
    approver: Optional[dict] = None
    admin_note: Optional[str] = None
    catering: Optional[dict] = None
    email_sent: bool = False
    email_details: Optional[dict] = None


class BookingPatchForm(BaseModel):
    status: Optional[str] = None
    admin_note: Optional[str] = None


####################
# Booking Table CRUD
####################


class BookingTable:
    def insert_or_update(self, form: BookingForm) -> Optional[BookingModel]:
        now = int(time.time())
        with get_db() as db:
            existing = db.query(Booking).filter_by(id=form.id).first()
            if existing:
                for key, value in form.model_dump(exclude_unset=True).items():
                    setattr(existing, key, value)
                existing.updated_at = now
                db.commit()
                db.refresh(existing)
                return BookingModel.model_validate(existing)
            else:
                booking = Booking(
                    **form.model_dump(),
                    created_at=now,
                    updated_at=now,
                )
                db.add(booking)
                db.commit()
                db.refresh(booking)
                return BookingModel.model_validate(booking)

    def get_booking_by_id(self, id: str) -> Optional[BookingModel]:
        with get_db() as db:
            booking = db.query(Booking).filter_by(id=id).first()
            return BookingModel.model_validate(booking) if booking else None

    def get_bookings(self) -> list[BookingModel]:
        with get_db() as db:
            bookings = (
                db.query(Booking).order_by(Booking.created_at.desc()).all()
            )
            return [BookingModel.model_validate(b) for b in bookings]

    def patch_booking(
        self, id: str, form: BookingPatchForm
    ) -> Optional[BookingModel]:
        with get_db() as db:
            booking = db.query(Booking).filter_by(id=id).first()
            if not booking:
                return None
            if form.status is not None:
                booking.status = form.status
            if form.admin_note is not None:
                booking.admin_note = form.admin_note
            booking.updated_at = int(time.time())
            db.commit()
            db.refresh(booking)
            return BookingModel.model_validate(booking)

    def delete_booking_by_id(self, id: str) -> bool:
        with get_db() as db:
            booking = db.query(Booking).filter_by(id=id).first()
            if not booking:
                return False
            db.delete(booking)
            db.commit()
            return True

    def get_bookings_for_availability(
        self, date: str, start_time: str, end_time: str, exclude_id: Optional[str] = None
    ) -> list[str]:
        """Return room_codes occupied at the given date/time slot (approved or sent only)."""
        with get_db() as db:
            query = (
                db.query(Booking.room_code)
                .filter(
                    Booking.date == date,
                    Booking.status.in_(["approved", "sent"]),
                    Booking.start_time < end_time,
                    Booking.end_time > start_time,
                )
            )
            if exclude_id:
                query = query.filter(Booking.id != exclude_id)
            rows = query.distinct().all()
            return [r[0] for r in rows if r[0]]


Bookings = BookingTable()
