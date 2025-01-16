import discord
import os
import asyncio
import logging
from discord.ext import commands
from keep_alive import keep_alive

# Importar funcionalidades separadas
from youtube_checker import start_youtube_checker
from role_selector import handle_role_selection

# Configurações
DISCORD_TOKEN = os.environ.get('TOKEN', '')
default_cargos = ["Guerreiro", "Mago", "Arqueiro", "Ladino", "Bardo"]

# Inicializa o servidor Flask para manter o bot online
keep_alive()

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
    logging.info(f"Bot está online e pronto para interagir!")
    
    # Inicia a verificação do YouTube
    start_youtube_checker(bot)

# Comando para iniciar a seleção de cargos
@bot.command()
async def selecionar_cargos(ctx):
    await handle_role_selection(ctx, bot, default_cargos)

# Função principal para executar o bot
async def run_bot():
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
