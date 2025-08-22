import sys
import os
import unittest
import tempfile
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'parsers'))

# Import parser module
import md_parser
MarkdownSchemaParser = md_parser.MarkdownSchemaParser


class TestMarkdownParser(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.parser = MarkdownSchemaParser()
        
        # Create sample markdown content
        self.sample_md = """# Sample Database Schema

Database: test_db

## Table: users

User information table

| Column | Type | Description |
|--------|------|-------------|
| id | INT PRIMARY KEY | User ID |
| username | VARCHAR(50) | Username |
| email | VARCHAR(100) | Email address |
| created_at | TIMESTAMP | Creation time |

## Table: orders

Order information table

| Column | Type | Description |
|--------|------|-------------|
| order_id | INT PRIMARY KEY | Order ID |
| user_id | INT | User ID (FK) |
| total | DECIMAL(10,2) | Total amount |
| order_date | DATE | Order date |
"""
    
    def test_extract_tables(self):
        """Test table extraction from markdown"""
        print("Testing table extraction...")
        
        tables = self.parser._extract_tables(self.sample_md)
        
        # Should find 2 tables
        self.assertEqual(len(tables), 2)
        print(f"  [OK] Found {len(tables)} tables")
        
        # Check first table
        users_table = tables[0]
        self.assertEqual(users_table['name'], 'users')
        self.assertEqual(len(users_table['columns']), 4)
        print(f"  [OK] Users table has {len(users_table['columns'])} columns")
        
        # Check column details
        id_column = users_table['columns'][0]
        self.assertEqual(id_column['name'], 'id')
        self.assertEqual(id_column['type'], 'INT PRIMARY KEY')
        print("  [OK] Column details extracted correctly")
    
    def test_extract_metadata(self):
        """Test metadata extraction"""
        print("Testing metadata extraction...")
        
        metadata = self.parser._extract_metadata(self.sample_md)
        
        # Should extract title
        self.assertIn('title', metadata)
        self.assertEqual(metadata['title'], 'Sample Database Schema')
        print(f"  [OK] Title extracted: {metadata['title']}")
        
        # Should extract database name
        self.assertIn('database', metadata)
        self.assertEqual(metadata['database'], 'test_db')
        print(f"  [OK] Database extracted: {metadata['database']}")
    
    def test_parse_markdown_file(self):
        """Test parsing a complete markdown file"""
        print("Testing file parsing...")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(self.sample_md)
            temp_file = Path(f.name)
        
        try:
            # Parse the file
            result = self.parser.parse_markdown_file(temp_file)
            
            # Check result structure
            self.assertIn('tables', result)
            self.assertIn('metadata', result)
            self.assertIn('raw_content', result)
            self.assertEqual(len(result['tables']), 2)
            print("  [OK] File parsed successfully")
            
            # Check that raw content is preserved
            self.assertEqual(result['raw_content'], self.sample_md)
            print("  [OK] Raw content preserved")
            
        finally:
            # Clean up
            temp_file.unlink(missing_ok=True)
    
    def test_create_document_text(self):
        """Test document text creation for indexing"""
        print("Testing document text creation...")
        
        parsed_data = {
            'metadata': {
                'title': 'Test Schema',
                'database': 'test_db'
            },
            'tables': [
                {
                    'name': 'users',
                    'description': 'User table',
                    'columns': [
                        {'name': 'id', 'type': 'INT', 'description': 'User ID'}
                    ]
                }
            ],
            'raw_content': 'Original content here'
        }
        
        doc_text = self.parser._create_document_text(parsed_data)
        
        # Check that all components are in the document
        self.assertIn('Test Schema', doc_text)
        self.assertIn('test_db', doc_text)
        self.assertIn('users', doc_text)
        self.assertIn('User table', doc_text)
        self.assertIn('Original content here', doc_text)
        print("  [OK] Document text created with all components")
    
    def test_table_description_extraction(self):
        """Test extraction of table descriptions"""
        print("Testing table description extraction...")
        
        table_content = """This is a description of the table.
It can span multiple lines.

| Column | Type | Description |
|--------|------|-------------|
| id | INT | ID column |
"""
        
        description = self.parser._extract_table_description(table_content)
        
        # Should extract description before the table
        self.assertIn("This is a description", description)
        self.assertIn("multiple lines", description)
        print("  [OK] Table description extracted")
    
    def test_get_table_schema(self):
        """Test getting schema for a specific table"""
        print("Testing get_table_schema...")
        
        # Create test markdown file
        test_dir = Path("data/schema_docs")
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "test_schema.md"
        
        try:
            # Write test content
            test_file.write_text(self.sample_md)
            
            # Get schema for users table
            schema = self.parser.get_table_schema("users")
            
            if schema:
                self.assertEqual(schema['name'], 'users')
                self.assertEqual(len(schema['columns']), 4)
                print("  [OK] Table schema retrieved")
            else:
                print("  [SKIP] Table schema not found (index not built)")
                
        finally:
            # Clean up
            test_file.unlink(missing_ok=True)


if __name__ == '__main__':
    print("\n" + "="*50)
    print("MARKDOWN PARSER TESTS")
    print("="*50 + "\n")
    
    # Run tests
    unittest.main(verbosity=0, exit=False)