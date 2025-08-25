import os, json
from datetime import datetime
from zoneinfo import ZoneInfo

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import UpdateGroupCallParticipants, UpdateGroupCall

# ------- konfigurasi dari environment variables -------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
STRING_SESSION = os.environ["STRING_SESSION"]

# peta grup -> channel log dalam bentuk JSON string
# contoh isi (nanti di Render):
# {"-1003333333333":"-1001111111111", "-1004444444444":"-1002222222222"}
GROUP_CHANNEL_MAP = json.loads(os.environ["GROUP_CHANNEL_MAP"])

# zona waktu default Asia/Jakarta
TZ = ZoneInfo(os.environ.get("TZ", "Asia/Jakarta"))

# ------- client userbot -------
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def ts():
    # format: 2025-08-24 21:04
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")

# simpan peta call_id -> chat_id (biar kita tahu update peserta itu milik grup mana)
CALL_TO_CHAT = {}

async def send_log(chat_id: int, text: str):
    # kirim ke channel log sesuai peta
    target = GROUP_CHANNEL_MAP.get(str(chat_id))
    if not target:
        # kalo belum dipetakan, ga usah kirim
        return
    try:
        await client.send_message(int(target), text)
    except Exception as e:
        print(f"[send_log error] {e}")

@client.on(events.Raw)
async def raw_handler(update):
    # 1) update ini muncul saat panggilan voice chat dibuat/diperbarui
    if isinstance(update, UpdateGroupCall):
        # beberapa versi Telethon menyediakan .chat_id, beberapa via .chat_instance/peer.
        # kita coba ambil chat_id via attribute yang tersedia.
        chat_id = getattr(update, "chat_id", None)
        if chat_id is None:
            # fallback: coba ambil dari entitas yang terlampir
            # kalau ga ada, kita biarin; peserta nanti tetap bisa map via partisipan
            pass
        call = getattr(update, "call", None)
        if call and hasattr(call, "id"):
            call_id = call.id
            if chat_id is not None:
                CALL_TO_CHAT[call_id] = chat_id

    # 2) update peserta join/leave
    if isinstance(update, UpdateGroupCallParticipants):
        call = getattr(update, "call", None)
        call_id = getattr(call, "id", None) if call else None
        chat_id = None

        # coba tebak chat_id dari cache call->chat
        if call_id and call_id in CALL_TO_CHAT:
            chat_id = CALL_TO_CHAT[call_id]

        # kalau belum tahu, kita coba ambil dari message terakhir user (opsional)
        # tapi biasanya mapping di atas cukup.
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

            left = bool(getattr(p, "left", False))
            action = "keluar" if left else "bergabung"

            # kalau kita belum berhasil deteksi chat_id dari call,
            # kita tulis ke semua channel yang dipetakan (daripada hilang).
            if chat_id is None:
                for mapped_chat in list(GROUP_CHANNEL_MAP.keys()):
                    await send_log(int(mapped_chat), f"[{ts()}] {tag} {action} ke VC")
            else:
                # kirim spesifik ke channel milik chat_id itu
                await send_log(int(chat_id), f"[{ts()}] {tag} {action} ke VC")

print("Userbot aktif. Menunggu event voice chat...")
with client:
    client.run_until_disconnected()
