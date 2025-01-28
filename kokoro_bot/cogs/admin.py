"""
Admin commands for bot management.
"""

import discord
from discord.ext import commands
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..bot import KokoroTTSBot

class AdminCog(commands.Cog):
    """Admin commands for bot management"""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the admin cog.
        
        Args:
            bot: Bot instance
        """
        self.bot = bot

    @commands.command(name='metrics')
    @commands.has_permissions(administrator=True)
    async def show_metrics(self, ctx: commands.Context):
        """Show bot metrics and performance data"""
        metrics = self.bot.metrics.get_metrics_report()
        
        embed = discord.Embed(
            title="Bot Metrics",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        # Command Performance
        avg_latency = {
            cmd: f"{lat:.2f}ms"
            for cmd, lat in metrics['command_latency'].items()
        }
        embed.add_field(
            name="Command Latency",
            value="\n".join(f"{cmd}: {lat}" for cmd, lat in avg_latency.items()),
            inline=False
        )
        
        # Error Stats
        embed.add_field(
            name="Errors",
            value="\n".join(
                f"{type_}: {count}"
                for type_, count in metrics['error_counts'].items()
            ),
            inline=False
        )
        
        # Cache Performance
        cache_stats = metrics['cache_stats']
        embed.add_field(
            name="Cache Performance",
            value=f"Hit Rate: {cache_stats.get('hit_rate', 0):.2%}\n"
                  f"Size: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 0)}",
            inline=False
        )
        
        # TTS Performance
        tts_stats = metrics['tts_performance']
        embed.add_field(
            name="TTS Performance",
            value=f"Avg Generation Time: {tts_stats['avg_generation_time']:.2f}s",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='cleanup')
    @commands.has_permissions(administrator=True)
    async def cleanup_resources(self, ctx: commands.Context):
        """Clean up bot resources and connections"""
        try:
            # Cleanup voice connections
            for guild in self.bot.guilds:
                if guild.voice_client:
                    await self.bot.voice_manager.cleanup_connection(guild.id)
            
            # Clear queues
            for guild_id in list(self.bot.queue_manager.queues.keys()):
                await self.bot.queue_manager.get_next(guild_id)
            
            await ctx.send(embed=self._create_embed(
                "Resources cleaned up successfully",
                color=discord.Color.green()
            ))
        except Exception as e:
            await ctx.send(embed=self._create_embed(
                f"Cleanup failed: {str(e)}",
                color=discord.Color.red()
            ))

    def _create_embed(self, description: str, color: discord.Color) -> discord.Embed:
        """Create consistent embed messages"""
        embed = discord.Embed(
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Kokoro TTS Bot | Admin")
        return embed