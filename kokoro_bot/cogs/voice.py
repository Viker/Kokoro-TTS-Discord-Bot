"""
Voice commands and functionality for the Kokoro TTS Bot.
"""

import time
import logging
import discord
from discord.ext import commands, tasks
from typing import Dict, Any, TYPE_CHECKING
import asyncio
import os

from ..utils.result import Result

if TYPE_CHECKING:
    from ..bot import KokoroTTSBot

class VoiceCog(commands.Cog):
    """Enhanced voice commands and functionality"""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the voice cog.
        
        Args:
            bot: Bot instance
        """
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self._setup_tasks()

    # Rest of your VoiceCog implementation...

    def _setup_tasks(self):
        """Setup background tasks"""
        self.cleanup_task.start()
        self.metrics_task.start()

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.cleanup_task.cancel()
        self.metrics_task.cancel()

    @tasks.loop(minutes=5)
    async def cleanup_task(self):
        """Cleanup inactive voice connections"""
        for guild in self.bot.guilds:
            if guild.voice_client and not guild.voice_client.is_playing():
                await self.bot.voice_manager.cleanup_connection(guild.id)

    @tasks.loop(minutes=1)
    async def metrics_task(self):
        """Update and log metrics"""
        metrics = self.bot.metrics.get_metrics_report()
        self.logger.info(f"Metrics update: {metrics}")

    @commands.command(name='join')
    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.has_permissions(connect=True)
    async def join(self, ctx: commands.Context):
        """Join voice channel with enhanced error handling"""
        start_time = time.time()
        
        try:
            if not ctx.author.voice:
                raise commands.CommandError("You need to be in a voice channel!")

            channel = ctx.author.voice.channel
            connection_result = await self.bot.voice_manager.get_connection(
                ctx.guild.id,
                channel
            )
            
            if not connection_result.success:
                raise commands.CommandError(connection_result.error)

            # Store text channel mapping
            text_channel = discord.utils.get(
                ctx.guild.text_channels,
                name=channel.name
            )
            if text_channel:
                self.bot.voice_text_channels[channel.id] = text_channel.id

            embed = self._create_embed(
                f"Joined {channel.name}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

            # Update metrics
            self.bot.metrics.track_command('join', time.time() - start_time)

        except Exception as e:
            await self.bot.error_handler.handle_command_error(e, ctx, 'join')
            embed = self._create_embed(str(e), color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(name='leave')
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def leave(self, ctx: commands.Context):
        """Leave voice channel"""
        start_time = time.time()
        
        try:
            if not ctx.voice_client:
                raise commands.CommandError("I'm not in a voice channel!")

            await self.bot.voice_manager.cleanup_connection(ctx.guild.id)
            embed = self._create_embed(
                "Left voice channel",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

            # Update metrics
            self.bot.metrics.track_command('leave', time.time() - start_time)

        except Exception as e:
            await self.bot.error_handler.handle_command_error(e, ctx, 'leave')
            embed = self._create_embed(str(e), color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(name='voice')
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def change_voice(self, ctx: commands.Context, voice: str = None):
        """Change TTS voice with validation"""
        start_time = time.time()
        
        try:
            available_voices = self.bot.tts_engine.get_voices()
            
            if voice is None:
                # Show available voices
                current_settings = self.bot.settings_manager.get_user_settings(
                    ctx.guild.id,
                    ctx.author.id
                )
                
                embed = self._create_embed("Available Voices", discord.Color.blue())
                embed.add_field(
                    name="Current Voice",
                    value=current_settings['voice'],
                    inline=False
                )
                
                # Split voices into chunks
                voice_chunks = [
                    available_voices[i:i + 10]
                    for i in range(0, len(available_voices), 10)
                ]
                for i, chunk in enumerate(voice_chunks, 1):
                    embed.add_field(
                        name=f"Voices (Page {i})",
                        value="\n".join(f"• {v}" for v in chunk),
                        inline=True
                    )
                
                await ctx.send(embed=embed)
                return

            if voice not in available_voices:
                raise commands.CommandError(
                    f"Invalid voice! Use `{ctx.prefix}voice` to see available voices."
                )

            # Update setting
            result = self.bot.settings_manager.set_user_setting(
                ctx.guild.id,
                ctx.author.id,
                'voice',
                voice
            )
            
            if not result.success:
                raise commands.CommandError(result.error)

            embed = self._create_embed(
                f"Voice changed to {voice}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

            # Update metrics
            self.bot.metrics.track_command('voice', time.time() - start_time)

        except Exception as e:
            await self.bot.error_handler.handle_command_error(e, ctx, 'voice')
            embed = self._create_embed(str(e), color=discord.Color.red())
            await ctx.send(embed=embed)


    @commands.command(name='language', aliases=['lang'])
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def change_language(self, ctx: commands.Context, lang: str = None):
        """Change TTS language with validation.
        
        Args:
            ctx: Command context
            lang: Language code (e.g., 'en', 'ja', 'fr')
        """
        start_time = time.time()
        
        try:
            # Get available languages from TTS engine
            available_languages = self.bot.tts_engine.get_available_languages()
            
            # Show current language if no parameter provided
            if lang is None:
                current_settings = self.bot.settings_manager.get_user_settings(
                    ctx.guild.id,
                    ctx.author.id
                )
                
                embed = self._create_embed(
                    "Available Languages and Current Setting",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Current Language",
                    value=f"{current_settings['lang']} ({available_languages.get(current_settings['lang'], 'Unknown')})",
                    inline=False
                )
                
                # Format available languages
                lang_list = [f"• {code}: {name}" for code, name in available_languages.items()]
                chunks = [lang_list[i:i + 10] for i in range(0, len(lang_list), 10)]
                
                for i, chunk in enumerate(chunks, 1):
                    embed.add_field(
                        name=f"Available Languages (Page {i})",
                        value="\n".join(chunk),
                        inline=True
                    )
                
                await ctx.send(embed=embed)
                return
            
            # Validate language code
            if lang not in available_languages:
                raise commands.CommandError(
                    f"Invalid language code! Use `{ctx.prefix}language` to see available languages."
                )
            
            # Update setting
            result = self.bot.settings_manager.set_user_setting(
                ctx.guild.id,
                ctx.author.id,
                'lang',
                lang
            )
            
            if not result.success:
                raise commands.CommandError(result.error)
                
            embed = self._create_embed(
                f"TTS language changed to {lang} ({available_languages[lang]})",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
            # Update metrics
            self.bot.metrics.track_command('language', time.time() - start_time)
            
        except Exception as e:
            await self.bot.error_handler.handle_command_error(e, ctx, 'language')
            embed = self._create_embed(str(e), color=discord.Color.red())
            await ctx.send(embed=embed)



    @commands.command(name='speed')
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def change_speed(self, ctx: commands.Context, speed: float = None):
        """Change TTS speed.
        
        Args:
            ctx: Command context
            speed: Speech speed multiplier (0.5 to 2.0)
        """
        start_time = time.time()
        
        try:
            # Show current speed if no parameter provided
            if speed is None:
                current_settings = self.bot.settings_manager.get_user_settings(
                    ctx.guild.id,
                    ctx.author.id
                )
                
                embed = self._create_embed(
                    f"Current TTS Speed: {current_settings['speed']}x\n"
                    f"Use `{ctx.prefix}speed <value>` to change speed (0.5 to 2.0)",
                    color=discord.Color.blue()
                )
                
                await ctx.send(embed=embed)
                return
            
            # Validate speed range
            if not 0.5 <= speed <= 2.0:
                raise commands.CommandError(
                    "Speed must be between 0.5 and 2.0\n"
                    "Examples:\n"
                    "0.5 = Half speed\n"
                    "1.0 = Normal speed\n"
                    "1.5 = 50% faster\n"
                    "2.0 = Double speed"
                )
            
            # Update setting
            result = self.bot.settings_manager.set_user_setting(
                ctx.guild.id,
                ctx.author.id,
                'speed',
                round(speed, 1)  # Round to 1 decimal place
            )
            
            if not result.success:
                raise commands.CommandError(result.error)
                
            embed = self._create_embed(
                f"TTS speed changed to {speed}x",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
            # Update metrics
            self.bot.metrics.track_command('speed', time.time() - start_time)
            
        except ValueError:
            await ctx.send(
                embed=self._create_embed(
                    "Please provide a valid number for speed (e.g., 1.5)",
                    color=discord.Color.red()
                )
            )
        except Exception as e:
            await self.bot.error_handler.handle_command_error(e, ctx, 'speed')
            await ctx.send(
                embed=self._create_embed(str(e), color=discord.Color.red())
            )
            
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle messages for TTS conversion"""
        try:
            # Ignore bot messages and commands
            if message.author.bot or message.content.startswith(self.bot.command_prefix):
                return

            # Check if bot is in voice channel
            if not message.guild or not message.guild.voice_client:
                return

            # Get user settings
            settings = self.bot.settings_manager.get_user_settings(
                message.guild.id,
                message.author.id
            )

            # Generate audio
            audio_result = await self.bot.tts_engine.generate_audio(
                text=message.content,
                voice=settings['voice'],
                speed=settings['speed'],
                lang=settings['lang']
            )

            if not audio_result.success:
                self.logger.error(f"TTS generation failed: {audio_result.error}")
                return

            # Add to queue with priority based on role
            priority = 1
            if message.author.guild_permissions.administrator:
                priority = 0

            queue_result = await self.bot.queue_manager.add_to_queue(
                message.guild.id,
                audio_result.value,
                message.content,
                priority
            )

            if not queue_result.success:
                self.logger.error(f"Queue add failed: {queue_result.error}")
                return

            # Start playing if not already playing
            voice_client = message.guild.voice_client
            if voice_client and not voice_client.is_playing():
                await self._play_audio(message.guild.id, voice_client)

            # Update metrics
            self.bot.metrics.track_message_processed()

            # Schedule message deletion after delay
            await self._schedule_message_deletion(message)

        except Exception as e:
            self.logger.error(f"Message handling error: {str(e)}")
            self.bot.metrics.track_error('message_handling')

    async def _schedule_message_deletion(self, message: discord.Message):
        """Schedule message deletion with error handling"""
        try:
            await asyncio.sleep(15)
            try:
                await message.delete()
            except discord.errors.NotFound:
                pass  # Message already deleted
            except discord.errors.Forbidden:
                self.logger.warning(
                    f"Bot lacks permission to delete message in channel {message.channel.id}"
                )
            except Exception as e:
                self.logger.error(f"Error deleting message: {str(e)}")
        except Exception as e:
            self.logger.error(f"Message deletion scheduling error: {str(e)}")

    async def _play_audio(self, guild_id: int, voice_client: discord.VoiceClient):
        """Enhanced audio playback with error handling"""
        try:
            while True:
                # Reset inactivity timer
                self.bot.inactivity_timers[guild_id] = 0
                
                # Get next queue item
                next_item_result = await self.bot.queue_manager.get_next(guild_id)
                if not next_item_result.success:
                    self.logger.error(f"Queue error: {next_item_result.error}")
                    break
                
                next_item = next_item_result.value
                if not next_item:
                    break

                # Create temporary file for audio
                temp_file = f"temp_{guild_id}.wav"
                try:
                    with open(temp_file, 'wb') as f:
                        f.write(next_item['audio'])
                    
                    # Play audio with error handling
                    try:
                        audio_source = discord.FFmpegPCMAudio(temp_file)
                        voice_client.play(
                            audio_source,
                            after=lambda e: self._handle_playback_error(e, guild_id)
                        )
                        
                        # Wait for playback to complete
                        while voice_client.is_playing():
                            await asyncio.sleep(0.1)
                    except Exception as e:
                        self.logger.error(f"Playback error: {str(e)}")
                        self.bot.metrics.track_error('playback')
                finally:
                    # Cleanup temporary file
                    try:
                        import os
                        os.remove(temp_file)
                    except:
                        pass

        except Exception as e:
            self.logger.error(f"Audio playback error: {str(e)}")
            self.bot.metrics.track_error('playback')

    def _handle_playback_error(self, error, guild_id: int):
        """Handle playback errors"""
        if error:
            self.logger.error(f"Playback error in guild {guild_id}: {str(error)}")
            self.bot.metrics.track_error('playback')

    def _create_embed(self, description: str, color: discord.Color) -> discord.Embed:
        """Create consistent embed messages"""
        embed = discord.Embed(
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Kokoro TTS Bot | {self.bot.command_prefix}help")
        return embed