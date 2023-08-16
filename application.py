import asyncio
import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta
import os
import base64

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

max_messages = 11
message_history = {}
sender_history = {}
nickname_history = {}
last_message_time = {}

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.event
async def on_message(message):

    channel_id = str(message.channel.id)

    if channel_id not in message_history:
        message_history[channel_id] = []
        sender_history[channel_id] = []
        nickname_history[channel_id] = []
        last_message_time[channel_id] = None

    message_history[channel_id].append(message.content)
    sender_history[channel_id].append(str(message.author))
    if message.author != bot.user:
        nickname_history[channel_id].append(message.author.display_name)
    else:
        nickname_history[channel_id].append("Charles (you)")

    if len(message_history[channel_id]) > max_messages:
        message_history[channel_id].pop(0)
        sender_history[channel_id].pop(0)
        nickname_history[channel_id].pop(0)

    formatted_history = "\n".join(f"{nickname}:{message}" for nickname, message in zip(nickname_history[channel_id], message_history[channel_id]))
    print(f"Formatted history in channel {channel_id}:\n{formatted_history}")

    if ("charles" in message.content.lower() and message.author != bot.user) or \
            (last_message_time[channel_id] is not None and datetime.now() - last_message_time[channel_id] <= timedelta(minutes=1) and sender_history[channel_id][-1] != str(bot.user)):

        messages = [
            {
                'role': 'system',
                'content': 'You are a helpful butler named Charles. You are a discord bot aimed at providing help to '
                           'the members of the server. You will be given the chatlogs of users of the server, '
                           'including your own (yours have the name Charles as the sender). Reply'
                           'with your answer in markdown format. Your response will be sent in the server to the '
                           'users. Include only your text of the response, do not include your name or any other text.'
            },
            {
                'role': 'user',
                'content': formatted_history
            }
        ]

        url = "https://nwe0dbevfl.execute-api.us-east-2.amazonaws.com/prod/chat"
        data = {"messages": messages}

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            message_reply = response.json()['content']
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

        await message.channel.send(message_reply)
        last_message_time[channel_id] = datetime.now()

        # Check if the user who sent the last message is in a voice channel
        member = message.guild.get_member(message.author.id)
        if member.voice and member.voice.channel:
            voice_channel = member.voice.channel
            vc = await voice_channel.connect()
            tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key=AIzaSyDuSXbNLbZ40_OQl4XtHtPYP_3o7iTHD-4"
            tts_data = {
                "input": {"text": message_reply},
                "voice": {"languageCode": "en-IN", "name": "en-IN-Wavenet-C"},
                "audioConfig": {"audioEncoding": "MP3"}
            }
            tts_response = requests.post(tts_url, json=tts_data)
            print("Response Status Code:", tts_response.status_code)
            print("Response Content:", tts_response.text)
            audio_content = tts_response.json()['audioContent']
            audio_data = base64.b64decode(audio_content)
            with open('tts_output.mp3', 'wb') as f:
                f.write(audio_data)
            vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source="tts_output.mp3"))
            while vc.is_playing():
                await asyncio.sleep(1)
            await vc.disconnect()

    await bot.process_commands(message)

bot.run("MTE0MTA2OTg0MTA2Mzc0Nzc1Ng.GfZd_u.GrPv5a2rnSLcDmfq5z58yZ-svh8ubqwvxUgul4")

