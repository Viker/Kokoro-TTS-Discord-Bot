"""
Queue management system for the Kokoro TTS Bot.
Handles message queues with priorities and limits.
"""

import time
import asyncio
from typing import Dict, List, Optional
from ..core.config import Config
from ..utils.result import Result

class QueueManager:
    """Enhanced message queue with priorities and limits"""
    
    def __init__(self, config: Config):
        """Initialize the queue manager.
        
        Args:
            config: Configuration instance
        """
        self.queues: Dict[int, List[Dict]] = {}
        self.locks: Dict[int, asyncio.Lock] = {}
        self.max_queue_size = config.get('max_queue_size', 100)
        self.message_ttl = config.get('message_ttl', 300)  # 5 minutes

    async def add_to_queue(
        self,
        guild_id: int,
        audio_data: bytes,
        text: str,
        priority: int = 1
    ) -> Result:
        """Add message to queue with priority.
        
        Args:
            guild_id: ID of the guild
            audio_data: Audio data to queue
            text: Original text of the message
            priority: Message priority (lower = higher priority)
            
        Returns:
            Result indicating success or failure
        """
        try:
            async with self._get_lock(guild_id):
                if guild_id not in self.queues:
                    self.queues[guild_id] = []
                
                # Check queue size limit
                if len(self.queues[guild_id]) >= self.max_queue_size:
                    return Result.err("Queue is full")
                
                # Add message with metadata
                message = {
                    'audio': audio_data,
                    'text': text,
                    'priority': priority,
                    'timestamp': time.time(),
                    'ttl': time.time() + self.message_ttl
                }
                
                # Insert based on priority
                insert_idx = 0
                for i, item in enumerate(self.queues[guild_id]):
                    if item['priority'] <= priority:
                        insert_idx = i + 1
                self.queues[guild_id].insert(insert_idx, message)
                
                return Result.ok(True)
        except Exception as e:
            return Result.err(str(e))

    async def get_next(self, guild_id: int) -> Result:
        """Get next message from queue with TTL checking.
        
        Args:
            guild_id: ID of the guild
            
        Returns:
            Result containing the next message or None if queue is empty
        """
        try:
            async with self._get_lock(guild_id):
                if not self.queues.get(guild_id):
                    return Result.ok(None)
                
                # Remove expired messages
                current_time = time.time()
                self.queues[guild_id] = [
                    msg for msg in self.queues[guild_id]
                    if msg['ttl'] > current_time
                ]
                
                if not self.queues[guild_id]:
                    return Result.ok(None)
                
                return Result.ok(self.queues[guild_id].pop(0))
        except Exception as e:
            return Result.err(str(e))

    def _get_lock(self, guild_id: int) -> asyncio.Lock:
        """Get or create lock for guild.
        
        Args:
            guild_id: ID of the guild
            
        Returns:
            Lock for the guild
        """
        if guild_id not in self.locks:
            self.locks[guild_id] = asyncio.Lock()
        return self.locks[guild_id]

    def get_queue_size(self, guild_id: int) -> int:
        """Get current size of queue for a guild.
        
        Args:
            guild_id: ID of the guild
            
        Returns:
            Number of messages in queue
        """
        return len(self.queues.get(guild_id, []))

    def clear_queue(self, guild_id: int) -> None:
        """Clear all messages from a guild's queue.
        
        Args:
            guild_id: ID of the guild
        """
        if guild_id in self.queues:
            self.queues[guild_id].clear()

    def get_queues_status(self) -> Dict:
        """Get status of all queues.
        
        Returns:
            Dictionary containing queue status information
        """
        return {
            guild_id: {
                'size': len(queue),
                'oldest_message': min((msg['timestamp'] for msg in queue), default=None),
                'newest_message': max((msg['timestamp'] for msg in queue), default=None),
                'priority_distribution': self._get_priority_distribution(queue)
            }
            for guild_id, queue in self.queues.items()
        }

    def _get_priority_distribution(self, queue: List[Dict]) -> Dict[int, int]:
        """Get distribution of priorities in a queue.
        
        Args:
            queue: List of queued messages
            
        Returns:
            Dictionary mapping priority levels to counts
        """
        priority_counts: Dict[int, int] = {}
        for msg in queue:
            priority = msg['priority']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        return priority_counts