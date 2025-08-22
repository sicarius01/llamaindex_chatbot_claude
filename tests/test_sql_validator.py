import sys
import os
import unittest

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'agent'))

# Import SQLValidator directly
import tools
SQLValidator = tools.SQLValidator


class TestSQLValidator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.validator = SQLValidator()
    
    def test_safe_select_queries(self):
        """Test that SELECT queries are allowed"""
        print("Testing safe SELECT queries...")
        
        safe_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE id = 1",
            "SELECT COUNT(*) FROM orders",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "WITH temp AS (SELECT * FROM users) SELECT * FROM temp",
        ]
        
        for query in safe_queries:
            is_safe, reason = self.validator.is_safe_query(query)
            self.assertTrue(is_safe, f"Query should be safe: {query}")
            print(f"  [OK] SAFE: {query[:50]}...")
    
    def test_dangerous_write_queries(self):
        """Test that write operations are blocked"""
        print("Testing dangerous write queries...")
        
        dangerous_queries = [
            "INSERT INTO users (name) VALUES ('test')",
            "UPDATE users SET name = 'test' WHERE id = 1",
            "DELETE FROM users WHERE id = 1",
            "DROP TABLE users",
            "CREATE TABLE test (id INT)",
            "ALTER TABLE users ADD COLUMN test VARCHAR(50)",
            "TRUNCATE TABLE users",
            "REPLACE INTO users VALUES (1, 'test')",
        ]
        
        for query in dangerous_queries:
            is_safe, reason = self.validator.is_safe_query(query)
            self.assertFalse(is_safe, f"Query should be dangerous: {query}")
            print(f"  [OK] BLOCKED: {query[:50]}...")
    
    def test_show_describe_queries(self):
        """Test that SHOW and DESCRIBE queries are allowed"""
        print("Testing SHOW/DESCRIBE queries...")
        
        info_queries = [
            "SHOW TABLES",
            "SHOW DATABASES",
            "DESCRIBE users",
            "EXPLAIN SELECT * FROM users",
        ]
        
        for query in info_queries:
            is_safe, reason = self.validator.is_safe_query(query)
            self.assertTrue(is_safe, f"Query should be safe: {query}")
            print(f"  [OK] SAFE: {query}")
    
    def test_case_insensitive_detection(self):
        """Test that detection works regardless of case"""
        print("Testing case insensitive detection...")
        
        # Lowercase dangerous query
        is_safe, _ = self.validator.is_safe_query("insert into users values (1)")
        self.assertFalse(is_safe)
        print("  [OK] Lowercase INSERT blocked")
        
        # Mixed case dangerous query
        is_safe, _ = self.validator.is_safe_query("DeLeTe FrOm UsErS")
        self.assertFalse(is_safe)
        print("  [OK] Mixed case DELETE blocked")
        
        # Uppercase safe query
        is_safe, _ = self.validator.is_safe_query("SELECT * FROM USERS")
        self.assertTrue(is_safe)
        print("  [OK] Uppercase SELECT allowed")
    
    def test_sql_injection_attempts(self):
        """Test that SQL injection attempts are handled"""
        print("Testing SQL injection prevention...")
        
        injection_attempts = [
            "SELECT * FROM users; DROP TABLE users",
            "SELECT * FROM users WHERE id = 1 OR 1=1; DELETE FROM users",
            "SELECT * FROM users -- ; DELETE FROM users",
        ]
        
        for query in injection_attempts:
            is_safe, reason = self.validator.is_safe_query(query)
            # Should be blocked because of dangerous keywords
            if "DROP" in query.upper() or "DELETE" in query.upper():
                self.assertFalse(is_safe)
                print(f"  [OK] Injection blocked: {query[:50]}...")
    
    def test_sanitize_query(self):
        """Test query sanitization"""
        print("Testing query sanitization...")
        
        # Test comment removal
        query_with_comment = "SELECT * FROM users -- this is a comment"
        sanitized = self.validator.sanitize_query(query_with_comment)
        self.assertNotIn("--", sanitized)
        print("  [OK] Comments removed")
        
        # Test whitespace normalization
        query_with_spaces = "SELECT    *     FROM      users"
        sanitized = self.validator.sanitize_query(query_with_spaces)
        self.assertEqual(sanitized, "SELECT * FROM users")
        print("  [OK] Whitespace normalized")
    
    def test_config_write_protection(self):
        """Test that write operations are always disabled"""
        print("Testing config write protection...")
        
        # Even if someone tries to enable writes, it should fail
        is_safe, reason = self.validator.is_safe_query("UPDATE users SET name = 'test'")
        self.assertFalse(is_safe)
        self.assertIn("forbidden operation", reason.lower())
        print("  [OK] Write operations permanently disabled")


if __name__ == '__main__':
    print("\n" + "="*50)
    print("SQL VALIDATOR TESTS")
    print("="*50 + "\n")
    
    # Run tests
    unittest.main(verbosity=0, exit=False)