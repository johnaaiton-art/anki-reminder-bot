#!/usr/bin/env python3
"""
Simple Anki Reminder Bot - Railway Compatible
Sends scheduled reminders and monitors for student responses
"""

import asyncio
import json
import logging
import os
import random
import signal
import sys
from datetime import datetime, time
from typing import List
import pytz
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters
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
        # Configuration - Get from environment variables
        self.token = os.getenv('TELEGRAM_TOKEN')
        chat_id_str = os.getenv('CHAT_ID')
        
        # Validate required environment variables
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")
        if not chat_id_str:
            raise ValueError("CHAT_ID environment variable is required")
        
        try:
            self.chat_id = int(chat_id_str)
        except ValueError:
            raise ValueError("CHAT_ID must be a valid integer")
        
        self.bot = Bot(token=self.token)
        self.application = None
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Persistent storage for completion status
        self.status_file = 'completion_status.json'
        
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
        
        self.congratulation_messages = [
            "🎉 Excellent work! Your dedication to Anki is paying off! 🌟",
            "👏 Amazing job! Another day, another step towards mastery! 💪",
            "🔥 Fantastic! Your consistency is inspiring! Keep it up! 🚀",
            "⭐ Well done! Your brain is getting stronger every day! 🧠💪",
            "🎯 Perfect! You're building such a great habit! 👍",
            "💎 Outstanding! Your future self is already thanking you! 🙏",
            "🌟 Brilliant work! Knowledge is your superpower! ⚡",
            "🎊 Awesome! Another successful Anki session completed! 📚✨",
            "👑 Champion! Your dedication to learning is admirable! 🏆",
            "🔥 Incredible! You're on fire with your Anki practice! 🚀"
        ]

        # Image paths
        self.image_paths = [
            "./vasilina_anki_1.png",
            "./vasilina_anki_2.png",
            "./vasilina_anki_3.png",
            "./vasilina_anki_4.png",
            "./vasilina_anki_5.png"
        ]

    def load_completion_status(self):
        """Load completion status from file"""
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_completion_status(self, status):
        """Save completion status to file"""
        with open(self.status_file, 'w') as f:
            json.dump(status, f)

    def is_completed_today(self) -> bool:
        """Check if task was completed today using persistent storage"""
        current_date = self.get_moscow_time().date().isoformat()
        status = self.load_completion_status()
        return status.get(current_date, False)

    def mark_completed_today(self):
        """Mark today as completed in persistent storage"""
        current_date = self.get_moscow_time().date().isoformat()
        status = self.load_completion_status()
        status[current_date] = True
        self.save_completion_status(status)
        logger.info(f"✅ Marked {current_date} as completed in persistent storage")

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

    async def handle_image_message(self, update: Update, context):
        """Handle incoming image messages"""
        try:
            # Only process messages from the target chat
            if update.effective_chat.id != self.chat_id:
                logger.info(f"❌ Message from wrong chat: {update.effective_chat.id}")
                return
            
            # Check if message contains a photo
            if not update.message.photo:
                logger.info("❌ Message doesn't contain photo")
                return
                
            current_time = self.get_moscow_time()
            current_date = current_time.date()
            
            logger.info(f"📸 Image received at {current_time}")
            
            # Check if already completed today using persistent storage
            if self.is_completed_today():
                logger.info("✅ Task already completed today - ignoring duplicate")
                return
            
            # Mark task as completed for today in persistent storage
            self.mark_completed_today()
            logger.info(f"✅ Marked {current_date} as completed")
            
            # Send congratulation message
            congratulation = random.choice(self.congratulation_messages)
            available_images = self.get_available_images()
            image_path = random.choice(available_images) if available_images else None
            
            await self.send_message_with_image(congratulation, image_path)
            logger.info(f"🎉 Congratulation sent for {current_date}")
            
        except Exception as e:
            logger.error(f"❌ Error handling image message: {e}", exc_info=True)

    async def send_daily_reminder(self):
        """Send the daily 16:00 reminder"""
        current_date = self.get_moscow_time().date()
        
        logger.info(f"🔔 Daily reminder check for {current_date}")
        logger.info(f"📊 Status - is_completed_today(): {self.is_completed_today()}")
        
        # Check if task already completed today using persistent storage
        if self.is_completed_today():
            logger.info(f"✅ Task already completed for {current_date} - skipping 16:00 reminder")
            return
        
        message = random.choice(self.reminder_messages)
        available_images = self.get_available_images()
        image_path = random.choice(available_images) if available_images else None
        
        await self.send_message_with_image(message, image_path)
        logger.info(f"📅 Daily reminder sent at {self.get_moscow_time()}")

    async def send_followup_reminder(self):
        """Send the 20:30 follow-up reminder"""
        current_date = self.get_moscow_time().date()
        
        logger.info(f"🔔 Follow-up reminder check for {current_date}")
        logger.info(f"📊 Status - is_completed_today(): {self.is_completed_today()}")
        
        # Check if task already completed today using persistent storage
        if self.is_completed_today():
            logger.info(f"✅ Task already completed for {current_date} - skipping 20:30 follow-up")
            return
        
        message = random.choice(self.followup_messages)
        available_images = self.get_available_images()
        image_path = random.choice(available_images) if available_images else None
        
        await self.send_message_with_image(message, image_path)
        logger.info(f"📅 Follow-up reminder sent at {self.get_moscow_time()}")

    async def reset_daily_flags(self):
        """Reset daily flags at midnight - now handled by date comparison"""
        logger.info("🕛 Midnight reset - persistent storage continues to work")

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
        
        # Midnight check (optional - mainly for logging)
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
        logger.info("🤖 Starting Simple Anki Reminder Bot with Image Monitoring...")
        
        try:
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Add message handler for images
            image_handler = MessageHandler(filters.PHOTO, self.handle_image_message)
            self.application.add_handler(image_handler)
            
            # Test bot connection
            me = await self.bot.get_me()
            logger.info(f"✅ Connected as: {me.username}")
            
            # Setup and start scheduler
            self.setup_scheduler()
            self.scheduler.start()
            
            logger.info("✅ Anki Reminder Bot started successfully!")
            logger.info(f"📅 Daily reminders: 16:00 Moscow time")
            logger.info(f"📅 Follow-up reminders: 20:30 Moscow time")
            logger.info(f"💬 Monitoring chat ID: {self.chat_id}")
            logger.info(f"🕐 Current Moscow time: {self.get_moscow_time()}")
            
            # Check for images
            available_images = self.get_available_images()
            if available_images:
                logger.info(f"📸 Found {len(available_images)} images")
            else:
                logger.info("📸 No images found - will send text-only messages")
            
            # Check persistent storage status
            status = self.load_completion_status()
            logger.info(f"💾 Persistent storage status: {len(status)} days recorded")
            
            # Start polling for messages
            logger.info("👀 Starting to monitor for student images...")
            await self.application.initialize()
            await self.application.start()
            
            # Send test message on startup
            await self.test_reminder()
            
            # Keep the bot running and polling for updates
            logger.info("🔄 Bot is now running and monitoring messages...")
            await self.application.updater.start_polling()
            
            # Keep alive
            while True:
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            raise

    async def stop_bot(self):
        """Stop the bot gracefully"""
        logger.info("🛑 Stopping Anki Reminder Bot...")
        
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
        
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram application stopped")
        
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
    
    print("🤖 Simple Anki Reminder Bot - Railway Compatible with Image Monitoring")
    print("=" * 65)
    
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
