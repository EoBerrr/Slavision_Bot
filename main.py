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
DISCORD_TOKEN = os.environ.get('TOKEN', '')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
CHANNEL_ID = 'UCY9ni94vmqT_ZLEZmnVOCoA'

# IDs dos canais do Discord
VIDEOS_CHANNEL_ID = 1308975523116093490
SHORTS_CHANNEL_ID = 1300538214884315166
LIVE_CHANNEL_ID = 1308975573338554368

# Verificações de Ambiente
if not DISCORD_TOKEN:
    logging.error("Token do Discord não configurado!")
    exit(1)

if not YOUTUBE_API_KEY:
    logging.error("Chave da API do YouTube não configurada!")
    exit(1)

# Configurar Intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

# Inicializa o bot e a API do YouTube
bot = commands.Bot(command_prefix='!', intents=intents)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Variáveis globais
last_video_id = None
live_notified = False

# Função de envio de mensagem com tratamento de erros
async def send_discord_message(channel_id, message):
    channel = bot.get_channel(channel_id)
    if channel is None:
        logging.error(f"Canal {channel_id} não encontrado")
        return
    try:
        await channel.send(message)
    except discord.Forbidden:
        logging.error(f"Sem permissão para enviar mensagem no canal {channel_id}")
    except discord.HTTPException as e:
        logging.error(f"Erro ao enviar mensagem: {e}")

# Função de retry com backoff exponencial
async def retry_with_backoff(func, *args, max_retries=5, initial_delay=5, backoff_factor=2, **kwargs):
    retries = 0
    delay = initial_delay

    while retries < max_retries:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Erro na função {func.__name__}: {e}")
            logging.info(f"Tentando novamente em {delay} segundos...")
            await asyncio.sleep(delay)
            retries += 1
            delay *= backoff_factor

    raise Exception(f"Número máximo de tentativas ({max_retries}) atingido para a função {func.__name__}")

# Evento de inicialização do bot
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    logging.info(f"Bot está online e monitorando o canal do YouTube!")
    
    # Log de verificação dos canais
    logging.info(f"Canal de vídeos: {bot.get_channel(VIDEOS_CHANNEL_ID)}")
    logging.info(f"Canal de shorts: {bot.get_channel(SHORTS_CHANNEL_ID)}")
    logging.info(f"Canal de lives: {bot.get_channel(LIVE_CHANNEL_ID)}")
    
    # Inicia a tarefa de verificação
    youtube_checker.start()

# Função para verificar novos vídeos no canal
async def check_latest_video():
    global last_video_id

    try:
        activities_request = youtube.activities().list(part='contentDetails', channelId=CHANNEL_ID, maxResults=1)
        activities_response = activities_request.execute()  # Uso síncrono aqui
        if not activities_response.get('items'):
            logging.info("Nenhuma atividade encontrada para este canal.")
            return

        content_details = activities_response['items'][0].get('contentDetails', {})
        if 'upload' not in content_details:
            logging.info("A atividade mais recente não é um upload de vídeo.")
            return

        latest_video_id = content_details['upload']['videoId']

        if latest_video_id != last_video_id:
            video_request = youtube.videos().list(part='contentDetails', id=latest_video_id)
            video_response = video_request.execute()  # Uso síncrono aqui
            video_duration = video_response['items'][0]['contentDetails']['duration']

            duration_seconds = isodate.parse_duration(video_duration).total_seconds()

            if duration_seconds < 60:  # Shorts
                await send_discord_message(SHORTS_CHANNEL_ID, f"Novo Shorts no canal! Assista aqui: https://www.youtube.com/watch?v={latest_video_id}\n@everyone")
            else:  # Vídeo normal
                await send_discord_message(VIDEOS_CHANNEL_ID, f"Novo vídeo no canal! Assista aqui: https://www.youtube.com/watch?v={latest_video_id}\n@everyone")

            last_video_id = latest_video_id

    except Exception as e:
        logging.error(f"Erro ao verificar novos vídeos: {e}")

# Função para verificar se há uma transmissão ao vivo ativa
async def check_live_status():
    global live_notified

    try:
        live_request = youtube.search().list(part='snippet', channelId=CHANNEL_ID, eventType='live', type='video')
        live_response = live_request.execute()  # Uso síncrono aqui
        if live_response['items'] and not live_notified:
            live_video_id = live_response['items'][0]['id']['videoId']
            live_notified = True
            await send_discord_message(LIVE_CHANNEL_ID, f"🔴 Estamos ao vivo! Assista aqui: https://www.youtube.com/watch?v={live_video_id}\n@everyone")
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

# Função principal para executar o bot
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