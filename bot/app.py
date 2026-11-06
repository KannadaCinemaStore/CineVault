from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN, ADMINS
from .database import init_db
from .handlers import (
    start_handler, help_handler, index_handler, search_handler, callback_handler,
    recent_handler, trending_handler, random_handler, stats_handler,
    ban_handler, unban_handler, broadcast_handler,
)

app = Client("cinevault_autofilter_v3", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

app.on_message(filters.private & filters.command("start"))(start_handler)
app.on_message(filters.private & filters.command("help"))(help_handler)
app.on_message(filters.command("recent"))(recent_handler)
app.on_message(filters.command("trending"))(trending_handler)
app.on_message(filters.command("random"))(random_handler)
app.on_message(filters.command("stats"))(stats_handler)
app.on_message(filters.command("ban"))(ban_handler)
app.on_message(filters.command("unban"))(unban_handler)
app.on_message(filters.command("broadcast"))(broadcast_handler)
app.on_message((filters.group | filters.channel) & (filters.document | filters.video | filters.audio))(index_handler)
app.on_message(filters.private & filters.text)(search_handler)
app.on_callback_query()(callback_handler)

async def main():
    await init_db()
    await app.start()
    me = await app.get_me()
    print(f"CineVault Auto Filter V3 started as @{me.username}")
    await __import__("asyncio").Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
