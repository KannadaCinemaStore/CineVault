from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DATABASE_NAME

client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client[DATABASE_NAME]
files = db.files
users = db.users
banned = db.banned
searches = db.searches

async def init_db():
    await client.admin.command("ping")
    await files.create_index([("file_name", "text"), ("caption", "text")])
    await files.create_index("file_unique_id", unique=True)
    await files.create_index("created_at")
    await users.create_index("user_id", unique=True)
    await searches.create_index("created_at")

async def save_user(user):
    await users.update_one({"user_id": user.id}, {"$set": {"first_name": user.first_name or "", "username": user.username or ""}, "$setOnInsert": {"joined_at": __import__("datetime").datetime.utcnow()}}, upsert=True)

async def is_banned(user_id: int) -> bool:
    return await banned.find_one({"user_id": user_id}) is not None

async def record_search(user_id: int, query: str):
    from datetime import datetime
    await searches.insert_one({"user_id": user_id, "query": query, "created_at": datetime.utcnow()})

async def add_file(message):
    media = message.document or message.video or message.audio
    if not media:
        return False
    from datetime import datetime
    name = getattr(media, "file_name", None) or (message.caption or "Media file")
    doc = {
        "file_unique_id": media.file_unique_id,
        "file_id": media.file_id,
        "file_name": name,
        "caption": message.caption or "",
        "file_size": getattr(media, "file_size", 0),
        "media_type": "document" if message.document else "video" if message.video else "audio",
        "created_at": datetime.utcnow(),
        "source_chat": message.chat.id,
        "source_message_id": message.id,
    }
    await files.update_one({"file_unique_id": media.file_unique_id}, {"$setOnInsert": doc}, upsert=True)
    return True
