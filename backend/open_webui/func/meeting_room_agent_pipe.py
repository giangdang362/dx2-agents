"""
title: Meeting Room Agent
description: CMC Global meeting room booking assistant — book, list, and cancel meetings
requirements: aiohttp
"""

import hashlib
import json as _json
import re
from datetime import datetime, timedelta
from typing import Callable

import aiohttp
from pydantic import BaseModel, Field

from open_webui.models.demo.meeting_rooms import Bookings, BookingForm, BookingPatchForm

# ---------------------------------------------------------------------------
# Inlined reference data (from data/meeting_data.py)
# ---------------------------------------------------------------------------

PROJECT_TYPE = "Service Center (SC)"
ISSUE_TYPE = "General Request"
REGIONS = "Vietnam"
# LOCATIOn =code + building + floorF

JIRA_TICKET_PREFIX = "https://pms.cmcglobal.com.vn/SC-"
OMS_TICKET_PREFIX = "https://office.cmcglobal.com.vn/meeting?id=&date="

MEETING_ROOMS = [
    # ── HCM (4 rooms, ascending capacity) ────────────────────────────────────
    {
        "id": "rose",
        "name": "Rose",
        "code": "HCM",
        "building": "Creative Space",
        "floor": 4,
        "capacity": 8,
        "equipment": ["projector", "whiteboard", "sound"],
        "available": True,
    },
    {
        "id": "daisy",
        "name": "Daisy",
        "code": "HCM",
        "building": "Creative Space",
        "floor": 2,
        "capacity": 10,
        "equipment": ["tv", "video_conf", "ac"],
        "available": True,
    },
    {
        "id": "blossom",
        "name": "Blossom",
        "code": "HCM",
        "building": "Creative Space",
        "floor": 5,
        "capacity": 15,
        "equipment": ["projector", "whiteboard", "ac"],
        "available": True,
    },
    {
        "id": "sunflower",
        "name": "Sun Flower",
        "code": "HCM",
        "building": "Creative Space",
        "floor": 3,
        "capacity": 20,
        "equipment": ["projector", "tv", "video_conf", "phone"],
        "available": True,
    },
    # ── HN (2 rooms, ascending capacity) ─────────────────────────────────────
    {
        "id": "orchid",
        "name": "Orchid",
        "code": "HN",
        "building": "789 Tower",
        "floor": 8,
        "capacity": 18,
        "equipment": ["projector", "tv", "video_conf", "ac"],
        "available": True,
    },
    {
        "id": "lotus",
        "name": "Lotus",
        "code": "HN",
        "building": "CMC Tower",
        "floor": 6,
        "capacity": 25,
        "equipment": ["projector", "tv", "video_conf", "phone", "mic"],
        "available": True,
    },
    # ── DN (2 rooms, ascending capacity) ─────────────────────────────────────
    {
        "id": "jasmine",
        "name": "Jasmine",
        "code": "DN",
        "building": "G8",
        "floor": 3,
        "capacity": 12,
        "equipment": ["projector", "tv", "video_conf"],
        "available": True,
    },
    {
        "id": "tulip",
        "name": "Tulip",
        "code": "DN",
        "building": "G8",
        "floor": 5,
        "capacity": 16,
        "equipment": ["projector", "whiteboard", "ac", "sound"],
        "available": True,
    },
]

ADMINS = [
    {
        "id": "admin-hn",
        "name": "Lê Thuý Loan",
        "email": "ltloan@cmcglobal.vn",
        "role": "Hanoi Office Admin",
        "department_code": "HN",
        "floor": 6,
    },
    {
        "id": "admin-dn",
        "name": "Nguyễn Thị Tình Yên",
        "email": "nttyen@cmcglobal.vn",
        "role": "Da Nang Office Admin",
        "department_code": "DN",
        "floor": 3,
    },
    {
        "id": "admin-hcm",
        "name": "Lê Thị Tuyết Hảo",
        "email": "ltthao1@cmcglobal.vn",
        "role": "Ho Chi Minh City Office Admin",
        "department_code": "HCM",
        "floor": 3,
    },
]

CATERING_OPTIONS = [
    {
        "id": "tea-coffee",
        "name": "Tea + Coffee + Pastries",
        "price": 35000,
        "per_person": True,
        "icon": "☕",
    },
    {
        "id": "coffee",
        "name": "Coffee + Pastries",
        "price": 30000,
        "per_person": True,
        "icon": "🥐",
    },
    {
        "id": "water",
        "name": "Mineral Water",
        "price": 10000,
        "per_person": True,
        "icon": "💧",
    },
    {
        "id": "buffet",
        "name": "Lunch Buffet",
        "price": 150000,
        "per_person": True,
        "icon": "🍱",
    },
    {
        "id": "lunch-box",
        "name": "Lunch Box",
        "price": 50000,
        "per_person": True,
        "icon": "🍚",
    },
    {
        "id": "fruit",
        "name": "Fresh Fruits",
        "price": 25000,
        "per_person": True,
        "icon": "🍎",
    },
]

DEPARTMENTS = [
    {
        "id": "dept-hno-1",
        "name": "Technical Department",
        "code": "HNO",
        "floor": 1,
        "admin_id": "admin-hno",
    },
    {
        "id": "dept-hno-2",
        "name": "Business Department",
        "code": "HNO",
        "floor": 1,
        "admin_id": "admin-hno",
    },
    {
        "id": "dept-hno-3",
        "name": "Marketing Department",
        "code": "HNO",
        "floor": 1,
        "admin_id": "admin-hno",
    },
    {
        "id": "dept-dno-1",
        "name": "Marketing Department",
        "code": "DNO",
        "floor": 2,
        "admin_id": "admin-dno",
    },
    {
        "id": "dept-dno-2",
        "name": "HR Department",
        "code": "DNO",
        "floor": 2,
        "admin_id": "admin-dno",
    },
    {
        "id": "dept-dno-3",
        "name": "Sales Department",
        "code": "DNO",
        "floor": 2,
        "admin_id": "admin-dno",
    },
    {
        "id": "dept-hcmo-1",
        "name": "Finance Department",
        "code": "HCMO",
        "floor": 3,
        "admin_id": "admin-hcmo",
    },
    {
        "id": "dept-hcmo-2",
        "name": "Legal Department",
        "code": "HCMO",
        "floor": 3,
        "admin_id": "admin-hcmo",
    },
    {
        "id": "dept-hcmo-3",
        "name": "External Affairs Department",
        "code": "HCMO",
        "floor": 3,
        "admin_id": "admin-hcmo",
    },
]

# ---------------------------------------------------------------------------
# System prompt builders
# ---------------------------------------------------------------------------


def _build_room_list_text() -> str:
    lines = []
    for r in MEETING_ROOMS:
        equip = ", ".join(r["equipment"]) if r["equipment"] else "none"
        lines.append(
            f"  - {r['name']} (id: {r['id']}) | Office: {r['code']}"
            f" | Building: {r['building']}"
            f" | Floor: {r['floor']} | Capacity: {r['capacity']} people | Equipment: {equip}"
        )
    return "\n".join(lines)


def _build_admin_list_text() -> str:
    lines = []
    for a in ADMINS:
        lines.append(
            f"  - {a['department_code']}: {a['name']} <{a['email']}> (Floor {a['floor']})"
        )
    return "\n".join(lines)


async def _fetch_active_bookings_text(api_base_url: str, user_email: str = "") -> str:
    """Fetch non-cancelled/rejected bookings from the API server for the system prompt."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{api_base_url}/api/v1/meeting-rooms/bookings",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return "  (No active meetings)"
                bookings = await resp.json()
    except Exception:
        return "  (No active meetings)"

    active = [
        b
        for b in bookings
        if b.get("status") not in ("cancelled", "rejected")
        and (not user_email or (b.get("requester") or "").lower() == user_email.lower())
    ]
    active.sort(key=lambda b: (b.get("date", ""), b.get("start_time", "")))

    if not active:
        return "  (No active meetings)"
    lines = []
    for b in active:
        client = b.get("client") or ""
        catering = b.get("catering")
        catering_str = "none"
        if catering and isinstance(catering, dict) and catering.get("items"):
            catering_str = ", ".join(
                f"{it.get('name','')} x{it.get('quantity',1)}"
                for it in catering["items"]
            )
        lines.append(
            f"  - [{b['id']}] \"{b.get('title','?')}\""
            + (f" | Client: {client}" if client else "")
            + f" | {b.get('date','?')} {b.get('start_time','?')} – {b.get('end_time','?')}"
            f" | Room: {b.get('room_code','?')} | Office: {b.get('location','?')}"
            f" | Status: {b.get('status','?')}"
            f" | Catering: {catering_str}"
        )
    return "\n".join(lines)


def _get_current_datetime():
    now = datetime.now()
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    def _nwd(wd: int) -> str:
        """Next occurrence of weekday wd (0=Mon…6=Sun), never today."""
        days = wd - now.weekday()
        if days <= 0:
            days += 7
        return (now + timedelta(days=days)).strftime("%Y-%m-%d")

    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": day_names[now.weekday()],
        "timestamp": int(now.timestamp()),
        "tomorrow": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        "day_after_tomorrow": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
        "next_week": (now + timedelta(days=7)).strftime("%Y-%m-%d"),
        "next_monday": _nwd(0),
        "next_tuesday": _nwd(1),
        "next_wednesday": _nwd(2),
        "next_thursday": _nwd(3),
        "next_friday": _nwd(4),
        "next_saturday": _nwd(5),
        "next_sunday": _nwd(6),
    }


def _next_weekday(today, weekday: int):
    days = weekday - today.weekday()
    if days <= 0:
        days += 7
    return today + timedelta(days=days)


def _resolve_dates(text: str) -> str:
    """Replace Vietnamese/English relative-date phrases with absolute DD/MM/YYYY strings."""
    if not isinstance(text, str):
        return text
    today = datetime.now()
    fmt = lambda d: d.strftime("%d/%m/%Y")  # noqa:     E731

    pairs = [
        (r"the day after tomorrow", fmt(today + timedelta(days=2))),
        (r"ngày kìa", fmt(today + timedelta(days=2))),
        (r"ngày kia", fmt(today + timedelta(days=2))),
        (r"2 ngày nữa", fmt(today + timedelta(days=2))),
        (r"ngày mai", fmt(today + timedelta(days=1))),
        (r"tuần tới", fmt(today + timedelta(days=7))),
        (r"tuần sau", fmt(today + timedelta(days=7))),
        (r"next week", fmt(today + timedelta(days=7))),
        (r"tomorrow", fmt(today + timedelta(days=1))),
        (
            r"thứ hai tuần sau|thứ 2 tuần sau|thứ hai này|thứ 2 này",
            fmt(_next_weekday(today, 0)),
        ),
        (
            r"thứ ba tuần sau|thứ 3 tuần sau|thứ ba này|thứ 3 này",
            fmt(_next_weekday(today, 1)),
        ),
        (
            r"thứ tư tuần sau|thứ 4 tuần sau|thứ tư này|thứ 4 này",
            fmt(_next_weekday(today, 2)),
        ),
        (
            r"thứ năm tuần sau|thứ 5 tuần sau|thứ năm này|thứ 5 này",
            fmt(_next_weekday(today, 3)),
        ),
        (
            r"thứ sáu tuần sau|thứ 6 tuần sau|thứ sáu này|thứ 6 này",
            fmt(_next_weekday(today, 4)),
        ),
        (
            r"thứ bảy tuần sau|thứ 7 tuần sau|thứ bảy này|thứ 7 này",
            fmt(_next_weekday(today, 5)),
        ),
        (r"chủ nhật tuần sau|chủ nhật này", fmt(_next_weekday(today, 6))),
        (r"next monday", fmt(_next_weekday(today, 0))),
        (r"next tuesday", fmt(_next_weekday(today, 1))),
        (r"next wednesday", fmt(_next_weekday(today, 2))),
        (r"next thursday", fmt(_next_weekday(today, 3))),
        (r"next friday", fmt(_next_weekday(today, 4))),
        (r"next saturday", fmt(_next_weekday(today, 5))),
        (r"next sunday", fmt(_next_weekday(today, 6))),
    ]
    for pattern, replacement in pairs:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


_ROOM_LIST = _build_room_list_text()
_ADMIN_LIST = _build_admin_list_text()

_BOOKING_AGENT_SYSTEM_PROMPT_STATIC = f"""
CRITICAL LANGUAGE RULE: You MUST respond ONLY in English, regardless of the language
the user writes in. Do NOT reply in Vietnamese, Chinese, Japanese, or any other language.
Every single response — greetings, confirmations, errors, table values, refusals, goodbyes —
must be in English. If the user writes in Vietnamese, understand the request but REPLY IN ENGLISH.

You are the CMC Global Meeting Room Booking Assistant.

LANGUAGE POLICY: ALL responses must be in English. This is non-negotiable and overrides
any other instruction about language matching. Both column labels AND values in tables
must be in English.

══════════════════════════════════════
YOUR ROLE
══════════════════════════════════════
- Your primary role is meeting room booking for CMC Global, but you ALSO handle:
    • Natural conversation during or after the booking flow — e.g. "cảm ơn", "ok", "được rồi",
      "thôi nhé", greetings, goodbyes, short clarifications.
    • Follow-up questions after a cancellation — e.g. "đặt phòng mới", "kiểm tra phòng trống".
    • Any message that is clearly part of or related to the booking / cancellation workflow.
- Only refuse with the standard apology for topics clearly outside booking entirely
  (e.g. IT support, HR questions, general company info). Use your judgement.
  Refusal message: "Sorry, I can only help with meeting room bookings at CMC Global. Would you like to book a room?"
- AMENDMENT DETECTION: If this conversation already contains a ```booking``` block
  AND the user's latest message mentions any meeting detail (attendee count, date, time,
  room, location) without starting a completely new unrelated request, treat it as an
  update to the previously discussed booking. Re-run steps 1–6, carrying over all fields
  from the previous booking except the ones the user explicitly changed.
  IMPORTANT: For updates, after user confirms, output a ```booking_list block (NOT a
  ```booking block). The booking_list block should contain a JSON array with a single
  object using the SAME booking id as the original, with the updated fields.
  This shows the compact upcoming-meeting card instead of the full booking card.
  NEVER refuse with "I only help with bookings" when there is prior booking context.
- Only greet the user if their message contains ZERO booking information (e.g. "xin chào", "hi").
  If ANY meeting detail is present (date, time, purpose, person name), skip all pleasantries
  and go DIRECTLY to step 5 of the BOOKING WORKFLOW — no preamble, but still ask the
  REQUIRED questions from step 5 (duration, catering) if they are missing.
- ALWAYS respond in English regardless of the language the user writes in.
  Even if the user writes in Vietnamese, understand their request but reply in English.
- IMPORTANT: Both table labels (first column) AND values (second column) must be in English.

══════════════════════════════════════
BOOKING WORKFLOW
══════════════════════════════════════

1. UNDERSTAND the user's intent naturally — they may describe it casually.
   Extract these fields:
   - Meeting title / purpose (who they're meeting with, what it's about)
   - Client name (`client` field) — ALWAYS extract the name of the person, company, or team being
     met with (e.g. "Sony", "Kuok Group", "HR team"). This field is used for cancellation lookup,
     so it must always be populated. If not explicitly stated, infer it from the meeting title.
   - Date → convert to DD/MM/YYYY (resolve relative dates using the rule above) - eg: 07/12/2026
   - Start time → HH:MM
   - End time (default: start + 1 hour if not given)
   - Number of attendees / capacity (default: 5 if not given)
   - City/office preference (default: Hanoi → HN if not given)

2. CITY-TO-OFFICE MAPPING — users say city names, not codes:
   - "Hà Nội" / "Hanoi" / not specified → HN (Hà Nội Office)  ← DEFAULT
   - "Đà Nẵng" / "Da Nang"              → DN (Đà Nẵng Office)
   - "Hồ Chí Minh" / "Ho Chi Minh" / "HCMC" / "Sài Gòn" / "Saigon" → HCM (HCM Office)

3. ROOM SELECTION — STRICT RULES:
   ⚠️  You MUST ONLY use rooms from the AVAILABLE ROOMS list in this prompt.
   ⚠️  NEVER invent, fabricate, or reference any room not in that list.
       Hallucinated names like "Phòng Họp A2", "B3", "Conference Room 1", etc. are FORBIDDEN.
   ⚠️  The room_name and room_code in the booking JSON MUST exactly match an entry in that list.

   Pick the SMALLEST room in the chosen office whose capacity ≥ requested attendees:
   - HN  ascending: Orchid (id: orchid, 18p) → Lotus (id: lotus, 25p)
   - DN  ascending: Jasmine (id: jasmine, 12p) → Tulip (id: tulip, 16p)
   - HCM ascending: Rose (id: rose, 8p) → Daisy (id: daisy, 10p) → Blossom (id: blossom, 15p) → Sun Flower (id: sunflower, 20p)

   AMENITY FILTERING: If the user requests specific equipment/amenities (e.g. "lấy phòng có TV",
   "cần điều hoà", "phòng có projector"), filter rooms to those that have the requested equipment
   in their Equipment list. Equipment keywords: projector, tv, video_conf, phone, whiteboard, ac, sound, mic.
   Map Vietnamese requests: "tivi"/"TV" → tv, "điều hoà"/"máy lạnh" → ac, "máy chiếu" → projector,
   "bảng trắng" → whiteboard, "micro" → mic, "âm thanh" → sound, "họp video" → video_conf.
   If no room matches both capacity AND amenity requirements, suggest the closest match and explain.

4. APPROVER — assign the admin for the selected office:
   - HN  → Nguyễn Văn Trang <nvtrang3@cmcglobal.vn> (Floor 6)
   - DN  → Trần Thị Hương <thuong5@cmcglobal.vn> (Floor 3)
   - HCM → Lê Minh Khoa <lmkhoa2@cmcglobal.vn> (Floor 3)

5. REQUIRED QUESTIONS — before proceeding to step 6, you MUST resolve these fields.
   If any are missing, ask the user in a SINGLE combined question (never one at a time):
   ✅ title/purpose — if completely absent
   ✅ date          — ONLY if there is zero date hint (no day, no relative expression, nothing)
   ✅ start_time    — if the user has NOT mentioned a start time. Do NOT default silently.
   ✅ duration      — Ask "Cuộc họp kéo dài bao lâu?" ONLY if the user has not already mentioned
                      duration or end time. Do NOT default to 1 hour. Calculate end_time = start_time + duration.
   ✅ catering      — Ask "Bạn có muốn đặt teabreak không?" ONLY if the user has not already
                      mentioned catering/teabreak in their message. If the user already requested
                      catering (e.g. "đặt teabreak", "cần catering", "order tea"), skip this question
                      and default to "Trà + Cà phê + Bánh" unless they specified otherwise.
                      If user explicitly declines (e.g. "không cần teabreak") → set catering to none.
   ❌ NEVER ask about: number of attendees, location, city, room

   Apply these defaults SILENTLY (do not mention them):
   - Attendees   → 5 people
   - Location    → HN (Hà Nội)
   - Catering    → Trà + Cà phê + Bánh (default if user says yes to catering)

   As soon as title + date + start_time + duration + catering preference are known, go to step 6.

6. CONFIRMATION SUMMARY — once all required fields are resolved, present the booking
   details in a structured table and ask the user to confirm. Do NOT output a booking
   block yet. Use this exact markdown format (adapt field values):

   |---|---|
   | **Title** | Meeting with Sony client |
   | **Date** | Wednesday, 05/03/2026 |
   | **Time** | 14:00 – 15:00 |
   | **Room** | Orchid – Lotte Center Hanoi (Floor 8) |
   | **Office** | Hanoi |
   | **Capacity** | 5 |
   | **Equipment** | Projector, TV, Video Conference |
   | **Teabreak** | Tea + Coffee + Pastries (or "None") |

   Then ask the user to confirm (in English).

   Keep the table header row (| | | and |---|---|) exactly as shown.
   BOTH column labels AND values MUST be in English.

7. BOOKING CREATION — output ONLY after the user explicitly confirms (says "yes", "đặt",
   "xác nhận", "ok", "được", "đồng ý", or any clear approval).

   Output a short acknowledgement line followed by the ```booking code block so the frontend
   renders the booking card:

```booking
{{
  "id": "MTG-<OFFICE_CODE>-<uuid4_no_hyphens>",
  "title": "Meeting title",
  "client": "<client/company/visitor name>",
  "date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "end_time": "HH:MM",
  "capacity": 5,
  "location": "HN",
  "room_name": "Orchid",
  "room_code": "orchid",
  "room_floor": 8,
  "room_building": "Lotte Center Hanoi",
  "room_equipment": ["projector"],
  "requester": "<user name or email>",
  "invitees": ["email1@cmcglobal.vn"],
  "catering": {{
    "items": [{{"id": "tea-coffee", "name": "Tea + Coffee + Pastries", "price": 35000, "quantity": 1}}],
    "total": 35000
  }},
  "status": "draft",
  "approver": {{ "name": "Admin Name", "email": "admin@cmcglobal.vn" }}
}}
```

   ID format: "MTG-" + office code (HN/DN/HCM) + "-" + UUID v4 without hyphens (32 hex chars).
   Keep any explanatory text OUTSIDE the booking block.

   INVITEES: If the user mentioned any attendee emails, populate the array. Otherwise [].

   CATERING: Available catering item IDs and prices:
     - "tea-coffee": "Trà + Cà phê + Bánh" (35,000 VNĐ/person) ← DEFAULT when user says yes
     - "coffee": "Cà phê + Bánh" (30,000 VNĐ/person)
     - "water": "Nước suối" (10,000 VNĐ/person)
     - "buffet": "Buffet Trưa" (150,000 VNĐ/person)
     - "lunch-box": "Cơm hộp" (50,000 VNĐ/person)
     - "fruit": "Trái cây" (25,000 VNĐ/person)
   Set quantity to 1 per item. Calculate total = sum of (price × quantity) for all items.
   If the user declined catering, set "catering" to null.

══════════════════════════════════════
AVAILABLE ROOMS
══════════════════════════════════════
⚠️  VALID room_name values — use EXACTLY one of these strings, copy-paste only:
    {_ROOM_LIST}
    Any other name ("A2", "B3", "Phòng Họp X", "Conference Room") is a hallucination.

{_ROOM_LIST}

══════════════════════════════════════
ADMIN CONTACTS (one per office)
══════════════════════════════════════
{_ADMIN_LIST}

══════════════════════════════════════
ACTIVE BOOKINGS REGISTRY (session)
══════════════════════════════════════
{{ACTIVE_BOOKINGS}}

  ⚠️  BOOKING IDs ARE INTERNAL — NEVER reveal any booking id (e.g. MTG-HN-...) to the user
  in any message, list, summary, or confirmation. IDs are for system use only.

CONFLICT DETECTION: If the user requests a room/time that overlaps with an existing
booking above, warn them and suggest an alternative room or time slot.

BOOKING OPERATIONS (UPDATE):
  When the user wants to update/change an existing booking:
  1. Keep the SAME booking id. Show a confirmation table with the updated fields.
  2. After user confirms, output a ```booking_list block containing a JSON array with a single object
     that has the FULL updated booking details (for frontend rendering).

LISTING BOOKINGS:
  When the user asks to see their meetings ("xem lịch họp", "danh sách cuộc họp",
  "list my bookings", "upcoming meetings", "lịch họp sắp tới", etc.):
  Respond with a brief intro sentence, then output a ```booking_list block using the
  bookings from the ACTIVE BOOKINGS REGISTRY above.

  Format (use triple-backtick booking_list fence):
  Each item must include: id, title, client, date (YYYY-MM-DD), start_time (HH:MM),
  end_time (HH:MM), location (HN/HCM/DN), room_name, status, catering.
  The catering field must be the full catering object from the booking (with items array
  and total), or null if no catering was ordered.
  The id field is required internally but MUST NOT appear in any user-visible text.

  Rules:
  - Use the data from the ACTIVE BOOKINGS REGISTRY above.
  - Sort by date ascending (soonest first).
  - If no bookings found, say "Bạn chưa có lịch họp nào." (no block needed).
  - NEVER invent bookings not in the registry.
  - NEVER show or mention booking ids in your reply text.
  - Keep explanatory text OUTSIDE the booking_list block.

CANCELLATION WORKFLOW — follow these 3 steps exactly:

Step C1 — SEARCH: When user wants to cancel a meeting, search ACTIVE BOOKINGS REGISTRY above
  by matching BOTH criteria (resolve relative dates same as booking workflow — TODAY = {{CURRENT_DATE}}):
    a) Client name — fuzzy/partial case-insensitive match of the name the user mentions (e.g. "Sony")
       against the `Client` field in the registry.
    b) Date and/or time hint — match against the date/start_time shown in the registry.
  - If only one criterion given (e.g. client name only), match on that alone.
  - If no match found: reply "No matching meeting found. Could you please describe it in more detail?"
  - If multiple matches: list them and ask which one.

Step C2 — CONFIRM: Show a summary table before cancelling (do NOT cancel yet):

  |---|---|
  | **Title** | <title from registry> |
  | **Client** | <client from registry> |
  | **Date** | <formatted date> |
  | **Time** | <start_time> – <end_time> |
  | **Room** | <room_name> |
  | **Office** | <location> |
  | **Status** | <status label — use the mapping below> |

  Status label mapping:
    draft     → Pending confirmation
    pending   → Awaiting approval
    approved  → Approved
    sent      → Sent
    cancelled → Cancelled
    rejected  → Rejected

  *Are you sure you want to cancel this meeting?*

Step C3 — EXECUTE: ONLY after user explicitly confirms (says "có", "huỷ", "yes", "đồng ý",
  "xác nhận", or any clear approval), output a ```cancel_booking code block so the frontend
  updates the UI:

```cancel_booking
{{"id": "<exact booking id copied from registry — e.g. MTG-HN-abc123...>"}}
```

  Then confirm the cancellation naturally.

  ⚠️  RULES:
  - The id MUST be copied verbatim from the ACTIVE BOOKINGS REGISTRY (the [id] field).
  - NEVER invent or guess an id.
  - NEVER output a ```booking block for cancellations — only ```cancel_booking.
  - Keep all explanatory text OUTSIDE the cancel_booking block.

POST-CANCELLATION: After confirming the cancellation naturally, always follow up by
  asking what else you can help with, then suggest ONLY the following (actions this agent
  can actually perform):
    • "Book a new meeting" — start the booking workflow for a new meeting
    • "Check room availability" — check room availability for a specific date/time
  Do NOT suggest: sending emails manually, contacting admins, rescheduling, or any action
  outside the booking workflow.
  If the user responds with a decline or farewell (e.g. "no", "thanks", "bye", "that's all",
  or similar in any language), reply with a warm English goodbye, e.g.:
    "Have a productive day! I'm always here to help with your next meeting booking. 😊"
  Otherwise, proceed with the relevant workflow based on the user's response.

AVAILABILITY CHECK:
  When the user asks to check room availability ("kiểm tra phòng trống", "phòng nào còn trống",
  "check availability", "xem phòng trống", etc.):
  1. Ask for date and time range if not provided.
  2. Look at the ACTIVE BOOKINGS REGISTRY above. Rooms with 'approved' or 'sent' bookings
     that overlap the requested time slot are OCCUPIED.
  3. List all rooms in the requested office (or all offices if not specified) that are NOT
     occupied at that time, showing: room name, capacity, floor, equipment.
  4. If all rooms are occupied, suggest alternative time slots or other offices.
  Respond conversationally — no special block format needed.

CONFLICT DETECTION:
  Only 'approved' or 'sent' bookings block a room. 'pending'/'draft' do NOT block.

  When a conflict exists, do NOT just warn — always suggest concrete alternatives:
    a) Same time, different room in the same office (next room up/down in capacity tier).
    b) If ALL rooms in that office are blocked at that time: suggest the same room at a
       different time slot, or a different office with available rooms.

  Suggestions must be specific — name the room or time, e.g.:
    "Rose is already booked at that time. Would you like to book Daisy (10 people)
     at the same time, or book Rose in the afternoon (e.g. 14:00 – 15:00) instead?"

  After the user responds, proceed with the new details immediately (no extra confirmation step).

══════════════════════════════════════
HANDLING THE BOOKING APPROVAL
══════════════════════════════════════
When the user message starts with [BOOKING_APPROVED], it is handled programmatically — do NOT respond.
""".strip()


async def get_booking_agent_system_prompt(
    api_base_url: str, user_email: str = ""
) -> str:
    """Build the system prompt dynamically, injecting the current date and live booking registry."""
    dt = _get_current_datetime()
    current_date = (
        f"{dt['date']} ({dt['day_of_week']})"
        f" | tomorrow={dt['tomorrow']}"
        f" | day_after_tomorrow={dt['day_after_tomorrow']}"
        f" | next_week={dt['next_week']}"
        f" | next_monday={dt['next_monday']}"
        f" | next_tuesday={dt['next_tuesday']}"
        f" | next_wednesday={dt['next_wednesday']}"
        f" | next_thursday={dt['next_thursday']}"
        f" | next_friday={dt['next_friday']}"
        f" | next_saturday={dt['next_saturday']}"
        f" | next_sunday={dt['next_sunday']}"
    )
    active_bookings = await _fetch_active_bookings_text(api_base_url, user_email)
    return _BOOKING_AGENT_SYSTEM_PROMPT_STATIC.replace(
        "{CURRENT_DATE}", current_date
    ).replace("{ACTIVE_BOOKINGS}", active_bookings)


# ---------------------------------------------------------------------------
# Pipe class
# ---------------------------------------------------------------------------


class Pipe:
    class Valves(BaseModel):
        LLM_PROVIDER: str = Field(
            default="gemini",
            description="LLM provider: 'ollama' or 'gemini'",
        )
        OLLAMA_BASE_URL: str = Field(
            default="http://localhost:11434",
            description="Ollama base URL (used when LLM_PROVIDER=ollama)",
        )
        MODEL: str = Field(
            default="gemini-2.5-flash",
            description="Model name — Ollama model or Gemini model (e.g. gemini-2.0-flash)",
        )
        API_BASE_URL: str = Field(
            default="http://localhost:8080",
            description="Meeting Room API server base URL (booking CRUD)",
        )

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self) -> list[dict]:
        return [{"id": "meeting-room-agent", "name": "Meeting Room Agent"}]

    async def _chat(self, messages: list[dict]) -> str:
        """Non-streaming LLM call. Returns assistant text string."""
        import sys, os

        sys.path.insert(0, os.path.dirname(__file__))
        from open_webui.utils import llm_client

        try:
            if self.valves.LLM_PROVIDER == "gemini":
                return await llm_client.gemini_chat(messages, model=self.valves.MODEL)
            return await llm_client.ollama_chat(
                messages, model=self.valves.MODEL, base_url=self.valves.OLLAMA_BASE_URL
            )
        except Exception as e:
            print(f"[meeting-room-agent] LLM error: {e!r}", flush=True)
            return "Sorry, an error occurred while processing your request. Please try again."

    @staticmethod
    def _extract_last_user_message(messages: list) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                return content if isinstance(content, str) else ""
        return ""

    _ENGLISH_REINFORCEMENT = (
        "\n\n[SYSTEM REMINDER: Respond ONLY in English, regardless of the language above.]"
    )

    @classmethod
    def _enforce_english_on_messages(cls, messages: list) -> list:
        """
        Append an English-only reinforcement to the last user message.
        Returns a new list; does not mutate the input.
        """
        if not messages:
            return messages
        result = [dict(m) for m in messages]
        for i in range(len(result) - 1, -1, -1):
            msg = result[i]
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                msg["content"] = content + cls._ENGLISH_REINFORCEMENT
            elif isinstance(content, list):
                new_parts = list(content)
                for j in range(len(new_parts) - 1, -1, -1):
                    part = new_parts[j]
                    if isinstance(part, dict) and part.get("type") == "text":
                        new_parts[j] = {
                            **part,
                            "text": part.get("text", "") + cls._ENGLISH_REINFORCEMENT,
                        }
                        break
                else:
                    new_parts.append({"type": "text", "text": cls._ENGLISH_REINFORCEMENT})
                msg["content"] = new_parts
            break
        return result

    @staticmethod
    def _generate_ticket_number(booking_id: str) -> str:
        """Generate a stable 6-digit fake ticket number from booking ID."""
        h = hashlib.md5(booking_id.encode()).hexdigest()
        return str(int(h[:8], 16) % 1000000).zfill(6)

    def _generate_ticket_response(self, booking: dict) -> str:
        ticket_num = self._generate_ticket_number(booking.get("id", ""))
        jira_url = f"{JIRA_TICKET_PREFIX}{ticket_num}"

        meeting_id = booking.get("id", "")
        booking_date = booking.get("date", "")
        oms_url = (
            f"{OMS_TICKET_PREFIX.split('?')[0]}?id={meeting_id}&date={booking_date}"
        )

        # Location: code - building - floorF
        room_code = (booking.get("location") or "").upper()
        room_building = booking.get("room_building", "")
        room_floor = booking.get("room_floor", "")
        location = f"{room_code} - {room_building} - {room_floor}F"

        title = booking.get("title", "")
        date_str = booking.get("date", "")
        start = booking.get("start_time", "")
        end = booking.get("end_time", "")
        capacity = booking.get("capacity", "")
        room_name = booking.get("room_name", "")

        # Build attendees list from invitees + requester
        invitees_raw = booking.get("invitees", "")
        invitee_list: list[str] = []
        if isinstance(invitees_raw, list):
            invitee_list = [
                e.strip() for e in invitees_raw if isinstance(e, str) and e.strip()
            ]
        elif isinstance(invitees_raw, str) and invitees_raw.strip():
            invitee_list = [e.strip() for e in invitees_raw.split(",") if e.strip()]
        requester = booking.get("requester", "")
        if requester and requester not in invitee_list:
            invitee_list.insert(0, requester)
        attendees = ", ".join(invitee_list) if invitee_list else "—"

        # Build catering info for description (name x quantity, no price)
        catering_lines = ""
        catering = booking.get("catering")
        if catering and isinstance(catering, dict):
            items = catering.get("items", [])
            if items:
                parts = []
                for item in items:
                    name = item.get("name", "")
                    qty = item.get("quantity", 1)
                    parts.append(f"{name} x{qty}")
                catering_lines = "\n".join(parts)

        # Description format: "Nhờ {code}O support đặt teabreak ... để {summary.lower()}:\n{catering}"
        office_code = room_code if room_code else "HN"
        summary_lower = title.lower() if title else ""
        if catering_lines:
            # Use <br> for line breaks inside markdown table cells
            catering_br = catering_lines.replace("\n", "<br>")
            description = (
                f"Please {office_code}O support arrange tea break as follows "
                f"for {summary_lower}:<br>{catering_br}"
            )
        else:
            description = (
                f"{title} | {date_str} {start}–{end} | {room_name} | {capacity} people"
            )

        # Build JIRA section only if catering was ordered
        jira_section = ""
        if catering_lines:
            jira_section = (
                f"🔗 **Ticket Links**\n"
                f"- JIRA: [{JIRA_TICKET_PREFIX}{ticket_num}]({jira_url})\n"
                f"- OMS: [{oms_url}]({oms_url})\n\n"
                f"---\n\n"
                f"📝 **JIRA Ticket Information**\n\n"
                f"| | |\n"
                f"|---|---|\n"
                f"| **Project Type** | {PROJECT_TYPE} |\n"
                f"| **Issue Type** | {ISSUE_TYPE} |\n"
                f"| **Regions** | {REGIONS} |\n"
                f"| **Location** | {location} |\n"
                f"| **Summary** | {title} |\n"
                f"| **Description** | {description} |\n\n"
                f"---\n\n"
            )
        else:
            jira_section = (
                f"🔗 **Ticket Link**\n" f"- OMS: [{oms_url}]({oms_url})\n\n" f"---\n\n"
            )

        return (
            f"**Booking Request Approved!**\n\n"
            f"{jira_section}"
            f"**OMS Ticket Information**\n\n"
            f"| | |\n"
            f"|---|---|\n"
            f"| **Title** | {title} |\n"
            f"| **Attendees** | {attendees} |\n"
            f"| **Date** | {date_str} |\n"
        )

    async def pipe(
        self,
        body: dict,
        __user__: dict = None,
        __event_emitter__: Callable = None,
        __task__: str = None,
    ) -> str:
        messages = body.get("messages", [])

        # Title/tag generation tasks — delegate directly without booking system prompt
        if __task__:
            non_system = [m for m in messages if m.get("role") != "system"]
            return await self._chat(non_system)

        # Handle [BOOKING_APPROVED] — return ticket info directly (no LLM call)
        user_msg = self._extract_last_user_message(messages)
        if user_msg.startswith("[BOOKING_APPROVED]"):
            try:
                booking_json = user_msg[len("[BOOKING_APPROVED]") :].strip()
                print(booking_json)
                booking = _json.loads(booking_json)
                return self._generate_ticket_response(booking)
            except Exception as e:
                print(
                    f"[meeting-room-agent] Ticket generation error: {e!r}", flush=True
                )
                return "Approved successfully but unable to generate ticket information."

        user_email = (__user__ or {}).get("email", "")

        # Resolve relative date expressions in user messages
        for msg in messages:
            if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                msg["content"] = _resolve_dates(msg["content"])

        # Strip existing system messages, prepend dynamic booking prompt
        non_system = [m for m in messages if m.get("role") != "system"]
        # Reinforce English-only on the last user message
        non_system = self._enforce_english_on_messages(non_system)
        system_prompt = await get_booking_agent_system_prompt(
            self.valves.API_BASE_URL, user_email
        )
        full_messages = [{"role": "system", "content": system_prompt}] + non_system

        return await self._chat(full_messages)
