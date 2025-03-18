import os
import random
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Enable required intents
intents = discord.Intents.default()
#intents.message_content = True  # REQUIRED to read message content

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


@client.event
async def on_message(message):
    if message.author == client.user:
        return  # Ignore messages from itself

    if message.author == client.user or not message.mentions:
        return

    username = message.author.name
    user_message = message.content.lower().replace(f'<@{client.user.id}>', '').strip()  # Remove bot mention
    print(f'Message "{user_message}" by {username}')

    # Respond to simple messages
    if user_message in ["hello", "hi"]:
        await message.channel.send(f'Hello {username}')
    elif user_message == "bye":
        await message.channel.send(f'Bye {username}')
    elif user_message == "tell me a joke":
        jokes = [
            "Can someone please shed more light on how my lamp got stolen?",
            "Why is she called Ilene? She stands on equal legs.",
            "What do you call a gazelle in a lion’s territory? Denzel."
        ]
        await message.channel.send(random.choice(jokes))
    else:
        await message.channel.send(f'Sorry, I did not understand "{user_message}"')

client.run(TOKEN)
