import asyncio
from pyrogram.errors import UserNotParticipant, PeerIdInvalid, ChannelPrivate
from rapidfuzz import fuzz, process
from config import FORCE_SUB_CHANNELS, AUTO_DELETE_SECONDS

async def subscribed(client, user_id: int) -> bool:
    for channel in FORCE_SUB_CHANNELS:
        try:
            await client.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return False
        except (PeerIdInvalid, ChannelPrivate):
            # A misconfigured/private channel must be fixed by the owner; don't silently block everyone.
            continue
        except Exception:
            continue
    return True

async def schedule_delete(client, chat_id: int, message_ids: list[int]):
    if AUTO_DELETE_SECONDS <= 0:
        return
    await asyncio.sleep(AUTO_DELETE_SECONDS)
    for message_id in message_ids:
        try:
            await client.delete_messages(chat_id, message_id)
        except Exception:
            pass

def rank_results(query: str, docs: list[dict], limit: int):
    names = [d.get("file_name", "") for d in docs]
    ranked = process.extract(query, names, scorer=fuzz.WRatio, limit=limit)
    by_name = {}
    for doc in docs:
        by_name.setdefault(doc.get("file_name", ""), []).append(doc)
    output = []
    for name, score, _ in ranked:
        if score >= 38:
            output.extend(by_name.get(name, []))
    return output[:limit]
