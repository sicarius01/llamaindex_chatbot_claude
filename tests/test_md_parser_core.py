import sys
import os
import unittest
import tempfile
import re
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


# Minimal MarkdownSchemaParser for testing without llama_index
class MarkdownSchemaParser:
    """Parse Markdown files containing database schema information"""
    
    def __init__(self):
        self.schema_path = Path('./data/schema_docs')
        self.file_extensions = ['.md']
    
    def _extract_tables(self, content: str) -> list[dict]:
        """Extract table definitions from markdown content"""
        tables = []
        
        # Pattern to match table definitions
        table_pattern = r'#{1,3}\s+(?:Table:?\s+)?(\w+)(?:\s+table)?'
        
        # Pattern to match column definitions in tables
        column_pattern = r'\|\s*(\w+)\s*\|\s*(\w+[^\|]*)\s*\|\s*([^\|]*)\s*\|'
        
        sections = re.split(table_pattern, content)
        
        for i in range(1, len(sections), 2):
            if i < len(sections):
                table_name = sections[i].strip()
                table_content = sections[i + 1] if i + 1 < len(sections) else ""
                
                # Extract columns
                columns = []
                for match in re.finditer(column_pattern, table_content):
                    column_name = match.group(1).strip()
                    column_type = match.group(2).strip()
                    column_desc = match.group(3).strip() if match.group(3) else ""
                    
                    # Skip header rows
                    if column_name.lower() in ['column', 'name', 'field']:
                        continue
                    if '---' in column_name or '---' in column_type:
                        continue
                    
                    columns.append({
                        'name': column_name,
                        'type': column_type,
                        'description': column_desc
                    })
                
                if columns:
                    tables.append({
                        'name': table_name,
                        'columns': columns,
                        'description': self._extract_table_description(table_content)
                    })
        
        return tables
    
    def _extract_table_description(self, content: str) -> str:
        """Extract table description from content"""
        lines = content.split('\n')
        description_lines = []
        
        for line in lines:
            # Stop when we hit the table
            if '|' in line:
                break
            # Skip empty lines and headers
            if line.strip() and not line.startswith('#'):
                description_lines.append(line.strip())
        
        return ' '.join(description_lines)
    
    def _extract_metadata(self, content: str) -> dict[str, str]:
        """Extract metadata from markdown"""
        metadata = {}
        
        # Extract main title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        # Extract database name if mentioned
        db_match = re.search(r'(?:Database|DB|Schema):\s*(\w+)', content, re.IGNORECASE)
        if db_match:
            metadata['database'] = db_match.group(1)
        
        return metadata
    
    def parse_markdown_file(self, file_path: Path) -> dict:
        """Parse a single markdown file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract table information
        tables = self._extract_tables(content)
        
        # Extract general metadata
        metadata = self._extract_metadata(content)
        
        return {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'tables': tables,
            'metadata': metadata,
            'raw_content': content
        }
    
    def _create_document_text(self, parsed_data: dict) -> str:
        """Create structured text from parsed data"""
        lines = []
        
        # Add title if available
        if 'title' in parsed_data['metadata']:
            lines.append(f"# {parsed_data['metadata']['title']}")
            lines.append("")
        
        # Add database info if available
        if 'database' in parsed_data['metadata']:
            lines.append(f"Database: {parsed_data['metadata']['database']}")
            lines.append("")
        
        # Add table information
        for table in parsed_data['tables']:
            lines.append(f"## Table: {table['name']}")
            
            if table['description']:
                lines.append(f"Description: {table['description']}")
            
            lines.append("\nColumns:")
            for column in table['columns']:
                col_text = f"- {column['name']} ({column['type']})"
                if column['description']:
                    col_text += f": {column['description']}"
                lines.append(col_text)
            
            lines.append("")
        
        # Add original content as reference
        lines.append("\n--- Original Content ---")
        lines.append(parsed_data['raw_content'])
        
        return '\n'.join(lines)


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
    
    def test_sample_schema_file(self):
        """Test parsing the actual sample schema file"""
        print("Testing sample schema file...")
        
        sample_file = Path("data/schema_docs/sample_schema.md")
        
        if sample_file.exists():
            result = self.parser.parse_markdown_file(sample_file)
            
            # Check that we found tables
            self.assertGreater(len(result['tables']), 0)
            print(f"  [OK] Found {len(result['tables'])} tables in sample file")
            
            # List table names
            table_names = [t['name'] for t in result['tables']]
            print(f"  [OK] Tables found: {', '.join(table_names)}")
        else:
            print("  [SKIP] Sample schema file not found")


if __name__ == '__main__':
    print("\n" + "="*50)
    print("MARKDOWN PARSER TESTS")
    print("="*50 + "\n")
    
    # Run tests
    unittest.main(verbosity=0, exit=False)