import os, json
from datetime import datetime
from zoneinfo import ZoneInfo
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import UpdateGroupCallParticipants, UpdateGroupCall

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
STRING_SESSION = os.environ["STRING_SESSION"]
GROUP_CHANNEL_MAP = json.loads(os.environ["GROUP_CHANNEL_MAP"])
TZ = ZoneInfo(os.environ.get("TZ", "Asia/Jakarta"))

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def ts():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")

CALL_TO_CHAT = {}

async def send_log(chat_id: int, text: str):
    target = GROUP_CHANNEL_MAP.get(str(chat_id))
    if not target:
        return
    try:
        await client.send_message(int(target), text)
    except Exception as e:
        print(f"[send_log error] {e}")

@client.on(events.Raw)
async def raw_handler(update):
    if isinstance(update, UpdateGroupCall):
        chat_id = getattr(update, "chat_id", None)
        call = getattr(update, "call", None)
        if call and hasattr(call, "id") and chat_id is not None:
            CALL_TO_CHAT[call.id] = chat_id
    if isinstance(update, UpdateGroupCallParticipants):
        call = getattr(update, "call", None)
        call_id = getattr(call, "id", None) if call else None
        chat_id = CALL_TO_CHAT.get(call_id)
        for p in update.participants:
            uid = getattr(p, "user_id", None)
            if not uid:
                continue
            try:
                user = await client.get_entity(uid)
                name = user.first_name or "TanpaNama"
                tag = f"@{user.username}" if user.username else name
            except Exception:
                tag = f"ID {uid}"
            action = "keluar" if getattr(p, "left", False) else "bergabung"
            if chat_id is None:
                for mapped_chat in list(GROUP_CHANNEL_MAP.keys()):
                    await send_log(int(mapped_chat), f"[{ts()}] {tag} {action} ke VC")
            else:
                await send_log(int(chat_id), f"[{ts()}] {tag} {action} ke VC")

print("Userbot aktif. Menunggu event voice chat...")
with client:
    client.run_until_disconnected()
