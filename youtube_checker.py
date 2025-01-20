import os
import logging
from datetime import datetime, time, timedelta, timezone
from googleapiclient.discovery import build
from discord.ext import tasks

def is_within_schedule():
    gmt_minus_3 = timezone(timedelta(hours=-3))
    now = datetime.now(gmt_minus_3)
    start_time = time(19, 0, 0)
    end_time = time(22, 10, 0)
    return now.weekday() in (4, 5, 6) and start_time <= now.time() <= end_time

class YouTubeChecker:
    def __init__(self, bot):
        self.bot = bot
        self.youtube_api_key = os.environ.get('YOUTUBE_API_KEY', '')
        self.channel_id = os.environ.get('CHANNEL_ID', '')
        self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
        self.check_lives.start()

    @tasks.loop(minutes=5)
    async def check_lives(self):
        if not is_within_schedule():
            logging.info("Fora do horário permitido para verificar lives.")
            return

        try:
            logging.info("Verificando lives no canal do YouTube...")

            request = self.youtube.search().list(
                part="snippet",
                channelId=self.channel_id,
                eventType="live",
                type="video"
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                video_title = item["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logging.info(f"Live encontrada: {video_title} ({video_url})")

                guild_id = int(os.environ.get("GUILD_ID", 0))
                channel_id = int(os.environ.get("ANNOUNCEMENT_CHANNEL_ID", 0))
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    logging.warning(f"Guilda {guild_id} não encontrada.")
                    continue

                channel = guild.get_channel(channel_id)
                if channel is None:
                    logging.warning(f"Canal {channel_id} não encontrado.")
                    continue

                await channel.send(f"\ud83d\udd34 **Live Agora!** {video_title} \n{video_url}")

        except Exception as e:
            logging.error(f"Erro ao verificar lives: {e}")

    @check_lives.before_loop
    async def before_check_lives(self):
        await self.bot.wait_until_ready()

def start_youtube_checker(bot):
    YouTubeChecker(bot)
