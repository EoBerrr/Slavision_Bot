import discord
import os
from discord.ext import commands, tasks
from googleapiclient.discovery import build
import isodate  # Para analisar a duração do vídeo no formato ISO 8601

# Configurações
DISCORD_TOKEN = os.environ['TOKEN']
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
CHANNEL_ID = 'UCHgPKp_8teRyUIjf6TfBWRA'

# IDs dos canais do Discord
VIDEOS_CHANNEL_ID = 1308238158202146857  # Canal para notificações de vídeos
SHORTS_CHANNEL_ID = 1308238158202146860  # Canal para notificações de Shorts (exemplo)
LIVE_CHANNEL_ID = 1308238158202146863  # Canal para notificações de Lives (exemplo)

# Configurar Intents
intents = discord.Intents.default()
intents.messages = True  # Se precisar ler mensagens
intents.guilds = True  # Necessário para interagir com guilds
intents.guild_messages = True  # Necessário para enviar mensagens

# Inicializa o bot e a API do YouTube
bot = commands.Bot(command_prefix='!', intents=intents)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Variáveis globais
last_video_id = None
live_notified = False

# Função para verificar novos vídeos no canal
async def check_latest_video():
    global last_video_id

    # Obtém o vídeo mais recente
    activities_request = youtube.activities().list(part='contentDetails', channelId=CHANNEL_ID, maxResults=1)
    activities_response = activities_request.execute()

    # Verifica se existem itens na resposta
    if not activities_response.get('items'):
        print("Nenhuma atividade encontrada para este canal.")
        return

    # Verifica se o item contém informações de upload
    content_details = activities_response['items'][0].get('contentDetails', {})
    if 'upload' not in content_details:
        print("A atividade mais recente não é um upload de vídeo.")
        return

    # Obtém o ID do vídeo mais recente
    latest_video_id = content_details['upload']['videoId']

    # Verifica se é um vídeo novo
    if latest_video_id != last_video_id:
        # Obtém informações detalhadas do vídeo
        video_request = youtube.videos().list(part='contentDetails', id=latest_video_id)
        video_response = video_request.execute()
        video_duration = video_response['items'][0]['contentDetails']['duration']

        # Converte duração para segundos
        duration_seconds = isodate.parse_duration(video_duration).total_seconds()

        # Envia mensagem específica com base no tipo de conteúdo
        if duration_seconds < 60:  # Shorts
            channel = bot.get_channel(SHORTS_CHANNEL_ID)
            await channel.send(f"@everyone Novo Shorts no canal! Assista aqui: https://www.youtube.com/watch?v={latest_video_id}")
        else:  # Vídeo normal
            channel = bot.get_channel(VIDEOS_CHANNEL_ID)
            await channel.send(f"@everyone Novo vídeo no canal! Assista aqui: https://www.youtube.com/watch?v={latest_video_id}")

        # Atualiza o último ID de vídeo
        last_video_id = latest_video_id

# Função para verificar se há uma transmissão ao vivo ativa
async def check_live_status():
    global live_notified

    # Busca transmissões ao vivo do canal
    live_request = youtube.search().list(
        part='snippet',
        channelId=CHANNEL_ID,
        eventType='live',
        type='video'
    )
    live_response = live_request.execute()

    # Se houver live e ainda não foi notificada
    if live_response['items'] and not live_notified:
        live_video_id = live_response['items'][0]['id']['videoId']
        live_notified = True
        channel = bot.get_channel(LIVE_CHANNEL_ID)
        await channel.send(f"🔴 @everyone Estamos ao vivo! Assista aqui: https://www.youtube.com/watch?v={live_video_id}")

    # Reseta notificação se não houver live
    elif not live_response['items']:
        live_notified = False

# Tarefa periódica para verificar novos vídeos e lives
@tasks.loop(minutes=5)
async def youtube_checker():
    await check_latest_video()
    await check_live_status()

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    youtube_checker.start()  # Inicia a verificação periódica

bot.run(DISCORD_TOKEN)
