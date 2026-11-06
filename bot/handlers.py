import math
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS, RESULTS_PER_PAGE
from .database import db, files, users, banned, searches, save_user, is_banned, record_search, add_file
from .helpers import subscribed, schedule_delete, rank_results

async def start_handler(client, message):
    user = message.from_user
    await save_user(user)
    if await is_banned(user.id):
        return await message.reply_text("⛔ You are not allowed to use this bot.")
    if not await subscribed(client, user.id):
        buttons = [[InlineKeyboardButton("Join channel", url=f"https://t.me/{c.lstrip('@')}")] for c in __import__('config').FORCE_SUB_CHANNELS if c.startswith('@')]
        return await message.reply_text("Please join the required channel(s), then send /start again.", reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
    await message.reply_text(
        f"👋 Welcome to **CineVault Auto Filter V3**!\n\n"
        "Send a movie or file name to search.\n\n"
        "✨ Smart typo-tolerant search\n📈 Trending searches · 🆕 Latest files\n🎲 Random discovery\n\n"
        "Commands: /recent /trending /random /help"
    )

async def help_handler(client, message):
    await message.reply_text("**CineVault V3 Help**\n\n• Send a title to search\n• /recent — latest indexed files\n• /trending — popular searches\n• /random — discover a random file\n• /stats — admin statistics\n\nSearch works best with a title plus language or quality.")

async def index_handler(client, message):
    if message.chat.type == "private" or (message.from_user and message.from_user.id not in ADMINS):
        return
    if await add_file(message):
        await message.reply_text("✅ File indexed.", quote=True)

async def send_page(client, message, query: str, page: int = 0):
    cursor = files.find({}, {"file_id": 1, "file_name": 1, "file_size": 1, "media_type": 1}).sort("created_at", -1).limit(500)
    docs = await cursor.to_list(length=500)
    results = rank_results(query, docs, 80)
    if not results:
        return await message.reply_text("❌ No matching files found. Try a shorter title or check the spelling.")
    pages = max(1, math.ceil(len(results) / RESULTS_PER_PAGE))
    page = max(0, min(page, pages - 1))
    chunk = results[page * RESULTS_PER_PAGE:(page + 1) * RESULTS_PER_PAGE]
    buttons = []
    for i, item in enumerate(chunk, start=page * RESULTS_PER_PAGE + 1):
        label = item.get("file_name", "File")[:48]
        size = item.get("file_size", 0)
        size_text = f" · {size / (1024*1024):.1f} MB" if size else ""
        buttons.append([InlineKeyboardButton(f"{i}. {label}{size_text}", callback_data=f"get:{item['_id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}:{query[:40]}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="noop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{page+1}:{query[:40]}"))
    buttons.append(nav)
    sent = await message.reply_text(f"🔎 Results for **{query}** · {len(results)} match(es)", reply_markup=InlineKeyboardMarkup(buttons))
    await schedule_delete(client, message.chat.id, [sent.id])

async def search_handler(client, message):
    if not message.from_user or message.text.startswith("/"):
        return
    if await is_banned(message.from_user.id):
        return
    if not await subscribed(client, message.from_user.id):
        return await message.reply_text("Please join the required channel(s) and send /start.")
    query = message.text.strip()
    if len(query) < 2:
        return
    await record_search(message.from_user.id, query)
    await send_page(client, message, query)

async def callback_handler(client, callback):
    data = callback.data or ""
    if data == "noop":
        return await callback.answer()
    if data.startswith("page:"):
        _, page, query = data.split(":", 2)
        await callback.answer()
        return await send_page(client, callback.message, query, int(page))
    if data.startswith("get:"):
        from bson import ObjectId
        try:
            item = await files.find_one({"_id": ObjectId(data.split(":", 1)[1])})
        except Exception:
            item = None
        if not item:
            return await callback.answer("File no longer exists.", show_alert=True)
        await callback.answer("Sending file…")
        try:
            sent = await client.send_cached_media(callback.from_user.id, item["file_id"], caption=f"**{item.get('file_name', 'Your file')}**\n\n✨ CineVault Auto Filter V3")
            await schedule_delete(client, callback.from_user.id, [sent.id])
        except Exception:
            await callback.message.reply_text("I couldn't send this file. Please start the bot in private and try again.")

async def recent_handler(client, message):
    docs = await files.find({}, {"file_name": 1, "file_id": 1}).sort("created_at", -1).limit(RESULTS_PER_PAGE).to_list(length=RESULTS_PER_PAGE)
    if not docs:
        return await message.reply_text("No files indexed yet.")
    rows = [[InlineKeyboardButton(d.get("file_name", "File")[:50], callback_data=f"get:{d['_id']}")] for d in docs]
    await message.reply_text("🆕 **Recently added**", reply_markup=InlineKeyboardMarkup(rows))

async def trending_handler(client, message):
    pipeline = [{"$group": {"_id": "$query", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 10}]
    rows = await searches.aggregate(pipeline).to_list(length=10)
    if not rows:
        return await message.reply_text("No search trends yet.")
    await message.reply_text("📈 **Trending searches**\n\n" + "\n".join(f"{i}. {r['_id']} — {r['count']} searches" for i, r in enumerate(rows, 1)))

async def random_handler(client, message):
    item = await files.aggregate([{"$sample": {"size": 1}}]).to_list(length=1)
    if not item:
        return await message.reply_text("No files indexed yet.")
    from bson import ObjectId
    await client.send_cached_media(message.chat.id, item[0]["file_id"], caption=f"🎲 **Random pick**\n{item[0].get('file_name', 'File')}")

async def stats_handler(client, message):
    if not message.from_user or message.from_user.id not in ADMINS:
        return
    total_files = await files.count_documents({})
    total_users = await users.count_documents({})
    total_searches = await searches.count_documents({})
    await message.reply_text(f"📊 **CineVault Stats**\n\nUsers: `{total_users}`\nIndexed files: `{total_files}`\nSearches: `{total_searches}`")

async def ban_handler(client, message):
    if not message.from_user or message.from_user.id not in ADMINS:
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply_text("Reply to a user's message with /ban.")
    target = message.reply_to_message.from_user.id
    await banned.update_one({"user_id": target}, {"$set": {"user_id": target, "by": message.from_user.id, "at": datetime.utcnow()}}, upsert=True)
    await message.reply_text(f"🚫 Banned `{target}`.")

async def unban_handler(client, message):
    if not message.from_user or message.from_user.id not in ADMINS:
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("Usage: /unban USER_ID")
    target = int(message.command[1])
    await banned.delete_one({"user_id": target})
    await message.reply_text(f"✅ Unbanned `{target}`.")

async def broadcast_handler(client, message):
    if not message.from_user or message.from_user.id not in ADMINS:
        return
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message with /broadcast to send it to all users.")
    sent = failed = 0
    async for user in users.find({}, {"user_id": 1}):
        try:
            await message.reply_to_message.copy(user["user_id"])
            sent += 1
        except Exception:
            failed += 1
    await message.reply_text(f"📣 Broadcast complete. Sent: {sent} · Failed: {failed}")
