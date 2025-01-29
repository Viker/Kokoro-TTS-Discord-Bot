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