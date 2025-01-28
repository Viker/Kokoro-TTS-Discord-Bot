"""
Metrics collection and monitoring system for the Kokoro TTS Bot.
"""

from typing import Dict, List, Any
from collections import defaultdict

class MetricsManager:
    """Comprehensive metrics collection and monitoring."""
    
    def __init__(self):
        """Initialize the metrics manager."""
        self.command_latency: Dict[str, List[float]] = defaultdict(list)
        self.tts_generation_times: List[float] = []
        self.errors_count: Dict[str, int] = defaultdict(int)
        self.total_messages_processed: int = 0
        self.voice_disconnects: Dict[int, int] = defaultdict(int)
        self.cache_stats: Dict[str, Any] = {}
        self.max_history_size = 1000  # Maximum number of samples to keep
        
    def track_command(self, command_name: str, latency: float) -> None:
        """Track command execution latency.
        
        Args:
            command_name: Name of the command
            latency: Execution time in seconds
        """
        self.command_latency[command_name].append(latency)
        if len(self.command_latency[command_name]) > self.max_history_size:
            self.command_latency[command_name] = \
                self.command_latency[command_name][-self.max_history_size:]

    def track_tts_generation(self, generation_time: float) -> None:
        """Track TTS generation time.
        
        Args:
            generation_time: Time taken to generate TTS audio in seconds
        """
        self.tts_generation_times.append(generation_time)
        if len(self.tts_generation_times) > self.max_history_size:
            self.tts_generation_times = self.tts_generation_times[-self.max_history_size:]

    def track_error(self, error_type: str) -> None:
        """Track error occurrences.
        
        Args:
            error_type: Type or category of error
        """
        self.errors_count[error_type] += 1

    def track_voice_disconnect(self, guild_id: int) -> None:
        """Track voice disconnections for a guild.
        
        Args:
            guild_id: ID of the guild where disconnect occurred
        """
        self.voice_disconnects[guild_id] += 1

    def update_cache_stats(self, stats: Dict[str, Any]) -> None:
        """Update cache performance metrics.
        
        Args:
            stats: Dictionary of cache statistics
        """
        self.cache_stats = stats

    def track_message_processed(self) -> None:
        """Track total number of messages processed."""
        self.total_messages_processed += 1

    def get_metrics_report(self) -> Dict[str, Any]:
        """Generate comprehensive metrics report.
        
        Returns:
            Dictionary containing all tracked metrics
        """
        return {
            'command_performance': {
                cmd: {
                    'avg_latency': sum(times) / len(times) if times else 0,
                    'min_latency': min(times) if times else 0,
                    'max_latency': max(times) if times else 0,
                    'total_calls': len(times)
                }
                for cmd, times in self.command_latency.items()
            },
            'tts_performance': {
                'avg_generation_time': (
                    sum(self.tts_generation_times) / len(self.tts_generation_times)
                    if self.tts_generation_times else 0
                ),
                'min_generation_time': min(self.tts_generation_times) if self.tts_generation_times else 0,
                'max_generation_time': max(self.tts_generation_times) if self.tts_generation_times else 0,
                'total_generations': len(self.tts_generation_times)
            },
            'error_statistics': {
                'total_errors': sum(self.errors_count.values()),
                'errors_by_type': dict(self.errors_count)
            },
            'voice_statistics': {
                'total_disconnects': sum(self.voice_disconnects.values()),
                'disconnects_by_guild': dict(self.voice_disconnects)
            },
            'cache_performance': self.cache_stats,
            'message_statistics': {
                'total_processed': self.total_messages_processed
            }
        }

    def get_command_stats(self, command_name: str) -> Dict[str, Any]:
        """Get detailed statistics for a specific command.
        
        Args:
            command_name: Name of the command to get stats for
            
        Returns:
            Dictionary containing command statistics
        """
        times = self.command_latency.get(command_name, [])
        if not times:
            return {
                'avg_latency': 0,
                'min_latency': 0,
                'max_latency': 0,
                'total_calls': 0,
                'recent_trend': []
            }
            
        return {
            'avg_latency': sum(times) / len(times),
            'min_latency': min(times),
            'max_latency': max(times),
            'total_calls': len(times),
            'recent_trend': times[-10:]  # Last 10 executions
        }

    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        self.__init__()

    def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        """Get metrics specific to a guild.
        
        Args:
            guild_id: ID of the guild to get stats for
            
        Returns:
            Dictionary containing guild-specific metrics
        """
        return {
            'voice_disconnects': self.voice_disconnects.get(guild_id, 0),
            'messages_processed': self.total_messages_processed,  # Total for now, could be guild-specific
            'error_count': sum(1 for err_type, count in self.errors_count.items() 
                             if str(guild_id) in err_type)
        }