"""
LRU Cache implementation with TTL and metrics.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Generic, TypeVar, Optional, Any
import asyncio
import sys

T = TypeVar('T')

@dataclass
class CacheEntry(Generic[T]):
    value: T
    expiry: datetime
    access_count: int = 0

class LRUCache:
    """Enhanced LRU cache with TTL and metrics"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0
        
    async def get(self, key: str) -> Optional[T]:
        """Get value from cache with TTL check"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry.expiry:
                    entry.access_count += 1
                    self.hits += 1
                    return entry.value
                else:
                    del self._cache[key]
            self.misses += 1
            return None
    
    async def put(self, key: str, value: T) -> None:
        """Add value to cache with LRU eviction"""
        async with self._lock:
            # Evict expired entries
            now = datetime.now()
            expired = [k for k, v in self._cache.items() if now >= v.expiry]
            for k in expired:
                del self._cache[k]
            
            # LRU eviction if still needed
            if len(self._cache) >= self.max_size:
                sorted_items = sorted(
                    self._cache.items(),
                    key=lambda x: (x[1].access_count, x[1].expiry)
                )
                for k, _ in sorted_items[:len(self._cache) - self.max_size + 1]:
                    del self._cache[k]
            
            self._cache[key] = CacheEntry(
                value=value,
                expiry=now + timedelta(seconds=self.ttl_seconds)
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hit_rate': hit_rate,
            'hits': self.hits,
            'misses': self.misses,
            'memory_usage': sum(sys.getsizeof(v.value) for v in self._cache.values())
        }