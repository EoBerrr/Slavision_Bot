import discord
import os
import asyncio
import logging
from discord.ext import commands
from youtube_checker import start_youtube_checker

# Configurações
DISCORD_TOKEN = os.environ.get('TOKEN', '')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')
VIDEOS_CHANNEL_ID = 1308975523116093490
SHORTS_CHANNEL_ID = 1300538214884315166
LIVE_CHANNEL_ID = 1308975573338554368

# Configurar Intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

# Inicializa o bot
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    logging.info(f"✅ Bot está online e pronto para interagir!")
    
    # Inicia a verificação do YouTube
    start_youtube_checker(bot, YOUTUBE_API_KEY, CHANNEL_ID, VIDEOS_CHANNEL_ID, SHORTS_CHANNEL_ID, LIVE_CHANNEL_ID)

# Função principal para executar o bot
async def run_bot():
    while True:
        try:
            await bot.start(DISCORD_TOKEN)
        except Exception as e:
            logging.error(f"❌ Erro ao executar o bot: {e}")
            logging.info("🔄 Reconectando em 5 minutos...")
            await asyncio.sleep(300)  # Espera 5 minutos antes de tentar reconectar

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    asyncio.run(run_bot())