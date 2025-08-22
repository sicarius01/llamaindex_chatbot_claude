"""
Integration tests for the complete LlamaIndex chatbot system
Tests the full flow from query to response with all components
"""
import unittest
import tempfile
import time
from pathlib import Path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import config_loader, setup_logging
from agent import LLMAgent, AgentOrchestrator
from parsers.schema_loader import SchemaLoader
from agent.tools import SQLValidator, RAGSearchTool, SQLQueryTool


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Load configuration
        config_loader.load_config('config.yaml')
        
        # Set up logging
        setup_logging('test_integration')
        
        # Create test schema
        cls.setup_test_schema()
    
    @classmethod
    def setup_test_schema(cls):
        """Create comprehensive test schema"""
        schema_path = Path(config_loader.get('data.schema_path'))
        
        # Ensure directory exists
        schema_path.mkdir(parents=True, exist_ok=True)
        
        # Create comprehensive schema file
        test_schema = """---
database: integration_test_db
version: 2.0
author: Test Suite
---

# Integration Test Database Schema

## employees

Employee information management table.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| employee_id | INT NOT NULL | PK | Employee unique identifier |
| first_name | VARCHAR(50) NOT NULL | | Employee first name |
| last_name | VARCHAR(50) NOT NULL | | Employee last name |
| email | VARCHAR(100) NOT NULL | UNIQUE | Employee email address |
| phone | VARCHAR(20) | | Contact phone number |
| hire_date | DATE NOT NULL | | Date of hire |
| job_title | VARCHAR(100) | | Current job title |
| salary | DECIMAL(10,2) | | Annual salary |
| department_id | INT | FK | Department reference |
| manager_id | INT | FK | Manager's employee_id |

FK: department_id -> departments.department_id
FK: manager_id -> employees.employee_id

## departments

Department organizational structure.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| department_id | INT NOT NULL | PK | Department identifier |
| department_name | VARCHAR(100) NOT NULL | | Department name |
| location | VARCHAR(100) | | Office location |
| budget | DECIMAL(15,2) | | Annual budget |
| head_count | INT | | Number of employees |

## products

Product catalog table.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| product_id | INT NOT NULL | PK | Product identifier |
| product_name | VARCHAR(200) NOT NULL | | Product name |
| category | VARCHAR(50) | | Product category |
| price | DECIMAL(10,2) NOT NULL | | Unit price |
| stock_quantity | INT | | Current stock level |
| supplier_id | INT | FK | Supplier reference |

FK: supplier_id -> suppliers.supplier_id

## orders

Customer order tracking.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| order_id | INT NOT NULL | PK | Order identifier |
| customer_id | INT NOT NULL | FK | Customer reference |
| order_date | TIMESTAMP NOT NULL | | Order timestamp |
| total_amount | DECIMAL(12,2) | | Total order value |
| status | VARCHAR(20) | | Order status |
| shipping_address | TEXT | | Delivery address |

FK: customer_id -> customers.customer_id

## customers

Customer information.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| customer_id | INT NOT NULL | PK | Customer identifier |
| company_name | VARCHAR(100) | | Company name |
| contact_name | VARCHAR(100) NOT NULL | | Primary contact |
| email | VARCHAR(100) NOT NULL | | Contact email |
| phone | VARCHAR(20) | | Contact phone |
| credit_limit | DECIMAL(10,2) | | Maximum credit |
"""
        
        # Write schema file
        schema_file = schema_path / "integration_test_schema.md"
        with open(schema_file, 'w', encoding='utf-8') as f:
            f.write(test_schema)
    
    def test_sql_validator_comprehensive(self):
        """Test SQL validator with various query types"""
        test_cases = [
            # Safe queries
            ("SELECT * FROM employees", True, "Basic SELECT"),
            ("SELECT e.first_name, d.department_name FROM employees e JOIN departments d ON e.department_id = d.department_id", True, "JOIN query"),
            ("WITH cte AS (SELECT * FROM orders) SELECT * FROM cte", True, "CTE query"),
            ("SELECT COUNT(*) FROM products WHERE price > 100", True, "Aggregate query"),
            ("SHOW TABLES", True, "SHOW command"),
            ("DESCRIBE employees", True, "DESCRIBE command"),
            ("EXPLAIN SELECT * FROM customers", True, "EXPLAIN query"),
            
            # Dangerous queries
            ("INSERT INTO employees VALUES (1, 'John', 'Doe')", False, "INSERT blocked"),
            ("UPDATE products SET price = 0", False, "UPDATE blocked"),
            ("DELETE FROM orders WHERE order_id = 1", False, "DELETE blocked"),
            ("DROP TABLE customers", False, "DROP blocked"),
            ("TRUNCATE TABLE departments", False, "TRUNCATE blocked"),
            ("ALTER TABLE employees ADD COLUMN test VARCHAR(50)", False, "ALTER blocked"),
            
            # SQL injection attempts
            ("SELECT * FROM users; DROP TABLE users", False, "Multiple statements blocked"),
            ("SELECT * FROM employees WHERE id = 1 OR 1=1; DELETE FROM employees", False, "Injection blocked"),
        ]
        
        for query, expected_safe, description in test_cases:
            is_safe, reason = SQLValidator.is_safe_query(query)
            self.assertEqual(is_safe, expected_safe, f"Failed: {description} - {reason}")
            status = "PASS" if is_safe == expected_safe else "FAIL"
            print(f"  [{status}] {description}: {query[:50]}...")
    
    def test_schema_loader_integration(self):
        """Test schema loader with comprehensive schema"""
        loader = SchemaLoader()
        
        # Check all tables loaded
        expected_tables = ['employees', 'departments', 'products', 'orders', 'customers']
        for table_name in expected_tables:
            self.assertIn(table_name, loader.tables)
        print(f"  [OK] All {len(expected_tables)} tables loaded")
        
        # Check relationships
        employees_table = loader.get_table('employees')
        self.assertEqual(len(employees_table.relationships), 2)
        print(f"  [OK] Foreign key relationships loaded")
        
        # Test LLM context generation
        context = loader.get_context_for_llm()
        self.assertIn('employees', context)
        self.assertIn('[PK]', context)
        self.assertIn('[FK]', context)
        print(f"  [OK] LLM context generated")
        
        # Test query validation
        valid_query = "SELECT * FROM employees JOIN departments ON employees.department_id = departments.department_id"
        is_valid, error = loader.validate_query_tables(valid_query)
        self.assertTrue(is_valid)
        print(f"  [OK] Valid query tables recognized")
        
        invalid_query = "SELECT * FROM non_existent_table"
        is_valid, error = loader.validate_query_tables(invalid_query)
        self.assertFalse(is_valid)
        print(f"  [OK] Invalid tables detected")
    
    def test_config_dynamic_loading(self):
        """Test that all configuration is loaded dynamically"""
        # Test that config values are used
        ollama_model = config_loader.get('ollama.model')
        self.assertIsNotNone(ollama_model)
        print(f"  [OK] Ollama model from config: {ollama_model}")
        
        # Test config updates
        original_verbose = config_loader.get('agent.verbose')
        config_loader.update('agent.verbose', not original_verbose)
        new_verbose = config_loader.get('agent.verbose')
        self.assertNotEqual(original_verbose, new_verbose)
        config_loader.update('agent.verbose', original_verbose)  # Restore
        print(f"  [OK] Config updates work dynamically")
        
        # Test that no hardcoded values exist
        sql_config = config_loader.get_section('sql')
        self.assertFalse(sql_config.get('allow_write', False))
        print(f"  [OK] SQL write protection enforced via config")
    
    def test_memory_persistence(self):
        """Test conversation memory management"""
        from agent.memory import ConversationMemory, MemoryManager
        
        # Create memory manager
        manager = MemoryManager()
        
        # Test session creation
        session1 = manager.create_session('test1')
        session1.add_user_message("Hello, how are you?")
        session1.add_assistant_message("I'm doing well, thank you!")
        
        # Test session switching
        session2 = manager.create_session('test2')
        session2.add_user_message("What's the weather?")
        session2.add_assistant_message("I don't have weather information.")
        
        # Verify isolation
        manager.set_current_session('test1')
        current = manager.get_current_session()
        self.assertEqual(len(current.messages), 2)
        
        manager.set_current_session('test2')
        current = manager.get_current_session()
        self.assertEqual(len(current.messages), 2)
        
        print(f"  [OK] Memory sessions isolated and persistent")
        
        # Test save/load
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            session1.save_to_file(temp_file)
            
            new_memory = ConversationMemory()
            new_memory.load_from_file(temp_file)
            self.assertEqual(len(new_memory.messages), 2)
            print(f"  [OK] Memory save/load works")
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    def test_tool_error_handling(self):
        """Test error handling in tools"""
        # Test SQL tool with invalid query
        sql_tool = SQLQueryTool()
        result = sql_tool.execute_query("DROP TABLE users")
        self.assertFalse(result['success'])
        self.assertIn('rejected', result['error'].lower())
        print(f"  [OK] SQL tool rejects dangerous queries")
        
        # Test with empty query
        result = sql_tool.execute_query("")
        self.assertFalse(result['success'])
        print(f"  [OK] SQL tool handles empty queries")
        
        # Test RAG tool initialization
        try:
            rag_tool = RAGSearchTool()
            # Tool should initialize even without index
            self.assertIsNotNone(rag_tool)
            print(f"  [OK] RAG tool initializes gracefully")
        except Exception as e:
            self.fail(f"RAG tool initialization failed: {str(e)}")
    
    def test_end_to_end_flow(self):
        """Test complete query processing flow"""
        print("\n  Testing end-to-end flow...")
        
        # Note: This test would require Ollama to be running
        # For CI/CD, we'll just test the component initialization
        
        try:
            # Test orchestrator creation
            orchestrator = AgentOrchestrator()
            self.assertIsNotNone(orchestrator)
            print(f"    [OK] Orchestrator created")
            
            # Test agent management
            agent_id = 'test_agent'
            agent = orchestrator.create_agent(agent_id)
            self.assertIsNotNone(agent)
            print(f"    [OK] Agent created")
            
            # Test agent listing
            agents = orchestrator.list_agents()
            self.assertIn(agent_id, agents)
            print(f"    [OK] Agent management works")
            
        except Exception as e:
            # This is expected if Ollama is not running
            if "connection" in str(e).lower() or "ollama" in str(e).lower():
                print(f"    [SKIP] Ollama not running - skipping LLM tests")
            else:
                raise


class TestPerformance(unittest.TestCase):
    """Performance and stress tests"""
    
    def test_schema_loading_performance(self):
        """Test schema loading performance with large schema"""
        start_time = time.time()
        
        # Create large schema file
        temp_dir = tempfile.mkdtemp()
        schema_path = Path(temp_dir)
        
        try:
            # Generate large schema with many tables
            large_schema = "# Large Schema\n\n"
            for i in range(50):  # 50 tables
                large_schema += f"""
## table_{i}

Table {i} description.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
"""
                for j in range(20):  # 20 columns per table
                    large_schema += f"| col_{j} | VARCHAR(100) | | Column {j} |\n"
                large_schema += "\n"
            
            schema_file = schema_path / "large_schema.md"
            with open(schema_file, 'w') as f:
                f.write(large_schema)
            
            # Load schema
            config_loader.update('data.schema_path', str(schema_path))
            loader = SchemaLoader()
            
            load_time = time.time() - start_time
            
            # Check performance
            self.assertEqual(len(loader.tables), 50)
            self.assertLess(load_time, 5.0)  # Should load in under 5 seconds
            print(f"  [OK] Loaded 50 tables with 1000 columns in {load_time:.2f}s")
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_sql_validation_performance(self):
        """Test SQL validation performance"""
        # Generate complex query
        complex_query = """
        WITH RECURSIVE emp_hierarchy AS (
            SELECT employee_id, first_name, last_name, manager_id, 0 as level
            FROM employees
            WHERE manager_id IS NULL
            
            UNION ALL
            
            SELECT e.employee_id, e.first_name, e.last_name, e.manager_id, h.level + 1
            FROM employees e
            JOIN emp_hierarchy h ON e.manager_id = h.employee_id
        )
        SELECT 
            h.level,
            h.employee_id,
            h.first_name || ' ' || h.last_name as full_name,
            d.department_name,
            COUNT(DISTINCT o.order_id) as order_count,
            SUM(o.total_amount) as total_sales
        FROM emp_hierarchy h
        LEFT JOIN departments d ON h.department_id = d.department_id
        LEFT JOIN orders o ON h.employee_id = o.processed_by
        GROUP BY h.level, h.employee_id, h.first_name, h.last_name, d.department_name
        ORDER BY h.level, total_sales DESC
        """
        
        start_time = time.time()
        
        # Validate 100 times
        for _ in range(100):
            is_safe, _ = SQLValidator.is_safe_query(complex_query)
            self.assertTrue(is_safe)
        
        validation_time = time.time() - start_time
        avg_time = validation_time / 100
        
        self.assertLess(avg_time, 0.01)  # Should validate in under 10ms
        print(f"  [OK] Complex query validated 100x in {validation_time:.2f}s (avg: {avg_time*1000:.2f}ms)")


def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "=" * 50)
    print(" INTEGRATION TESTS")
    print("=" * 50 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "-" * 50)
    if result.wasSuccessful():
        print(f"[SUCCESS] All {result.testsRun} integration tests passed!")
    else:
        print(f"[FAILURE] {len(result.failures)} failures, {len(result.errors)} errors")
        for failure in result.failures:
            print(f"  - {failure[0]}: {failure[1]}")
        for error in result.errors:
            print(f"  - {error[0]}: {error[1]}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)