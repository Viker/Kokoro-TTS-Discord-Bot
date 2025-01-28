from typing import Dict, Any
import yaml
import os
import time
import logging

class Config:
    """Enhanced configuration management with validation and hot-reloading"""
    def __init__(self, config_path: str = 'config.yaml'):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.last_load_time = 0
        self.reload_interval = 300  # 5 minutes
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file with environment variable support"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Override with environment variables
            for key in self.config:
                env_value = os.getenv(f'KOKORO_{key.upper()}')
                if env_value:
                    self.config[key] = env_value
                    
            self.last_load_time = time.time()
            self._validate_config()
            
        except Exception as e:
            logging.error(f"Failed to load config: {str(e)}")
            raise RuntimeError(f"Configuration error: {str(e)}")

    def _validate_config(self) -> None:
        """Validate configuration values"""
        required_fields = ['discord_token', 'command_prefix', 'max_cache_size']
        missing = [field for field in required_fields if field not in self.config]
        if missing:
            raise ValueError(f"Missing required config fields: {missing}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with automatic reload"""
        if time.time() - self.last_load_time > self.reload_interval:
            self._load_config()
        return self.config.get(key, default)