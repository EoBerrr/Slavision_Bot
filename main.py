import discord
import os
import asyncio
import logging
from discord.ext import commands
from keep_alive import keep_alive
from youtube_checker import YouTubeMonitor

# Configurações
DISCORD_TOKEN = os.environ.get('TOKEN', '')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
CHANNEL_ID = 'UCY9ni94vmqT_ZLEZmnVOCoA'
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

# Inicializa o bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Inicializa o monitor do YouTube
youtube_checker = None

@bot.event
async def on_ready():
    global youtube_checker
    print(f'Bot conectado como {bot.user}')
    logging.info(f"Bot está online e monitorando o canal do YouTube!")
    
    youtube_checker = YouTubeMonitor(
        bot,
        YOUTUBE_API_KEY,
        CHANNEL_ID,
        VIDEOS_CHANNEL_ID,
        SHORTS_CHANNEL_ID,
        LIVE_CHANNEL_ID
    )
    youtube_checker.start_monitoring.start()

async def run_bot():
    keep_alive()
    while True:
        try:
            await bot.start(DISCORD_TOKEN)
        except Exception as e:
            logging.error(f"Erro ao executar o bot: {e}")
            logging.info("Reconectando em 60 segundos...")
            await asyncio.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    asyncio.run(run_bot())