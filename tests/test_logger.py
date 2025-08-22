import sys
import os
import unittest
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger, setup_logging, QueryLogger


class TestLogger(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.test_logger = get_logger('test_logger')
        self.query_logger = QueryLogger()
    
    def test_logger_creation(self):
        """Test logger creation"""
        print("Testing logger creation...")
        
        logger = get_logger('test_module')
        self.assertIsNotNone(logger)
        print("  [OK] Logger created successfully")
        
        # Test logging
        try:
            logger.info("Test info message")
            logger.debug("Test debug message")
            logger.warning("Test warning message")
            print("  [OK] Logging messages work")
        except Exception as e:
            self.fail(f"Logger failed: {str(e)}")
    
    def test_log_file_creation(self):
        """Test that log file is created"""
        print("Testing log file creation...")
        
        log_path = Path("./logs/agent.log")
        
        # Log something to ensure file creation
        self.test_logger.info("Test message for file creation")
        
        # Check if log file exists
        self.assertTrue(log_path.exists())
        print(f"  [OK] Log file exists: {log_path}")
    
    def test_query_logger_sql(self):
        """Test SQL query logging"""
        print("Testing SQL query logging...")
        
        # Test successful query
        self.query_logger.log_sql_query(
            "SELECT * FROM users",
            result=[{"id": 1, "name": "test"}]
        )
        print("  [OK] SQL success logging works")
        
        # Test failed query
        self.query_logger.log_sql_query(
            "DROP TABLE users",
            error=Exception("Query rejected: Write operations not allowed")
        )
        print("  [OK] SQL error logging works")
    
    def test_query_logger_tool(self):
        """Test tool call logging"""
        print("Testing tool call logging...")
        
        # Test successful tool call
        self.query_logger.log_tool_call(
            "rag_search",
            {"query": "find users table"},
            output="Found 3 results"
        )
        print("  [OK] Tool success logging works")
        
        # Test failed tool call
        self.query_logger.log_tool_call(
            "sql_query",
            {"query": "invalid sql"},
            error=Exception("SQL parse error")
        )
        print("  [OK] Tool error logging works")
    
    def test_query_logger_conversation(self):
        """Test conversation logging"""
        print("Testing conversation logging...")
        
        self.query_logger.log_conversation(
            "What is the users table structure?",
            "The users table has columns: id, name, email..."
        )
        print("  [OK] Conversation logging works")
    
    def test_query_logger_rag_search(self):
        """Test RAG search logging"""
        print("Testing RAG search logging...")
        
        results = [
            {"text": "Result 1", "score": 0.95},
            {"text": "Result 2", "score": 0.85},
        ]
        
        self.query_logger.log_rag_search("test query", results)
        print("  [OK] RAG search logging works")


if __name__ == '__main__':
    print("\n" + "="*50)
    print("LOGGER TESTS")
    print("="*50 + "\n")
    
    # Run tests
    unittest.main(verbosity=0, exit=False)