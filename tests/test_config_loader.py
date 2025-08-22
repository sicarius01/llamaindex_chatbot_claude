import sys
import os
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_loader import ConfigLoader


class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.config_loader = ConfigLoader()
        
    def test_load_config(self):
        """Test config file loading"""
        print("Testing config loading...")
        config = self.config_loader.load_config("config.yaml")
        
        # Check that config is loaded
        self.assertIsNotNone(config)
        self.assertIsInstance(config, dict)
        
        # Check required sections exist
        required_sections = ['ollama', 'vector_store', 'data', 'agent', 'sql', 'logging']
        for section in required_sections:
            self.assertIn(section, config)
            print(f"  [OK] Section '{section}' exists")
    
    def test_get_value(self):
        """Test getting config values with dot notation"""
        print("Testing get value with dot notation...")
        
        # Test getting nested values
        ollama_model = self.config_loader.get('ollama.model')
        self.assertIsNotNone(ollama_model)  # Dynamic check - any model is valid
        print(f"  [OK] ollama.model = {ollama_model}")
        
        ollama_host = self.config_loader.get('ollama.host')
        self.assertEqual(ollama_host, 'http://localhost')
        print(f"  [OK] ollama.host = {ollama_host}")
        
        # Test default value
        non_existent = self.config_loader.get('non.existent.key', 'default')
        self.assertEqual(non_existent, 'default')
        print("  [OK] Default value works")
    
    def test_get_section(self):
        """Test getting entire config section"""
        print("Testing get section...")
        
        ollama_section = self.config_loader.get_section('ollama')
        self.assertIsInstance(ollama_section, dict)
        self.assertIn('model', ollama_section)
        self.assertIn('host', ollama_section)
        print(f"  [OK] Ollama section retrieved: {list(ollama_section.keys())}")
    
    def test_sql_safety_validation(self):
        """Test that SQL write operations are disabled"""
        print("Testing SQL safety validation...")
        
        allow_write = self.config_loader.get('sql.allow_write')
        self.assertFalse(allow_write)
        print(f"  [OK] SQL write operations disabled: allow_write = {allow_write}")
    
    def test_directory_creation(self):
        """Test that required directories are created"""
        print("Testing directory creation...")
        
        # Check if directories exist
        dirs_to_check = [
            Path(self.config_loader.get('vector_store.path')),
            Path(self.config_loader.get('data.schema_path')),
            Path(self.config_loader.get('logging.file')).parent
        ]
        
        for dir_path in dirs_to_check:
            self.assertTrue(dir_path.exists())
            print(f"  [OK] Directory exists: {dir_path}")
    
    def test_update_value(self):
        """Test updating config values at runtime"""
        print("Testing update value...")
        
        # Update a value
        self.config_loader.update('agent.verbose', False)
        verbose_value = self.config_loader.get('agent.verbose')
        self.assertFalse(verbose_value)
        print(f"  [OK] Updated agent.verbose to False")
        
        # Restore original value
        self.config_loader.update('agent.verbose', True)
        verbose_value = self.config_loader.get('agent.verbose')
        self.assertTrue(verbose_value)
        print(f"  [OK] Restored agent.verbose to True")


if __name__ == '__main__':
    print("\n" + "="*50)
    print("CONFIG LOADER TESTS")
    print("="*50 + "\n")
    
    # Run tests
    unittest.main(verbosity=0, exit=False)