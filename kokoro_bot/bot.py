"""
Kokoro TTS Bot - Main Bot Class
"""

import logging
import discord
from discord.ext import commands
from typing import Optional, Dict

from .core.config import Config
from .core.tts_engine import TTSEngine
from .core.queue_manager import QueueManager
from .core.voice_manager import VoiceConnectionManager
from .core.settings_manager import SettingsManager
from .utils.metrics import MetricsManager
from .utils.error_handler import ErrorHandler

# Import cogs after bot class definition to avoid circular imports
class KokoroTTSBot(commands.Bot):
    """Enhanced Discord bot for text-to-speech functionality"""
    
    def __init__(self):
        # Load configuration
        self.config = Config()
        
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        # Initialize base class
        super().__init__(
            command_prefix=self.config.get('command_prefix', '!'),
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize state dictionaries
        self.inactivity_timers: Dict[int, float] = {}
        self.voice_text_channels: Dict[int, int] = {}
        
        # Initialize components
        self._init_components()

    def _init_components(self) -> None:
        """Initialize all bot components and managers."""
        try:
            # Initialize metrics first for monitoring
            self.metrics = MetricsManager()
            
            # Initialize core components
            self.tts_engine = TTSEngine(
                self.config.get('model_path', 'kokoro-v0_19.onnx'),
                self.config.get('voices_path', 'voices.bin'),
                self.config
            )
            
            self.queue_manager = QueueManager(self.config)
            self.voice_manager = VoiceConnectionManager(self.metrics)
            
            # Initialize settings manager with the correct default voice
            self.settings_manager = SettingsManager(self.config)
            self.settings_manager.default_settings['voice'] = self.tts_engine.get_default_voice()
            
            # Initialize error handler
            self.error_handler = ErrorHandler(self.logger)
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize components: {e}")
            raise

    async def setup_hook(self) -> None:
        """
        Setup hook called after the bot logs in but before it starts running.
        Used to set up background tasks and initialize cogs.
        """
        try:
            self.logger.info("Setting up bot components...")
            
            # Add cogs
            await self.add_cog(VoiceCog(self))
            await self.add_cog(AdminCog(self))
            
            self.logger.info("Bot setup completed successfully")
            
        except Exception as e:
            self.logger.critical(f"Failed to setup bot: {e}")
            raise

    async def on_ready(self) -> None:
        """
        Event handler called when the bot has successfully connected to Discord.
        """
        self.logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set custom status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{self.command_prefix}help"
        )
        await self.change_presence(activity=activity)

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """
        Global error handler for all unhandled exceptions.
        
        Args:
            event_method: The event that raised the exception
            *args: Positional arguments for the event
            **kwargs: Keyword arguments for the event
        """
        self.logger.error(f"Error in {event_method}", exc_info=True)
        self.metrics.track_error('unhandled_exception')

    async def close(self) -> None:
        """
        Clean up resources when shutting down the bot.
        """
        self.logger.info("Shutting down bot...")
        
        try:
            # Cleanup voice connections
            for guild in self.guilds:
                if guild.voice_client:
                    await self.voice_manager.cleanup_connection(guild.id)
            
            # Additional cleanup if needed
            # Add any other cleanup code here
            
            # Call parent close
            await super().close()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            raise
        finally:
            self.logger.info("Bot shutdown complete")

    def get_guild_voice_client(self, guild_id: int) -> Optional[discord.VoiceClient]:
        """
        Get the voice client for a specific guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            The voice client if connected, None otherwise
        """
        guild = self.get_guild(guild_id)
        return guild.voice_client if guild else None

    def is_in_voice_channel(self, guild_id: int) -> bool:
        """
        Check if the bot is connected to a voice channel in the specified guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            True if connected to a voice channel, False otherwise
        """
        voice_client = self.get_guild_voice_client(guild_id)
        return voice_client is not None and voice_client.is_connected()

    @property
    def connected_guilds(self) -> int:
        """
        Get the number of guilds the bot is connected to.
        
        Returns:
            The number of connected guilds
        """
        return len([g for g in self.guilds if self.is_in_voice_channel(g.id)])

    def format_status(self) -> str:
        """
        Format the bot's current status for display.
        
        Returns:
            A formatted status string
        """
        return (
            f"Connected to {self.connected_guilds}/{len(self.guilds)} voice channels\n"
            f"Active queues: {len(self.queue_manager.queues)}\n"
            f"Command prefix: {self.command_prefix}"
        )

from .cogs.voice import VoiceCog
from .cogs.admin import AdminCog