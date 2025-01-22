import discord
import isodate
import logging
import asyncio
from googleapiclient.discovery import build
from datetime import datetime, time, timedelta, timezone
from discord.ext import commands, tasks

class YouTubeChecker:
    def __init__(self, bot, youtube_api_key, channel_id, video_channel_id, shorts_channel_id, live_channel_id):
        self.bot = bot
        self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        self.channel_id = channel_id
        self.video_channel_id = video_channel_id
        self.shorts_channel_id = shorts_channel_id
        self.live_channel_id = live_channel_id
        self.last_video_id = None
        self.live_notified = False
        
    async def send_discord_message(self, channel_id, message):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            logging.error(f"Canal {channel_id} não encontrado")
            return
        try:
            await channel.send(message)
        except discord.Forbidden:
            logging.error(f"Sem permissão para enviar mensagem no canal {channel_id}")
        except discord.HTTPException as e:
            logging.error(f"Erro ao enviar mensagem: {e}")

    def is_live_check_allowed(self):
        now_utc = datetime.now(timezone.utc)
        now = now_utc - timedelta(hours=3)
        current_day = now.weekday()
        current_time = now.time()

        if current_day in [4, 5, 6]:
            start_time = time(19, 0)
            end_time = time(22, 10)
            return start_time <= current_time <= end_time
        return False

    async def check_latest_video(self):
        try:
            activities_request = self.youtube.activities().list(part='contentDetails', channelId=self.channel_id, maxResults=1)
            activities_response = activities_request.execute()
            
            if not activities_response.get('items'):
                logging.info("Nenhuma atividade encontrada para este canal.")
                return

            content_details = activities_response['items'][0].get('contentDetails', {})
            if 'upload' not in content_details:
                logging.info("A atividade mais recente não é um upload de vídeo.")
                return

            latest_video_id = content_details['upload']['videoId']

            if latest_video_id != self.last_video_id:
                video_request = self.youtube.videos().list(part='contentDetails', id=latest_video_id)
                video_response = video_request.execute()
                video_duration = video_response['items'][0]['contentDetails']['duration']

                duration_seconds = isodate.parse_duration(video_duration).total_seconds()

                if duration_seconds <= 180:
                    await self.send_discord_message(self.shorts_channel_id, f"Novo Shorts no canal! Assista aqui: https://www.youtube.com/watch?v={latest_video_id}\n@everyone")
                else:
                    await self.send_discord_message(self.video_channel_id, f"Novo vídeo no canal! Assista aqui: https://www.youtube.com/watch?v={latest_video_id}\n@everyone")

                self.last_video_id = latest_video_id

        except Exception as e:
            logging.error(f"Erro ao verificar novos vídeos: {e}")

    async def check_live_status(self):
        try:
            live_request = self.youtube.search().list(part='snippet', channelId=self.channel_id, eventType='live', type='video')
            live_response = live_request.execute()
            
            if live_response['items'] and not self.live_notified:
                live_video_id = live_response['items'][0]['id']['videoId']
                self.live_notified = True
                await self.send_discord_message(self.live_channel_id, f"🔴 Estamos ao vivo! Assista aqui: https://www.youtube.com/watch?v={live_video_id}\n@everyone")
            elif not live_response['items']:
                self.live_notified = False
        except Exception as e:
            logging.error(f"Erro ao verificar transmissões ao vivo: {e}")

    @tasks.loop(minutes=5)
    async def start_monitoring(self):
        try:
            await self.check_latest_video()

            if self.is_live_check_allowed():
                await self.check_live_status()
            else:
                logging.info("Fora do horário permitido para verificar lives.")

        except Exception as e:
            logging.error(f"Erro no youtube_checker: {e}")