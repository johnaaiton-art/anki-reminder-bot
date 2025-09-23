#!/usr/bin/env python3
"""
Simple Anki Reminder Bot - Railway Compatible
Sends scheduled reminders without complex polling
"""

import asyncio
import logging
import os
import random
import signal
import sys
from datetime import datetime
from typing import List
import pytz
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('anki_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleAnkiBot:
    def __init__(self):
        # Configuration
        self.token = os.getenv('TELEGRAM_TOKEN', '7660365913:AAGSKYO3rzJ62USF-ppU2XZwZW9aKIX714Y')
        self.chat_id = int(os.getenv('CHAT_ID', '-1002452488546'))
        
        self.bot = Bot(token=self.token)
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Daily tracking
        self.waiting_for_response = False
        self.response_received = False
        self.last_reminder_date = None
        
        # Messages
        self.reminder_messages = [
            "Time for your Anki flashcards! 📚✨",
            "Hey! Don't forget your daily Anki practice! 🧠💪",
            "Anki time! Let's strengthen that memory! 🎯",
            "Your brain is waiting for some Anki love! 💝📖",
            "Daily Anki reminder: Knowledge is power! ⚡📚",
            "Ready to boost your brain? Anki awaits! 🚀🧠",
            "Don't let your neurons get lazy! Anki time! ⚡📖",
            "Consistency is the key to mastery! Time for Anki! 🔑",
            "Level up your knowledge with today's Anki session! 🎮",
            "Your future self will thank you for this Anki session! 🙏"
        ]
        
        self.followup_messages = [
            "Still waiting for your Anki screenshot! Don't give up! 💪",
            "Hey, did you forget about Anki? It's not too late! ⏰",
            "Your brain is still waiting for that Anki session! 🧠❤️",
            "Gentle reminder: Anki flashcards are still pending! 📚",
            "Don't let the day end without your Anki practice! 🌙",
            "Last chance to complete your daily Anki goal! 🎯",
            "Even 5 minutes of Anki is better than none! ⚡"
        ]

        # Image paths
        self.image_paths = [
            "./vasilina_anki_1.png",
            "./vasilina_anki_2.png",
            "./vasilina_anki_3.png",
            "./vasilina_anki_4.png",
            "./vasilina_anki_5.png"
        ]

    def get_available_images(self) -> List[str]:
        """Get list of available images"""
        return [img for img in self.image_paths if os.path.exists(img)]

    async def send_message_with_image(self, message: str, image_path: str = None):
        """Send message with optional image"""
        try:
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    await self.bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo,
                        caption=message
                    )
                logger.info(f"Message sent with image: {os.path.basename(image_path)}")
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message
                )
                logger.info("Message sent (text only)")
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    def get_moscow_time(self) -> datetime:
        """Get current Moscow time"""
        return datetime.now(self.moscow_tz)

    async def send_daily_reminder(self):
        """Send the daily 16:00 reminder"""
        current_date = self.get_moscow_time().date()
        
        # Check if we already sent reminder today
        if self.last_reminder_date == current_date:
            logger.info("Daily reminder already sent today")
            return
            
        self.last_reminder_date = current_date
        self.waiting_for_response = True
        self.response_received = False
        
        message = random.choice(self.reminder_messages)
        available_images = self.get_available_images()
        image_path = random.choice(available_images) if available_images else None
        
        await self.send_message_with_image(message, image_path)
        logger.info(f"Daily reminder sent at {self.get_moscow_time()}")

    async def send_followup_reminder(self):
        """Send the 20:30 follow-up reminder"""
        if self.waiting_for_response and not self.response_received:
            message = random.choice(self.followup_messages)
            available_images = self.get_available_images()
            image_path = random.choice(available_images) if available_images else None
            
            await self.send_message_with_image(message, image_path)
            logger.info(f"Follow-up reminder sent at {self.get_moscow_time()}")
        else:
            logger.info("Follow-up reminder not needed - response already received")

    async def reset_daily_flags(self):
        """Reset daily flags at midnight"""
        self.waiting_for_response = False
        self.response_received = False
        logger.info("Daily flags reset at midnight")

    def setup_scheduler(self):
        """Setup the scheduler with cron jobs"""
        # Daily reminder at 16:00 Moscow time
        self.scheduler.add_job(
            self.send_daily_reminder,
            CronTrigger(hour=16, minute=0, timezone=self.moscow_tz),
            id='daily_reminder',
            replace_existing=True
        )
        
        # Follow-up reminder at 20:30 Moscow time
        self.scheduler.add_job(
            self.send_followup_reminder,
            CronTrigger(hour=20, minute=30, timezone=self.moscow_tz),
            id='followup_reminder',
            replace_existing=True
        )
        
        # Reset flags at midnight Moscow time
        self.scheduler.add_job(
            self.reset_daily_flags,
            CronTrigger(hour=0, minute=0, timezone=self.moscow_tz),
            id='reset_flags',
            replace_existing=True
        )
        
        logger.info("Scheduler setup complete with Moscow timezone")

    async def test_reminder(self):
        """Send a test reminder immediately"""
        message = "🧪 Test reminder: " + random.choice(self.reminder_messages)
        available_images = self.get_available_images()
        image_path = random.choice(available_images) if available_images else None
        await self.send_message_with_image(message, image_path)
        logger.info("Test reminder sent")

    async def start_bot(self):
        """Start the bot and scheduler"""
        logger.info("🤖 Starting Simple Anki Reminder Bot...")
        
        try:
            # Test bot connection
            me = await self.bot.get_me()
            logger.info(f"✅ Connected as: {me.username}")
            
            # Setup and start scheduler
            self.setup_scheduler()
            self.scheduler.start()
            
            logger.info("✅ Anki Reminder Bot started successfully!")
            logger.info(f"📅 Daily reminders: 16:00 Moscow time")
            logger.info(f"📅 Follow-up reminders: 20:30 Moscow time")
            logger.info(f"💬 Sending to chat ID: {self.chat_id}")
            logger.info(f"🕐 Current Moscow time: {self.get_moscow_time()}")
            
            # Check for images
            available_images = self.get_available_images()
            if available_images:
                logger.info(f"📸 Found {len(available_images)} images")
            else:
                logger.info("📸 No images found - will send text-only messages")
            
            # Send test message on startup
            await self.test_reminder()
            
            # Keep the bot running with simple loop
            logger.info("🔄 Bot is now running continuously...")
            while True:
                await asyncio.sleep(60)  # Check every minute
                
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            raise

    async def stop_bot(self):
        """Stop the bot gracefully"""
        logger.info("🛑 Stopping Anki Reminder Bot...")
        
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
        
        logger.info("Bot stopped gracefully")

# Global bot instance for signal handling
bot_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if bot_instance:
        asyncio.create_task(bot_instance.stop_bot())
    sys.exit(0)

async def main():
    """Main function"""
    global bot_instance
    
    print("🤖 Simple Anki Reminder Bot - Railway Compatible")
    print("=" * 50)
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        bot_instance = SimpleAnkiBot()
        await bot_instance.start_bot()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if bot_instance:
            await bot_instance.stop_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
