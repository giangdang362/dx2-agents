"""
title: Meeting Room Booking Tools
description: CRUD tools for meeting room bookings — create, update, cancel, and list.
requirements: aiohttp
version: 1.0.0
"""

import json
import aiohttp
from pydantic import BaseModel, Field
from typing import Optional


class Tools:
    class Valves(BaseModel):
        API_BASE_URL: str = Field(
            default="http://localhost:8080/api/v1/meeting-rooms",
            description="Meeting Room API base URL",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def create_booking(
        self,
        id: str,
        title: str,
        date: str,
        start_time: str,
        end_time: str,
        location: str,
        room_name: str,
        room_code: str,
        room_floor: int,
        room_building: str,
        room_equipment: list,
        approver_name: str,
        approver_email: str,
        client: str = "",
        capacity: int = 5,
        requester: str = "",
        invitees: list = [],
        catering: dict = None,
        status: str = "draft",
        __user__: dict = {},
    ) -> str:
        """
        Create a new meeting room booking. Call this ONLY after the user confirms the booking details.

        :param id: Booking ID in format MTG-<OFFICE_CODE>-<uuid4_no_hyphens>
        :param title: Meeting title/purpose
        :param date: Date in YYYY-MM-DD format
        :param start_time: Start time in HH:MM format
        :param end_time: End time in HH:MM format
        :param location: Office code (HN, DN, HCM)
        :param room_name: Room name (e.g. Orchid, Lotus)
        :param room_code: Room ID (e.g. orchid, lotus)
        :param room_floor: Floor number
        :param room_building: Building name
        :param room_equipment: List of equipment in the room
        :param approver_name: Name of the office admin who approves
        :param approver_email: Email of the office admin
        :param client: Client/company name being met with
        :param capacity: Number of attendees
        :param requester: Email of the person making the booking
        :param invitees: List of attendee emails
        :param catering: Catering details object or null
        :param status: Booking status (default: draft)
        :return: Confirmation of the created booking
        """
        booking = {
            "id": id,
            "title": title,
            "client": client,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "capacity": capacity,
            "location": location,
            "room_name": room_name,
            "room_code": room_code,
            "room_floor": room_floor,
            "room_building": room_building,
            "room_equipment": room_equipment,
            "requester": requester or __user__.get("email", ""),
            "invitees": invitees if isinstance(invitees, list) else [],
            "status": status,
            "approver": {"name": approver_name, "email": approver_email},
            "catering": catering,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.valves.API_BASE_URL}/bookings",
                    json=booking,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    result = await resp.json()
                    if resp.status == 200:
                        return f"Booking {id} created successfully."
                    return f"Failed to create booking: {result}"
        except Exception as e:
            return f"Error creating booking: {e}"

    async def update_booking(
        self,
        id: str,
        title: str = None,
        client: str = None,
        date: str = None,
        start_time: str = None,
        end_time: str = None,
        capacity: int = None,
        location: str = None,
        room_name: str = None,
        room_code: str = None,
        room_floor: int = None,
        room_building: str = None,
        room_equipment: list = None,
        invitees: list = None,
        catering: dict = None,
        __user__: dict = {},
    ) -> str:
        """
        Update an existing meeting room booking. Only the provided fields will be updated; omitted fields keep their current values.

        :param id: The booking ID to update (e.g. MTG-HN-abc123...)
        :param title: New meeting title (optional)
        :param client: New client name (optional)
        :param date: New date in YYYY-MM-DD (optional)
        :param start_time: New start time in HH:MM (optional)
        :param end_time: New end time in HH:MM (optional)
        :param capacity: New attendee count (optional)
        :param location: New office code (optional)
        :param room_name: New room name (optional)
        :param room_code: New room code (optional)
        :param room_floor: New floor number (optional)
        :param room_building: New building name (optional)
        :param room_equipment: New equipment list (optional)
        :param invitees: New invitee list (optional)
        :param catering: New catering details (optional)
        :return: Confirmation of the updated booking
        """
        try:
            # Fetch existing booking first
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.valves.API_BASE_URL}/bookings/{id}",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return f"Booking {id} not found."
                    existing = await resp.json()

            # Merge: keep existing values, override with provided ones
            for field, value in [
                ("title", title), ("client", client), ("date", date),
                ("start_time", start_time), ("end_time", end_time),
                ("capacity", capacity), ("location", location),
                ("room_name", room_name), ("room_code", room_code),
                ("room_floor", room_floor), ("room_building", room_building),
                ("room_equipment", room_equipment), ("invitees", invitees),
                ("catering", catering),
            ]:
                if value is not None:
                    existing[field] = value

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.valves.API_BASE_URL}/bookings",
                    json=existing,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        return f"Booking {id} updated successfully."
                    result = await resp.json()
                    return f"Failed to update booking: {result}"
        except Exception as e:
            return f"Error updating booking: {e}"

    async def cancel_booking(
        self,
        id: str,
        __user__: dict = {},
    ) -> str:
        """
        Cancel an existing meeting room booking by setting its status to cancelled.

        :param id: The booking ID to cancel (e.g. MTG-HN-abc123...)
        :return: Confirmation of the cancellation
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    f"{self.valves.API_BASE_URL}/bookings/{id}",
                    json={"status": "cancelled"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        return f"Booking {id} cancelled successfully."
                    result = await resp.json()
                    return f"Failed to cancel booking: {result}"
        except Exception as e:
            return f"Error cancelling booking: {e}"

    async def list_bookings(
        self,
        __user__: dict = {},
    ) -> str:
        """
        List all active (non-cancelled, non-rejected) bookings for the current user. Use this when the user asks to see their upcoming meetings.

        :return: JSON array of active bookings
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.valves.API_BASE_URL}/bookings",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return "No bookings found."
                    all_bookings = await resp.json()

            user_email = __user__.get("email", "")
            active = [
                b for b in all_bookings
                if b.get("status") not in ("cancelled", "rejected")
                and (not user_email or (b.get("requester") or "").lower() == user_email.lower())
            ]
            active.sort(key=lambda b: (b.get("date", ""), b.get("start_time", "")))

            if not active:
                return "No active bookings found."
            return json.dumps(active, ensure_ascii=False)
        except Exception as e:
            return f"Error listing bookings: {e}"
