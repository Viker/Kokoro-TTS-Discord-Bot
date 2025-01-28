"""
TTS engine implementation for the Kokoro TTS Bot.
"""

import io
import time
import logging
import numpy as np
import soundfile as sf
from typing import List, Dict
from datetime import datetime

from ..utils.cache import LRUCache
from ..utils.metrics import MetricsManager
from ..utils.error_handler import ErrorHandler
from ..utils.result import Result
from ..core.config import Config
from kokoro_onnx import Kokoro

class TTSEngine:
    """Enhanced TTS engine with caching and error recovery"""
    
    def __init__(self, model_path: str, voices_path: str, config: Config):
        """Initialize the TTS engine.
        
        Args:
            model_path: Path to the TTS model file
            voices_path: Path to the voices data file
            config: Configuration instance
        """
        self.kokoro = Kokoro(model_path, voices_path)
        self.cache = LRUCache(max_size=config.get('max_cache_size', 1000))
        self.metrics = MetricsManager()
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        # Circuit breaker configuration
        self.circuit_breaker = {
            'failures': 0,
            'last_failure': None,
            'threshold': config.get('circuit_breaker_threshold', 5),
            'recovery_time': config.get('circuit_breaker_recovery', 300)
        }
        
        # Initialize available voices
        self.available_voices = self._initialize_voices()
        if not self.available_voices:
            raise RuntimeError("No voices available in the TTS engine")

    def _initialize_voices(self) -> List[str]:
        """Initialize and validate available voices.
        
        Returns:
            List of available voice identifiers
        """
        try:
            voices = self.kokoro.get_voices()
            if not voices:
                raise RuntimeError("No voices found in the TTS engine")
            return voices
        except Exception as e:
            self.logger.error(f"Failed to initialize voices: {str(e)}")
            return []

    def get_default_voice(self) -> str:
        """Get the default voice identifier.
        
        Returns:
            Default voice identifier
        """
        if 'default' in self.available_voices:
            return 'default'
        return self.available_voices[0] if self.available_voices else 'default'

    async def generate_audio(
        self,
        text: str,
        voice: str,
        speed: float,
        lang: str
    ) -> Result:
        """Generate audio from text with caching and circuit breaker.
        
        Args:
            text: Text to convert to speech
            voice: Voice identifier to use
            speed: Speech speed multiplier
            lang: Language code
            
        Returns:
            Result containing audio data or error
        """
        try:
            # Validate voice
            if voice not in self.available_voices:
                return Result.err(f"Voice {voice} not found in available voices")

            # Check circuit breaker
            if self._is_circuit_open():
                return Result.err("Service temporarily unavailable")

            # Check cache
            cache_key = f"{text}-{voice}-{speed}-{lang}"
            cached_audio = await self.cache.get(cache_key)
            if cached_audio:
                return Result.ok(cached_audio)

            # Validate input
            if len(text) > 500:
                return Result.err("Message too long (max 500 characters)")

            # Generate audio
            start_time = time.time()
            try:
                samples = None
                sample_rate = None
                async for s, sr in self.kokoro.create_stream(text, voice, speed, lang):
                    samples = s if samples is None else np.concatenate((samples, s))
                    sample_rate = sr

                with io.BytesIO() as wav_io:
                    sf.write(wav_io, samples, sample_rate, format='WAV')
                    audio_data = wav_io.getvalue()

                # Cache result
                await self.cache.put(cache_key, audio_data)

                # Update metrics
                generation_time = time.time() - start_time
                self.metrics.track_tts_generation(generation_time)

                return Result.ok(audio_data)

            except Exception as e:
                self._record_failure()
                return Result.err(str(e))

        except Exception as e:
            return Result.err(str(e))

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open.
        
        Returns:
            True if circuit breaker is open, False otherwise
        """
        if self.circuit_breaker['failures'] >= self.circuit_breaker['threshold']:
            if self.circuit_breaker['last_failure']:
                elapsed = time.time() - self.circuit_breaker['last_failure']
                if elapsed < self.circuit_breaker['recovery_time']:
                    return True
                # Reset circuit breaker after recovery time
                self.circuit_breaker['failures'] = 0
        return False

    def _record_failure(self) -> None:
        """Record a failure for circuit breaker."""
        self.circuit_breaker['failures'] += 1
        self.circuit_breaker['last_failure'] = time.time()

    def get_voices(self) -> List[str]:
        """Get list of available voices.
        
        Returns:
            List of voice identifiers
        """
        return self.available_voices.copy()

    def get_status(self) -> Dict:
        """Get engine status information.
        
        Returns:
            Dictionary containing engine status
        """
        return {
            'available_voices': len(self.available_voices),
            'circuit_breaker_status': 'open' if self._is_circuit_open() else 'closed',
            'failures': self.circuit_breaker['failures'],
            'cache_stats': self.cache.get_metrics()
        }