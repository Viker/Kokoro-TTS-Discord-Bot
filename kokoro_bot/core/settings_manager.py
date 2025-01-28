"""
Settings management system for the Kokoro TTS Bot.
Handles guild and user settings with persistence and validation.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from ..utils.result import Result

class SettingsManager:
    """Enhanced settings management with validation and persistence.
    
    This class manages both guild-wide and user-specific settings,
    with proper validation, persistence, and default values.
    
    Attributes:
        config: Configuration instance
        guild_settings: Dictionary of guild-specific settings
        user_settings: Nested dictionary of user-specific settings
        default_settings: Dictionary of default setting values
    """
    
    def __init__(self, config):
        """Initialize the settings manager.
        
        Args:
            config: Configuration instance containing settings file path
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize settings dictionaries
        self.guild_settings: Dict[int, Dict[str, Any]] = {}
        self.user_settings: Dict[int, Dict[int, Dict[str, Any]]] = {}
        
        # Define default settings
        self.default_settings = {
            'voice': 'default',  # Default voice ID
            'speed': 1.0,       # Speech speed multiplier
            'pitch': 1.0,       # Pitch adjustment
            'volume': 1.0,      # Volume level
            'lang': 'en-us',    # Language code
            'auto_join': False, # Auto-join voice channels
            'read_usernames': True,  # Read usernames when users join
            'ignore_bots': True,     # Ignore bot messages
            'max_length': 500,       # Maximum message length
            'timeout': 300,          # Inactivity timeout (seconds)
        }
        
        # Load existing settings
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from persistent storage."""
        try:
            settings_file = self.config.get('settings_file', 'settings.yaml')
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        # Convert string keys back to integers for guild/user IDs
                        self.guild_settings = {
                            int(k): v for k, v in data.get('guild_settings', {}).items()
                        }
                        self.user_settings = {
                            int(guild_id): {
                                int(user_id): settings
                                for user_id, settings in guild_data.items()
                            }
                            for guild_id, guild_data in data.get('user_settings', {}).items()
                        }
                        self.logger.info("Settings loaded successfully")
                    else:
                        self.logger.warning("No settings data found, using defaults")
        except Exception as e:
            self.logger.error(f"Failed to load settings: {str(e)}")
            # Continue with empty settings rather than crashing

    def _save_settings(self) -> None:
        """Save settings to persistent storage."""
        try:
            settings_file = self.config.get('settings_file', 'settings.yaml')
            with open(settings_file, 'w', encoding='utf-8') as f:
                yaml.dump({
                    'guild_settings': self.guild_settings,
                    'user_settings': self.user_settings
                }, f, default_flow_style=False)
            self.logger.debug("Settings saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save settings: {str(e)}")

    def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get settings for a specific guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary containing guild settings with defaults
        """
        guild_settings = self.guild_settings.get(guild_id, {})
        return {**self.default_settings, **guild_settings}

    def get_user_settings(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Get settings for a specific user in a guild.
        
        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            
        Returns:
            Dictionary containing user settings with guild and default fallbacks
        """
        # Start with default settings
        settings = self.default_settings.copy()
        
        # Apply guild overrides
        guild_settings = self.guild_settings.get(guild_id, {})
        settings.update(guild_settings)
        
        # Apply user overrides
        user_settings = self.user_settings.get(guild_id, {}).get(user_id, {})
        settings.update(user_settings)
        
        return settings

    def set_guild_setting(self, guild_id: int, setting: str, value: Any) -> Result:
        """Set a setting for a specific guild.
        
        Args:
            guild_id: Discord guild ID
            setting: Setting name to change
            value: New value for the setting
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Validate setting exists
            if setting not in self.default_settings:
                return Result.err(f"Invalid setting: {setting}")
            
            # Validate value type
            expected_type = type(self.default_settings[setting])
            if not isinstance(value, expected_type):
                return Result.err(
                    f"Invalid type for {setting}. Expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )
            
            # Validate value range if applicable
            if not self._validate_setting_value(setting, value):
                return Result.err(f"Invalid value for {setting}")
            
            # Update setting
            if guild_id not in self.guild_settings:
                self.guild_settings[guild_id] = {}
            self.guild_settings[guild_id][setting] = value
            
            # Save changes
            self._save_settings()
            return Result.ok(True)
            
        except Exception as e:
            self.logger.error(f"Error setting guild setting: {str(e)}")
            return Result.err(str(e))

    def set_user_setting(self, guild_id: int, user_id: int, setting: str, value: Any) -> Result:
        """Set a setting for a specific user in a guild.
        
        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            setting: Setting name to change
            value: New value for the setting
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Validate setting exists
            if setting not in self.default_settings:
                return Result.err(f"Invalid setting: {setting}")
            
            # Validate value type
            expected_type = type(self.default_settings[setting])
            if not isinstance(value, expected_type):
                return Result.err(
                    f"Invalid type for {setting}. Expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )
            
            # Validate value range if applicable
            if not self._validate_setting_value(setting, value):
                return Result.err(f"Invalid value for {setting}")
            
            # Initialize nested dictionaries if needed
            if guild_id not in self.user_settings:
                self.user_settings[guild_id] = {}
            if user_id not in self.user_settings[guild_id]:
                self.user_settings[guild_id][user_id] = {}
            
            # Update setting
            self.user_settings[guild_id][user_id][setting] = value
            
            # Save changes
            self._save_settings()
            return Result.ok(True)
            
        except Exception as e:
            self.logger.error(f"Error setting user setting: {str(e)}")
            return Result.err(str(e))

    def reset_user_settings(self, guild_id: int, user_id: int) -> Result:
        """Reset all settings for a specific user in a guild.
        
        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            
        Returns:
            Result indicating success or failure
        """
        try:
            if guild_id in self.user_settings and user_id in self.user_settings[guild_id]:
                del self.user_settings[guild_id][user_id]
                if not self.user_settings[guild_id]:
                    del self.user_settings[guild_id]
                self._save_settings()
            return Result.ok(True)
        except Exception as e:
            self.logger.error(f"Error resetting user settings: {str(e)}")
            return Result.err(str(e))

    def _validate_setting_value(self, setting: str, value: Any) -> bool:
        """Validate a setting value based on setting-specific rules.
        
        Args:
            setting: Setting name to validate
            value: Value to validate
            
        Returns:
            True if value is valid, False otherwise
        """
        try:
            if setting == 'speed':
                return 0.5 <= float(value) <= 2.0
            elif setting == 'pitch':
                return 0.5 <= float(value) <= 2.0
            elif setting == 'volume':
                return 0.0 <= float(value) <= 2.0
            elif setting == 'max_length':
                return 1 <= int(value) <= 2000
            elif setting == 'timeout':
                return 0 <= int(value) <= 3600
            return True
        except (ValueError, TypeError):
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all available settings and their default values.
        
        Returns:
            Dictionary of all settings and their defaults
        """
        return self.default_settings.copy()

    def get_setting_info(self, setting: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific setting.
        
        Args:
            setting: Setting name
            
        Returns:
            Dictionary containing setting information or None if setting doesn't exist
        """
        setting_info = {
            'speed': {
                'type': 'float',
                'range': '0.5 to 2.0',
                'description': 'Speech speed multiplier'
            },
            'pitch': {
                'type': 'float',
                'range': '0.5 to 2.0',
                'description': 'Voice pitch adjustment'
            },
            'volume': {
                'type': 'float',
                'range': '0.0 to 2.0',
                'description': 'Audio volume level'
            },
            'voice': {
                'type': 'string',
                'description': 'TTS voice identifier'
            },
            'lang': {
                'type': 'string',
                'description': 'Language code (e.g., en-us)'
            },
            'auto_join': {
                'type': 'boolean',
                'description': 'Automatically join voice channels'
            },
            'read_usernames': {
                'type': 'boolean',
                'description': 'Read usernames when users join'
            },
            'ignore_bots': {
                'type': 'boolean',
                'description': 'Ignore messages from bots'
            },
            'max_length': {
                'type': 'integer',
                'range': '1 to 2000',
                'description': 'Maximum message length'
            },
            'timeout': {
                'type': 'integer',
                'range': '0 to 3600',
                'description': 'Inactivity timeout in seconds'
            }
        }
        return setting_info.get(setting)