import os
import logging
import asyncio
from datetime import datetime, time, timedelta, timezone
import discord
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from discord.ext import tasks

def is_within_schedule():
    gmt_minus_3 = timezone(timedelta(hours=-3))
    now = datetime.now(gmt_minus_3)
    start_time = time(19, 0, 0)
    end_time = time(22, 10, 0)
    return now.weekday() in (4, 5, 6) and start_time <= now.time() <= end_time

class YouTubeChecker:
    def __init__(self, bot, youtube_api_key, channel_id, videos_channel_id, shorts_channel_id, live_channel_id):
        self.bot = bot
        self.youtube_api_key = youtube_api_key
        self.channel_id = channel_id
        self.videos_channel_id = videos_channel_id
        self.shorts_channel_id = shorts_channel_id
        self.live_channel_id = live_channel_id
        self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
        self.monitoring_task = None
        self.request_count = 0
        self.quota_limit_reached = False
        self.quota_reset_time = None

    async def send_discord_message(self, channel_id, message):
        try:
            channel = self.bot.get_channel(channel_id)
            await channel.send(message)
        except Exception as e:
            logging.error(f"❌ Erro ao enviar mensagem: {e}")

    @tasks.loop(minutes=10)
    async def check_lives(self):
        if self.quota_limit_reached:
            current_time = datetime.now()
            if current_time >= self.quota_reset_time:
                self.quota_limit_reached = False
                self.request_count = 0
            else:
                logging.info(f"⏳ Quota da API excedida. Próxima tentativa em: {self.quota_reset_time}")
                return

        if not is_within_schedule():
            logging.info("⏳ Fora do horário permitido para verificar lives.")
            return

        try:
            self.request_count += 1
            logging.info(f"🔍 Verificando lives (Requisição #{self.request_count})")

            request = self.youtube.search().list(
                part="snippet",
                channelId=self.channel_id,
                eventType="live",
                type="video"
            )
            response = request.execute()

            if "items" not in response or not response["items"]:
                logging.info("📭 Nenhuma live encontrada no momento.")
                return

            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                video_title = item["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logging.info(f"🎥 Live encontrada: {video_title} ({video_url})")

                await self.send_discord_message(self.live_channel_id, f"🔴 **Live Agora!** {video_title}\n{video_url}")

        except HttpError as e:
            if e.resp.status == 403:
                logging.error("❌ Cota da API do YouTube excedida")
                self.quota_limit_reached = True
                # Define o tempo de reset para 24 horas a partir de agora
                self.quota_reset_time = datetime.now() + timedelta(hours=24)
            else:
                logging.error(f"❌ Erro na API do YouTube: {e}")
        except Exception as e:
            logging.error(f"❌ Erro inesperado: {e}")

    async def start_monitoring(self):
        await self.bot.wait_until_ready()
        if self.monitoring_task is None:
            self.monitoring_task = self.check_lives.start()
        logging.info("✅ Monitoramento do YouTube iniciado!")

def start_youtube_checker(bot, youtube_api_key, channel_id, videos_channel_id, shorts_channel_id, live_channel_id):
    checker = YouTubeChecker(bot, youtube_api_key, channel_id, videos_channel_id, shorts_channel_id, live_channel_id)
    bot.loop.create_task(checker.start_monitoring())