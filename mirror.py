import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SOURCE = int(os.getenv("SOURCE_CHANNEL"))
DEST = int(os.getenv("DEST_GROUP"))

PROGRESS_FILE = "last_posted.txt"

user_client = TelegramClient("user_session", API_ID, API_HASH)

def get_last_posted_id():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            val = f.read().strip()
            if val:
                return int(val)
    return 0

def save_last_posted_id(msg_id):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(msg_id))

def reset_progress():
    """Reset progress to start from beginning."""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

async def send_message(message):
    try:
        if message.media:
            path = await user_client.download_media(message.media)
            if path:
                caption = message.text or ""
                await user_client.send_file(DEST, path, caption=caption)
                os.remove(path)
            elif message.text:
                await user_client.send_message(DEST, message.text)
        elif message.text:
            await user_client.send_message(DEST, message.text)
    except Exception as e:
        print(f"Skipped message {message.id}: {e}")

async def scrape_and_post():
    """One full cycle through the source channel."""
    try:
        entity = await user_client.get_entity(SOURCE)
        print(f"Found channel: {entity.title}")
    except Exception as e:
        print(f"Could not resolve channel: {e}")
        return

    last_id = get_last_posted_id()
    if last_id:
        print(f"Resuming from message ID: {last_id}")
    else:
        print("Starting from the beginning...")

    count = 0
    async for message in user_client.iter_messages(entity, reverse=True, min_id=last_id):
        await send_message(message)
        save_last_posted_id(message.id)
        count += 1
        print(f"Posted message {count} (ID: {message.id}) — waiting 30 min...")
        await asyncio.sleep(1800)  # 30 minutes

    print(f"Cycle complete! Posted {count} messages.")
    return count

@user_client.on(events.NewMessage(chats=SOURCE))
async def handle_new_message(event):
    print(f"New message detected: {event.message.id}")
    await send_message(event.message)

async def main():
    await user_client.start()

    me = await user_client.get_me()
    print(f"Logged in as: {me.first_name} {me.last_name or ''}")

    print("Loading dialogs...")
    await user_client.get_dialogs()
    print("Dialogs loaded.")

    cycle = 1
    while True:
        print(f"\n🔄 Starting cycle #{cycle}...")
        count = await scrape_and_post()

        if count == 0:
            # No new messages found, already at the end — reset and loop
            print("All posts done! Resetting to start from beginning...")
            reset_progress()
        else:
            # Reached end of channel, reset for next cycle
            print("End of channel reached! Resetting for next cycle...")
            reset_progress()

        cycle += 1
        print(f"Next cycle starting now...")

if __name__ == "__main__":
    asyncio.run(main())