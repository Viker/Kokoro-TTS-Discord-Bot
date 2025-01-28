"""
Centralized error handling system for the Kokoro TTS Bot.
"""

import logging
import discord
import asyncio
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime

class ErrorHandler:
    """Centralized error handling with recovery mechanisms"""
    
    def __init__(self, logger: logging.Logger):
        """Initialize the error handler.
        
        Args:
            logger: Logger instance for error logging
        """
        self.logger = logger
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.last_errors: Dict[str, List[dict]] = defaultdict(list)
        self.MAX_ERROR_HISTORY = 10
        
    async def handle_command_error(
        self,
        error: Exception,
        ctx: discord.ext.commands.Context,
        command_name: str
    ) -> bool:
        """Handle command-specific errors with context.
        
        Args:
            error: The error that occurred
            ctx: Command context
            command_name: Name of the command that failed
            
        Returns:
            bool: True if recovery should be attempted, False otherwise
        """
        error_key = f"{ctx.guild.id}:{command_name}"
        self.error_counts[error_key] += 1
        
        # Store error history
        self.last_errors[error_key].append({
            'timestamp': datetime.now(),
            'error': str(error),
            'user_id': ctx.author.id if ctx.author else None,
            'channel_id': ctx.channel.id if ctx.channel else None
        })
        
        # Keep only recent errors
        self.last_errors[error_key] = self.last_errors[error_key][-self.MAX_ERROR_HISTORY:]
        
        # Log with context
        self.logger.error(
            f"Command '{command_name}' failed in guild {ctx.guild.id}",
            extra={
                'guild_id': ctx.guild.id,
                'channel_id': ctx.channel.id if ctx.channel else None,
                'user_id': ctx.author.id if ctx.author else None,
                'error': str(error)
            },
            exc_info=error
        )
        
        # Determine if we should attempt recovery
        should_recover = self.error_counts[error_key] < 3
        
        if should_recover:
            try:
                # Attempt recovery based on error type
                if isinstance(error, discord.errors.ClientException):
                    await self._handle_client_exception(ctx)
                elif isinstance(error, discord.errors.HTTPException):
                    await self._handle_http_exception(ctx)
                else:
                    await self._handle_generic_error(ctx)
            except Exception as recovery_error:
                self.logger.error(
                    f"Recovery failed: {str(recovery_error)}",
                    exc_info=recovery_error
                )
                should_recover = False
        
        return should_recover

    async def _handle_client_exception(
        self,
        ctx: discord.ext.commands.Context
    ) -> bool:
        """Handle Discord client-specific errors.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        try:
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
                await asyncio.sleep(1)
                if ctx.author.voice:
                    await ctx.author.voice.channel.connect()
                    return True
        except Exception as e:
            self.logger.error(f"Failed to handle client exception: {str(e)}")
        return False

    async def _handle_http_exception(
        self,
        ctx: discord.ext.commands.Context
    ) -> bool:
        """Handle HTTP-related errors with exponential backoff.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        for i in range(3):  # Try 3 times
            try:
                await asyncio.sleep(2 ** i)  # Exponential backoff
                # Attempt to resend the last message
                if hasattr(ctx, 'last_message'):
                    await ctx.send(ctx.last_message)
                return True
            except Exception as e:
                self.logger.warning(f"Retry {i+1} failed: {str(e)}")
        return False

    async def _handle_generic_error(
        self,
        ctx: discord.ext.commands.Context
    ) -> bool:
        """Handle general errors with basic recovery.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        try:
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
            await asyncio.sleep(1)
            return True
        except Exception as e:
            self.logger.error(f"Failed to handle generic error: {str(e)}")
            return False

    def get_error_stats(self, guild_id: Optional[int] = None) -> Dict:
        """Get error statistics for a guild or globally.
        
        Args:
            guild_id: Optional guild ID to filter stats
            
        Returns:
            Dictionary containing error statistics
        """
        stats = {
            'total_errors': 0,
            'errors_by_command': defaultdict(int),
            'recent_errors': []
        }
        
        for error_key, count in self.error_counts.items():
            if guild_id is None or str(guild_id) in error_key:
                guild_command = error_key.split(':')
                command = guild_command[1] if len(guild_command) > 1 else 'unknown'
                stats['total_errors'] += count
                stats['errors_by_command'][command] += count
        
        for error_key, errors in self.last_errors.items():
            if guild_id is None or str(guild_id) in error_key:
                stats['recent_errors'].extend(errors)
        
        # Sort recent errors by timestamp
        stats['recent_errors'] = sorted(
            stats['recent_errors'],
            key=lambda x: x['timestamp'],
            reverse=True
        )[:self.MAX_ERROR_HISTORY]
        
        return dict(stats)

    def clear_error_history(self, guild_id: Optional[int] = None) -> None:
        """Clear error history for a guild or globally.
        
        Args:
            guild_id: Optional guild ID to clear history for
        """
        if guild_id is None:
            self.error_counts.clear()
            self.last_errors.clear()
        else:
            keys_to_remove = [
                k for k in self.error_counts.keys()
                if str(guild_id) in k
            ]
            for k in keys_to_remove:
                del self.error_counts[k]
                if k in self.last_errors:
                    del self.last_errors[k]