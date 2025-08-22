import yaml
import os
from typing import Dict, Any
from pathlib import Path


class ConfigLoader:
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self, config_path: str = "config.yaml") -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            # Validate required configuration sections
            self._validate_config()
            
            # Create necessary directories
            self._create_directories()
            
            return self._config
            
        except Exception as e:
            raise Exception(f"Failed to load configuration: {str(e)}")
    
    def _validate_config(self):
        """Validate that all required configuration sections exist"""
        required_sections = ['ollama', 'vector_store', 'data', 'agent', 'sql', 'logging']
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Required configuration section '{section}' is missing")
        
        # Validate Ollama configuration
        if 'host' not in self._config['ollama'] or 'model' not in self._config['ollama']:
            raise ValueError("Ollama configuration must include 'host' and 'model'")
        
        # Validate SQL safety settings
        if self._config['sql'].get('allow_write', False):
            raise ValueError("SQL write operations are not allowed for security reasons")
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        dirs_to_create = [
            self._config['vector_store']['path'],
            self._config['data']['schema_path'],
            os.path.dirname(self._config['logging']['file'])
        ]
        
        for dir_path in dirs_to_create:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'ollama.host')"""
        if self._config is None:
            self.load_config()
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        if self._config is None:
            self.load_config()
        
        return self._config.get(section, {})
    
    def update(self, key: str, value: Any):
        """Update configuration value at runtime (does not persist to file)"""
        if self._config is None:
            self.load_config()
        
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary"""
        if self._config is None:
            self.load_config()
        return self._config


# Singleton instance
config_loader = ConfigLoader()