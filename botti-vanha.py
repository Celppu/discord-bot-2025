import os
import requests
import json
import discord
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta
import pytz
from fuzzywuzzy import fuzz
import re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MODEL_URL = "http://127.0.0.1:1234/v1/chat/completions"

chathis = "This is a discord chat. Make short helpful answer, tag users using @username \n"
inUse = False
tokenshist = []

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected!')

def remove_bot_mention(text):
    text = text.replace(f'<@{client.user.id}>', '')
    text = text.replace(f'<@!{client.user.id}>', '')
    text = text.replace(f'@{client.user.id}', '')
    text = text.replace(f'@{client.user.name}', '')
    return text

async def replace_mentions_with_names(message):
    content = message.content
    for mention in message.mentions:
        content = content.replace(f'<@{mention.id}>', f'@{mention.name}')
    for mention in message.role_mentions:
        content = content.replace(f'<@&{mention.id}>', f'@{mention.name}')
    return content

def replace_usernames_with_mentions(text):
    usernames = re.findall(r'@(\w+)', text)
    for username in usernames:
        user = discord.utils.get(client.get_all_members(), name=username)
        if user:
            text = text.replace(f'@{username}', f'<@{user.id}>')
    return text

def similar_enough(username1, username2, allowed_ratio=70):
    username1, username2 = re.sub(r'\W+', '', username1), re.sub(r'\W+', '', username2)
    return fuzz.ratio(username1.lower(), username2.lower()) >= allowed_ratio

def replace_usernames_with_mentions_fuzzy(text):
    usernames = re.findall(r'@(\w+)', text)
    for username in usernames:
        users = client.get_all_members()
        user = next((u for u in users if similar_enough(username, u.name)), None)
        if user:
            text = text.replace(f'@{username}', f'<@{user.id}>')
    return text

def query_llm(chat_history):
    payload = {
        "model": "llama-3.2-lb-instruct",
        "messages": [{"role": "system", "content": "Always answer in 2020 tiktok brain rot."}] + [
            {"role": "user" if "User" in msg else "assistant", "content": msg.split(':', 1)[1].strip()}
            for msg in chat_history.split('\n') if msg.strip()
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": True
    }
    
    # Debug print query payload
    print(json.dumps(payload, indent=4))
    
    try:
        response = requests.post(MODEL_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), stream=True)
        response.raise_for_status()
        
        outtext = ""
        for line in response.iter_lines(decode_unicode=True):
            if line and line != "data: [DONE]":
                try:
                    data = json.loads(line[6:])
                    token = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if token:
                        outtext += token
                except json.JSONDecodeError:
                    continue
        return outtext
    except requests.exceptions.RequestException as e:
        return f"SYSTEM - An error occurred: {e}"

async def edit_response(response, text):
    if len(text) > 1 and not text.isspace():
        await response.edit(content=text)

response = None

@client.event
async def on_message(message):
    global inUse, chathis, response
    
    if message.author == client.user or not message.mentions:
        return
    
    if client.user in message.mentions:
        try:
            msg = await replace_mentions_with_names(message)
            msg = remove_bot_mention(msg)
            
            user = message.author
            bot = client.user
            
            if inUse:
                await message.channel.send("```thinkthönkin already somewhere```")
            else:
                inUse = True
                response = await message.channel.send("```thinking...```")
                
                chathis = ""
                now = datetime.now(pytz.utc)
                day_ago = now - timedelta(days=1)
                messages = []
                
                async for m in message.channel.history(limit=30):
                    if m.created_at > day_ago and m.id != response.id:
                        if bot in m.mentions or m.author == bot:
                            contents = await replace_mentions_with_names(m)
                            contents = remove_bot_mention(contents)
                            usertype = "Assistant" if m.author == bot else "User"
                            messages.append(f"{usertype} {m.author}: {contents}\n")
                
                messages.reverse()
                chathis = "".join(messages) + f"Assistant {bot}: "
                
                outtext = query_llm(chathis)
                await edit_response(response, outtext)
                
                outtext_with_mentions = replace_usernames_with_mentions_fuzzy(outtext)
                if outtext_with_mentions != outtext and len(outtext_with_mentions) > 1:
                    await edit_response(response, outtext_with_mentions)
                
                inUse = False
                print("\ndone")
        except Exception as e:
            inUse = False
            await response.edit(content=f"SYSTEM - An error occurred: {e} -")

client.run(TOKEN)
