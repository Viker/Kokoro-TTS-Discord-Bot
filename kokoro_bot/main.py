#!/usr/bin/env python3
"""
Kokoro TTS Bot - Main Entry Point
This module serves as the entry point for the Kokoro TTS Bot application.
"""

import asyncio
import logging
import signal
import sys
import platform
from logging.handlers import RotatingFileHandler
from typing import Optional

from .bot import KokoroTTSBot
from .core.config import Config

# Global bot instance for cleanup
bot_instance: Optional[KokoroTTSBot] = None

def setup_logging(config: Config) -> None:
    """Configure the logging system based on configuration settings."""
    log_file = config.get('log_file', 'bot.log')
    log_level = config.get('log_level', 'INFO')
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                log_file,
                maxBytes=1024 * 1024,  # 1MB
                backupCount=5
            ),
            logging.StreamHandler()
        ]
    )

async def shutdown(signal: signal.Signals, loop: asyncio.AbstractEventLoop) -> None:
    """Handle graceful shutdown of the bot."""
    logger = logging.getLogger(__name__)
    logger.info(f"Received exit signal {signal.name}...")
    
    if bot_instance:
        logger.info("Cleaning up bot resources...")
        try:
            # Cleanup voice connections
            for guild in bot_instance.guilds:
                if guild.voice_client:
                    await bot_instance.voice_manager.cleanup_connection(guild.id)
            
            # Close the bot
            await bot_instance.close()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks...")
    
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

def handle_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Handle unhandled exceptions in the event loop."""
    msg = context.get("exception", context["message"])
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {msg}")

def setup_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """Set up signal handlers if platform supports them."""
    if platform.system() != 'Windows':
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s, loop))
            )

async def main() -> None:
    """Main entry point for the bot application."""
    try:
        # Load configuration
        config = Config()
        
        # Setup logging
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("Starting Kokoro TTS Bot...")
        
        # Get event loop
        loop = asyncio.get_running_loop()
        
        # Set up signal handlers if platform supports them
        setup_signal_handlers(loop)
        
        # Set up global exception handler
        loop.set_exception_handler(handle_exception)
        
        # Create and start bot
        global bot_instance
        bot_instance = KokoroTTSBot()
        
        try:
            async with bot_instance:
                await bot_instance.start(config.get('discord_token'))
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        # Handle Windows console signals
        if platform.system() == 'Windows':
            import win32api
            def handler(signal):
                if signal == signal.CTRL_C_EVENT:
                    asyncio.create_task(shutdown(signal.SIGINT, asyncio.get_event_loop()))
                    return True
                return False
            win32api.SetConsoleCtrlHandler(handler, True)
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot shutdown by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)