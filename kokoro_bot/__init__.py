# kokoro_bot/__init__.py
"""
Kokoro TTS Bot - A Discord bot for text-to-speech conversion
"""

__version__ = '0.1.0'
__author__ = 'Your Name'
__email__ = 'your.email@example.com'

from .bot import KokoroTTSBot
from .core.config import Config

__all__ = ['KokoroTTSBot', 'Config']