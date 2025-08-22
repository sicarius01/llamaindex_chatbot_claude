import sys
import os
import unittest
import re
import sqlparse

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Minimal SQLValidator for testing without llama_index dependencies
class SQLValidator:
    """Validate SQL queries for safety"""
    
    # Dangerous keywords that modify data
    DANGEROUS_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
        'TRUNCATE', 'REPLACE', 'MERGE', 'CALL', 'EXEC', 'EXECUTE'
    ]
    
    @classmethod
    def is_safe_query(cls, query: str) -> tuple[bool, str]:
        """
        Check if a SQL query is safe (read-only)
        
        Args:
            query: SQL query string
        
        Returns:
            Tuple of (is_safe, reason)
        """
        # Always disable write operations
        # Parse and format the query
        formatted_query = sqlparse.format(query, strip_comments=True)
        upper_query = formatted_query.upper()
        
        # Check for dangerous keywords
        for keyword in cls.DANGEROUS_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', upper_query):
                return False, f"Query contains forbidden operation: {keyword}"
        
        # Check if query starts with SELECT or WITH
        parsed = sqlparse.parse(formatted_query)
        if not parsed:
            return False, "Unable to parse SQL query"
        
        first_statement = parsed[0]
        first_token = first_statement.token_first(skip_ws=True, skip_cm=True)
        
        if first_token and first_token.value.upper() not in ['SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN']:
            return False, f"Query must start with SELECT, WITH, SHOW, DESCRIBE, or EXPLAIN"
        
        return True, "Query is safe"
    
    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """
        Basic query sanitization
        
        Args:
            query: SQL query string
        
        Returns:
            Sanitized query string
        """
        # Remove comments
        query = sqlparse.format(query, strip_comments=True)
        
        # Remove excessive whitespace
        query = ' '.join(query.split())
        
        return query.strip()


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
            self.assertTrue(is_safe, f"Query should be safe: {query}\nReason: {reason}")
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
            self.assertTrue(is_safe, f"Query should be safe: {query}\nReason: {reason}")
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
        
        # Test queries with dangerous keywords that should be blocked
        injection_attempts = [
            ("SELECT * FROM users; DROP TABLE users", False),  # Contains DROP
            ("SELECT * FROM users WHERE id = 1 OR 1=1; DELETE FROM users", False),  # Contains DELETE
        ]
        
        for query, expected_safe in injection_attempts:
            is_safe, reason = self.validator.is_safe_query(query)
            self.assertEqual(is_safe, expected_safe, f"Query safety mismatch for: {query}")
            if not expected_safe:
                print(f"  [OK] Injection blocked: {query[:50]}...")
        
        # Test that comments are properly sanitized
        query_with_comment = "SELECT * FROM users -- ; DELETE FROM users"
        sanitized = self.validator.sanitize_query(query_with_comment)
        self.assertNotIn("DELETE", sanitized)
        print(f"  [OK] Comments sanitized: removed dangerous code after comment")
    
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


if __name__ == '__main__':
    print("\n" + "="*50)
    print("SQL VALIDATOR TESTS")
    print("="*50 + "\n")
    
    # Run tests
    unittest.main(verbosity=0, exit=False)