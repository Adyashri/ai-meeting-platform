import socketio
from app.database import SessionLocal
from app.models.meeting import Meeting

# Create Socket.io server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False
)

# Track connected users
# { room_code: [{ sid, user_name, user_id }] }
room_participants: dict = {}


def get_room_participants(room_code: str):
    return room_participants.get(room_code, [])


# ── Events ─────────────────────────────────────────────

@sio.event
async def connect(sid, environ):
    print(f"[Socket] Connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"[Socket] Disconnected: {sid}")
    # Remove from all rooms
    for room_code in list(room_participants.keys()):
        participants = room_participants[room_code]
        user = next((p for p in participants if p["sid"] == sid), None)
        if user:
            participants.remove(user)
            print(f"[Socket] {user['user_name']} left room {room_code}")
            # Notify everyone else
            await sio.emit("user_left", {
                "user_name": user["user_name"],
                "user_id":   user["user_id"],
                "participants": participants,
            }, room=room_code)
            # If room is empty
            if not participants:
                del room_participants[room_code]
            break


@sio.event
async def join_room(sid, data):
    """
    data = { room_code, user_name, user_id }
    """
    room_code = data.get("room_code", "").strip().upper()
    user_name = data.get("user_name", "Unknown")
    user_id   = data.get("user_id",   "")

    if not room_code:
        await sio.emit("error", {"message": "Room code missing"}, to=sid)
        return

    # Update meeting status in DB
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(
            Meeting.room_code == room_code
        ).first()
        if not meeting:
            await sio.emit("error", {"message": "Meeting not found"}, to=sid)
            return
        meeting_id = str(meeting.id)
    finally:
        db.close()

    # Join the socket room
    await sio.enter_room(sid, room_code)

    # Add participant
    if room_code not in room_participants:
        room_participants[room_code] = []

    # Check if already joined
    existing = next((p for p in room_participants[room_code] if p["sid"] == sid), None)
    if not existing:
        room_participants[room_code].append({
            "sid":       sid,
            "user_name": user_name,
            "user_id":   user_id,
        })

    participants = room_participants[room_code]
    print(f"[Socket] {user_name} joined room {room_code} — {len(participants)} participants")

    # Notify joining user
    await sio.emit("room_joined", {
        "room_code":    room_code,
        "meeting_id":   meeting_id,
        "participants": participants,
        "message":      f"Joined room {room_code}",
    }, to=sid)

    # Baaki sabko batao
    await sio.emit("user_joined", {
        "user_name":    user_name,
        "user_id":      user_id,
        "participants": participants,
    }, room=room_code, skip_sid=sid)


@sio.event
async def leave_room(sid, data):
    """
    data = { room_code }
    """
    room_code = data.get("room_code", "").strip().upper()
    if not room_code or room_code not in room_participants:
        return

    participants = room_participants[room_code]
    user = next((p for p in participants if p["sid"] == sid), None)
    if user:
        participants.remove(user)
        await sio.leave_room(sid, room_code)
        await sio.emit("user_left", {
            "user_name":    user["user_name"],
            "user_id":      user["user_id"],
            "participants": participants,
        }, room=room_code)
        if not participants:
            del room_participants[room_code]


@sio.event
async def send_chat(sid, data):
    """
    data = { room_code, message, user_name }
    """
    room_code = data.get("room_code", "").strip().upper()
    message   = data.get("message",   "").strip()
    user_name = data.get("user_name", "Unknown")

    if not room_code or not message:
        return

    print(f"[Socket] Chat in {room_code} — {user_name}: {message}")

    await sio.emit("new_message", {
        "user_name": user_name,
        "message":   message,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }, room=room_code)


@sio.event
async def meeting_ended(sid, data):
    """
    data = { room_code }
    """
    room_code = data.get("room_code", "").strip().upper()
    if not room_code:
        return

    print(f"[Socket] Meeting ended: {room_code}")
    await sio.emit("meeting_ended", {
        "message": "Meeting has ended",
        "room_code": room_code,
    }, room=room_code)