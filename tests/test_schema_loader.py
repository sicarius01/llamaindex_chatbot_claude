"""
Test cases for SchemaLoader - dynamic schema loading from markdown files
"""
import unittest
import tempfile
import json
from pathlib import Path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.schema_loader import SchemaLoader, Table, Column, get_schema_loader
from utils import config_loader


class TestSchemaLoader(unittest.TestCase):
    """Test schema loader functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Load config first
        config_loader.load_config('config.yaml')
        
        # Create temporary directory for test schema files
        self.temp_dir = tempfile.mkdtemp()
        self.schema_path = Path(self.temp_dir)
        
        # Create test schema markdown file
        self.create_test_schema_file()
        
        # Override config to use temp directory
        config_loader.update('data.schema_path', str(self.schema_path))
        
        # Create schema loader
        self.loader = SchemaLoader()
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_schema_file(self):
        """Create a test schema markdown file"""
        content = """---
database: test_db
version: 1.0
---

# Database Schema Documentation

## Table: users

This table stores user information for the application.

| Column Name | Data Type | Key | Description |
|------------|-----------|-----|-------------|
| user_id | INT NOT NULL | PK | Unique user identifier |
| username | VARCHAR(50) NOT NULL | | User's login name |
| email | VARCHAR(100) NOT NULL | | User's email address |
| department_id | INT | FK | Reference to departments table |
| created_at | TIMESTAMP | | Account creation timestamp |

FK: department_id -> departments.department_id

## departments

Department information table.

| Column Name | Data Type | Key | Description |
|------------|-----------|-----|-------------|
| department_id | INT NOT NULL | PK | Department identifier |
| name | VARCHAR(100) NOT NULL | | Department name |
| budget | DECIMAL(15,2) | | Annual budget |
| manager_id | INT | FK | Department manager |

FK: manager_id -> users.user_id

### projects

Project tracking table.

| Column Name | Data Type | Key | Description |
|------------|-----------|-----|-------------|
| project_id | INT NOT NULL | PK | Project identifier |
| name | VARCHAR(200) NOT NULL | | Project name |
| department_id | INT | FK | Owning department |
| status | VARCHAR(20) | | Current status |
| start_date | DATE | | Project start date |
| end_date | DATE | | Project end date |

FK: department_id -> departments.department_id
"""
        
        schema_file = self.schema_path / "test_schema.md"
        with open(schema_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_load_schema_from_markdown(self):
        """Test loading schema from markdown files"""
        # Check that tables were loaded
        self.assertGreater(len(self.loader.tables), 0)
        print(f"  [OK] Loaded {len(self.loader.tables)} tables from markdown")
        
        # Check specific tables exist
        self.assertIn('users', self.loader.tables)
        self.assertIn('departments', self.loader.tables)
        self.assertIn('projects', self.loader.tables)
        print(f"  [OK] All expected tables found")
    
    def test_table_structure(self):
        """Test that table structure is parsed correctly"""
        users_table = self.loader.get_table('users')
        self.assertIsNotNone(users_table)
        
        # Check table properties
        self.assertEqual(users_table.name, 'users')
        self.assertIn('user information', users_table.description.lower())
        print(f"  [OK] Table metadata parsed correctly")
        
        # Check columns
        self.assertEqual(len(users_table.columns), 5)
        column_names = users_table.get_column_names()
        self.assertIn('user_id', column_names)
        self.assertIn('email', column_names)
        self.assertIn('department_id', column_names)
        print(f"  [OK] All columns parsed: {column_names}")
    
    def test_column_properties(self):
        """Test that column properties are parsed correctly"""
        users_table = self.loader.get_table('users')
        
        # Find user_id column
        user_id_col = next(col for col in users_table.columns if col.name == 'user_id')
        self.assertTrue(user_id_col.is_primary_key)
        self.assertFalse(user_id_col.nullable)
        self.assertEqual(user_id_col.data_type, 'INT')
        print(f"  [OK] Primary key column properties correct")
        
        # Find department_id column
        dept_id_col = next(col for col in users_table.columns if col.name == 'department_id')
        self.assertTrue(dept_id_col.is_foreign_key)
        self.assertTrue(dept_id_col.nullable)
        print(f"  [OK] Foreign key column properties correct")
    
    def test_relationships(self):
        """Test that foreign key relationships are extracted"""
        users_table = self.loader.get_table('users')
        self.assertEqual(len(users_table.relationships), 1)
        
        rel = users_table.relationships[0]
        self.assertEqual(rel['column'], 'department_id')
        self.assertEqual(rel['references_table'], 'departments')
        self.assertEqual(rel['references_column'], 'department_id')
        print(f"  [OK] Foreign key relationships parsed correctly")
    
    def test_metadata_extraction(self):
        """Test that YAML front matter is extracted"""
        self.assertIn('database', self.loader.metadata)
        self.assertEqual(self.loader.metadata['database'], 'test_db')
        self.assertEqual(self.loader.metadata['version'], 1.0)
        print(f"  [OK] Metadata extracted from YAML front matter")
    
    def test_get_schema_summary(self):
        """Test schema summary generation"""
        summary = self.loader.get_schema_summary()
        self.assertIn('Total tables: 3', summary)
        self.assertIn('users', summary)
        self.assertIn('Primary Keys:', summary)
        print(f"  [OK] Schema summary generated")
    
    def test_export_schema_json(self):
        """Test exporting schema as JSON"""
        json_str = self.loader.export_schema_json()
        schema_dict = json.loads(json_str)
        
        self.assertIn('tables', schema_dict)
        self.assertIn('metadata', schema_dict)
        self.assertEqual(len(schema_dict['tables']), 3)
        print(f"  [OK] Schema exported to JSON successfully")
    
    def test_validate_query_tables(self):
        """Test query table validation"""
        # Valid query
        valid_query = "SELECT * FROM users JOIN departments ON users.department_id = departments.department_id"
        is_valid, error = self.loader.validate_query_tables(valid_query)
        self.assertTrue(is_valid)
        print(f"  [OK] Valid query tables recognized")
        
        # Invalid query with unknown table
        invalid_query = "SELECT * FROM unknown_table"
        is_valid, error = self.loader.validate_query_tables(invalid_query)
        self.assertFalse(is_valid)
        self.assertIn('unknown_table', error)
        print(f"  [OK] Invalid table detected: {error}")
    
    def test_get_context_for_llm(self):
        """Test LLM context generation"""
        context = self.loader.get_context_for_llm()
        
        # Check that context includes all tables
        self.assertIn('users', context)
        self.assertIn('departments', context)
        self.assertIn('projects', context)
        
        # Check that it includes column details
        self.assertIn('[PK]', context)
        self.assertIn('[FK]', context)
        self.assertIn('NOT NULL', context)
        
        print(f"  [OK] LLM context generated with all schema details")
    
    def test_no_hardcoded_schema(self):
        """Test that no schema is hardcoded"""
        # Create new loader with empty directory
        empty_dir = tempfile.mkdtemp()
        config_loader.update('data.schema_path', empty_dir)
        
        empty_loader = SchemaLoader()
        self.assertEqual(len(empty_loader.tables), 0)
        print(f"  [OK] No hardcoded schema - loader starts empty")
        
        # Clean up
        import shutil
        shutil.rmtree(empty_dir, ignore_errors=True)
    
    def test_reload_schema(self):
        """Test schema reloading"""
        initial_count = len(self.loader.tables)
        
        # Add a new table to the schema file
        new_content = """
## new_table

Test table added dynamically.

| Column Name | Data Type | Key | Description |
|------------|-----------|-----|-------------|
| id | INT | PK | Primary key |
| name | VARCHAR(50) | | Name field |
"""
        
        new_file = self.schema_path / "new_table.md"
        with open(new_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Reload schema
        self.loader.reload_schema()
        
        # Check that new table is loaded
        self.assertIn('new_table', self.loader.tables)
        self.assertGreater(len(self.loader.tables), initial_count)
        print(f"  [OK] Schema reloaded successfully with new table")
    
    def test_global_instance(self):
        """Test global schema loader instance"""
        loader1 = get_schema_loader()
        loader2 = get_schema_loader()
        
        # Should be the same instance
        self.assertIs(loader1, loader2)
        print(f"  [OK] Global schema loader singleton works")


class TestColumnParsing(unittest.TestCase):
    """Test various column definition formats"""
    
    def setUp(self):
        """Set up test environment"""
        config_loader.load_config('config.yaml')
        self.temp_dir = tempfile.mkdtemp()
        self.schema_path = Path(self.temp_dir)
        config_loader.update('data.schema_path', str(self.schema_path))
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_various_column_formats(self):
        """Test parsing different column definition formats"""
        content = """
## test_table

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| name | VARCHAR(255) | NOT NULL | |
| email | TEXT | UNIQUE NOT NULL | User email |
| age | INTEGER | CHECK (age > 0) | Must be positive |
| created_at | TIMESTAMP | DEFAULT NOW() | |
| is_active | BOOLEAN | DEFAULT TRUE | |
| data | JSONB | | Flexible data storage |
"""
        
        schema_file = self.schema_path / "test.md"
        with open(schema_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        loader = SchemaLoader()
        table = loader.get_table('test_table')
        
        self.assertIsNotNone(table)
        self.assertEqual(len(table.columns), 7)
        
        # Check specific column properties
        id_col = next(col for col in table.columns if col.name == 'id')
        self.assertIn('SERIAL', id_col.data_type)
        
        name_col = next(col for col in table.columns if col.name == 'name')
        self.assertFalse(name_col.nullable)
        
        print(f"  [OK] Various column formats parsed correctly")


def run_tests():
    """Run all schema loader tests"""
    print("\n" + "=" * 50)
    print(" SCHEMA LOADER TESTS")
    print("=" * 50 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSchemaLoader))
    suite.addTests(loader.loadTestsFromTestCase(TestColumnParsing))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "-" * 50)
    if result.wasSuccessful():
        print(f"[SUCCESS] All {result.testsRun} tests passed!")
    else:
        print(f"[FAILURE] {len(result.failures)} failures, {len(result.errors)} errors")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)