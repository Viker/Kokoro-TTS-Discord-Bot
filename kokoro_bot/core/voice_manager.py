"""
Voice connection management system for the Kokoro TTS Bot.
Handles voice connections, health monitoring, and cleanup.
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
import discord
from ..utils.result import Result

class VoiceConnectionManager:
    """
    Manages voice connections with health monitoring and connection lifecycle.
    """
    
    def __init__(self, metrics):
        self.connections: Dict[int, discord.VoiceClient] = {}
        self.locks: Dict[int, asyncio.Lock] = {}
        self.health_checks: Dict[int, datetime] = {}
        self.metrics = metrics
        self.logger = logging.getLogger(__name__)
        
        # Start background health monitoring
        self._start_health_monitor()

    def _start_health_monitor(self) -> None:
        """Start the background health monitoring task."""
        asyncio.create_task(self._monitor_connections())

    async def _monitor_connections(self) -> None:
        """
        Monitor connection health without disconnecting.
        Only logs issues and updates health checks.
        """
        while True:
            try:
                for guild_id, connection in list(self.connections.items()):
                    try:
                        if not connection.is_connected():
                            self.logger.warning(
                                f"Voice client disconnected in guild {guild_id}"
                            )
                            self.metrics.track_voice_disconnect(guild_id)
                            # Don't call cleanup_connection here
                            continue
                        
                        # Check latency but don't disconnect
                        if hasattr(connection, 'latency'):
                            if connection.latency > 1.0:
                                self.logger.warning(
                                    f"High latency detected in guild {guild_id}: "
                                    f"{connection.latency}s"
                                )
                        
                        # Update health check timestamp
                        self.health_checks[guild_id] = datetime.now()
                        
                    except Exception as e:
                        self.logger.error(
                            f"Error checking connection for guild {guild_id}: {str(e)}"
                        )
                        # Don't call cleanup_connection here
                
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                self.logger.info("Health monitor task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in health monitor: {str(e)}")
                await asyncio.sleep(60)

    async def cleanup_connection(self, guild_id: int) -> None:
        """
        Clean up a voice connection for a guild.
        Only stops playing audio without disconnecting.
        """
        try:
            async with self._get_lock(guild_id):
                if guild_id in self.connections:
                    connection = self.connections[guild_id]
                    
                    try:
                        # Only stop playing audio
                        if connection.is_playing():
                            connection.stop()
                        
                        # Don't disconnect
                        
                    except Exception as e:
                        self.logger.error(
                            f"Error stopping audio in guild {guild_id}: {str(e)}"
                        )
                    
                    # Don't remove from connections dictionary
                    self.logger.info(f"Stopped audio for guild {guild_id}")
                    
        except Exception as e:
            self.logger.error(f"Error in cleanup_connection: {str(e)}")

    async def disconnect_all(self) -> None:
        """Stop all audio playback without disconnecting."""
        for guild_id in list(self.connections.keys()):
            await self.cleanup_connection(guild_id)

    async def get_connection(
        self,
        guild_id: int,
        channel: discord.VoiceChannel
    ) -> Result[discord.VoiceClient]:
        """Get or create a voice connection for a guild."""
        try:
            async with self._get_lock(guild_id):
                if guild_id in self.connections:
                    connection = self.connections[guild_id]
                    
                    if connection.channel.id != channel.id:
                        try:
                            await connection.move_to(channel)
                            self.logger.info(
                                f"Moved voice connection to channel {channel.id} "
                                f"in guild {guild_id}"
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to move voice connection: {str(e)}"
                            )
                            # Don't cleanup on move failure
                            return Result.err(f"Could not move to channel: {str(e)}")
                    else:
                        return Result.ok(connection)
                
                # Create new connection
                try:
                    connection = await channel.connect(timeout=20.0)
                    self.connections[guild_id] = connection
                    self.health_checks[guild_id] = datetime.now()
                    
                    self.logger.info(
                        f"Created new voice connection in guild {guild_id}, "
                        f"channel {channel.id}"
                    )
                    
                    return Result.ok(connection)
                    
                except Exception as e:
                    self.logger.error(
                        f"Failed to create voice connection: {str(e)}"
                    )
                    return Result.err(f"Could not connect to voice: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error in get_connection: {str(e)}")
            return Result.err(str(e))

    def _get_lock(self, guild_id: int) -> asyncio.Lock:
        """
        Get or create a lock for a guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            An asyncio Lock for the guild
        """
        if guild_id not in self.locks:
            self.locks[guild_id] = asyncio.Lock()
        return self.locks[guild_id]

    def get_voice_client(self, guild_id: int) -> Optional[discord.VoiceClient]:
        """
        Get the voice client for a guild if it exists.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            The voice client if it exists, None otherwise
        """
        return self.connections.get(guild_id)

    def is_connected(self, guild_id: int) -> bool:
        """
        Check if connected to a voice channel in a guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            True if connected, False otherwise
        """
        client = self.get_voice_client(guild_id)
        return client is not None and client.is_connected()

    async def pause(self, guild_id: int) -> Result:
        """
        Pause audio playback in a guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            Result indicating success or failure
        """
        try:
            client = self.get_voice_client(guild_id)
            if client and client.is_playing():
                client.pause()
                return Result.ok(True)
            return Result.err("No audio playing")
        except Exception as e:
            return Result.err(str(e))

    async def resume(self, guild_id: int) -> Result:
        """
        Resume audio playback in a guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            Result indicating success or failure
        """
        try:
            client = self.get_voice_client(guild_id)
            if client and client.is_paused():
                client.resume()
                return Result.ok(True)
            return Result.err("No audio paused")
        except Exception as e:
            return Result.err(str(e))

    async def stop(self, guild_id: int) -> Result:
        """
        Stop audio playback in a guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            Result indicating success or failure
        """
        try:
            client = self.get_voice_client(guild_id)
            if client and (client.is_playing() or client.is_paused()):
                client.stop()
                return Result.ok(True)
            return Result.err("No audio playing")
        except Exception as e:
            return Result.err(str(e))

    def get_connection_status(self, guild_id: int) -> Dict:
        """
        Get detailed status of a voice connection.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            Dictionary containing connection status information
        """
        client = self.get_voice_client(guild_id)
        if not client:
            return {'connected': False}
            
        return {
            'connected': client.is_connected(),
            'playing': client.is_playing(),
            'paused': client.is_paused(),
            'channel_id': client.channel.id if client.channel else None,
            'latency': getattr(client, 'latency', None),
            'last_health_check': self.health_checks.get(guild_id)
        }