import discord
import isodate
import os
import asyncio
import logging
import time
import random
from discord.ext import commands, tasks
from googleapiclient.discovery import build
from keep_alive import keep_alive

keep_alive()  # Inicializa o servidor Flask para manter o bot online

# Configurações
DISCORD_TOKEN = os.environ['TOKEN']
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
CHANNEL_ID = 'UCHgPKp_8teRyUIjf6TfBWRA'

# IDs dos canais do Discord
VIDEOS_CHANNEL_ID = 1308238158202146857
SHORTS_CHANNEL_ID = 1308238158202146857
LIVE_CHANNEL_ID = 1308238158202146857

# Configurar Intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.guild_messages = True

# Inicializa o bot e a API do YouTube
bot = commands.Bot(command_prefix='!', intents=intents)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Variáveis globais
last_video_id = None
live_notified = False

# Função de retry com backoff exponencial
async def retry_with_backoff(func, *args, max_retries=5, initial_delay=5, backoff_factor=2):
    retries = 0
    delay = initial_delay

    while retries < max_retries:
        try:
            return await func(*args)
        except Exception as e:
            logging.error(f"Erro na função {func.__name__}: {e}")
            logging.info(f"Tentando novamente em {delay} segundos...")
            await asyncio.sleep(delay)
            retries += 1
            delay *= backoff_factor

    raise Exception(f"Número máximo de tentativas ({max_retries}) atingido para a função {func.__name__}")

# Função para verificar novos vídeos no canal
async def check_latest_video():
    global last_video_id

    try:
        activities_response = await retry_with_backoff(youtube.activities().list, part='contentDetails', channelId=CHANNEL_ID, maxResults=1)
        if not activities_response.get('items'):
            logging.info("Nenhuma atividade encontrada para este canal.")
            return

        content_details = activities_response['items'][0].get('contentDetails', {})
        if 'upload' not in content_details:
            logging.info("A atividade mais recente não é um upload de vídeo.")
            return

        latest_video_id = content_details['upload']['videoId']

        if latest_video_id != last_video_id:
            video_response = await retry_with_backoff(youtube.videos().list, part='contentDetails', id=latest_video_id)
            video_duration = video_response['items'][0]['contentDetails']['duration']

            duration_seconds = isodate.parse_duration(video_duration).total_seconds()

            if duration_seconds < 60:  # Shorts
                channel = bot.get_channel(SHORTS_CHANNEL_ID)
                await channel.send(f"Novo Shorts no canal! Assista aqui: https://www.youtube.com/watch?v={latest_video_id}\n@everyone")
            else:  # Vídeo normal
                channel = bot.get_channel(VIDEOS_CHANNEL_ID)
                await channel.send(f"Novo vídeo no canal! Assista aqui: https://www.youtube.com/watch?v={latest_video_id}\n@everyone")

            last_video_id = latest_video_id

    except Exception as e:
        logging.error(f"Erro ao verificar novos vídeos: {e}")

# Função para verificar se há uma transmissão ao vivo ativa
async def check_live_status():
    global live_notified

    try:
        live_response = await retry_with_backoff(youtube.search().list, part='snippet', channelId=CHANNEL_ID, eventType='live', type='video')
        if live_response['items'] and not live_notified:
            live_video_id = live_response['items'][0]['id']['videoId']
            live_notified = True
            channel = bot.get_channel(LIVE_CHANNEL_ID)
            await channel.send(f"🔴 Estamos ao vivo! Assista aqui: https://www.youtube.com/watch?v={live_video_id}\n@everyone")
        elif not live_response['items']:
            live_notified = False
    except Exception as e:
        logging.error(f"Erro ao verificar transmissões ao vivo: {e}")

# Tarefa periódica para verificar novos vídeos e lives
@tasks.loop(minutes=5)
async def youtube_checker():
    try:
        await check_latest_video()
        await check_live_status()
    except Exception as e:
        logging.error(f"Erro no youtube_checker: {e}")

async def run_bot():
    global last_video_id, live_notified

    while True:
        try:
            await bot.start(DISCORD_TOKEN)
        except Exception as e:
            logging.error(f"Erro ao executar o bot: {e}")
            last_video_id = None
            live_notified = False
            logging.info("Reconectando em 60 segundos...")
            await asyncio.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    asyncio.run(run_bot())