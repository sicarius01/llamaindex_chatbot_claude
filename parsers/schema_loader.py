"""
Dynamic schema loader that parses markdown files to extract database schema information
No hardcoding - everything loaded from .md files
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from utils import config_loader, get_logger

logger = get_logger(__name__)


@dataclass
class Column:
    """Represents a database column"""
    name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Table:
    """Represents a database table"""
    name: str
    columns: List[Column]
    description: str = ""
    relationships: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.relationships is None:
            self.relationships = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'columns': [col.to_dict() for col in self.columns],
            'relationships': self.relationships
        }
    
    def get_column_names(self) -> List[str]:
        return [col.name for col in self.columns]
    
    def get_primary_keys(self) -> List[str]:
        return [col.name for col in self.columns if col.is_primary_key]
    
    def get_foreign_keys(self) -> List[str]:
        return [col.name for col in self.columns if col.is_foreign_key]


class SchemaLoader:
    """Loads database schema from markdown documentation files"""
    
    def __init__(self):
        self.config = config_loader.config
        self.data_config = self.config['data']
        self.schema_path = Path(self.data_config['schema_path'])
        self.file_extensions = self.data_config.get('file_extensions', ['.md'])
        self.tables: Dict[str, Table] = {}
        self.metadata: Dict[str, Any] = {}
        
        # Load schema on initialization
        self.reload_schema()
    
    def reload_schema(self):
        """Reload all schema information from files"""
        self.tables = {}
        self.metadata = {}
        
        if not self.schema_path.exists():
            logger.warning(f"Schema path does not exist: {self.schema_path}")
            return
        
        # Load all schema files
        for ext in self.file_extensions:
            for file_path in self.schema_path.glob(f"*{ext}"):
                try:
                    self._parse_schema_file(file_path)
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {str(e)}")
        
        logger.info(f"Loaded {len(self.tables)} tables from schema files")
    
    def _parse_schema_file(self, file_path: Path):
        """Parse a single schema markdown file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata from YAML front matter if present
        metadata = self._extract_metadata(content)
        if metadata:
            self.metadata.update(metadata)
        
        # Extract tables from content
        tables = self._extract_tables(content)
        
        for table in tables:
            self.tables[table.name.lower()] = table
            logger.debug(f"Loaded table: {table.name} with {len(table.columns)} columns")
    
    def _extract_metadata(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract YAML front matter metadata if present"""
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)
        
        if match:
            try:
                import yaml
                metadata_str = match.group(1)
                return yaml.safe_load(metadata_str)
            except:
                logger.warning("Failed to parse YAML front matter")
        
        return None
    
    def _extract_tables(self, content: str) -> List[Table]:
        """Extract table definitions from markdown content"""
        tables = []
        
        # Pattern to match table sections
        # Supports various heading formats: ## Table: name, ### name, # name table
        table_section_pattern = r'#{1,3}\s+(?:Table:?\s+)?(\w+)(?:\s+[Tt]able)?(?:\s*\n(.+?))?(?=\n#{1,3}\s|\Z)'
        
        matches = re.finditer(table_section_pattern, content, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            table_name = match.group(1)
            table_content = match.group(2) if match.group(2) else ""
            
            # Extract table description (first paragraph after heading)
            description = self._extract_description(table_content)
            
            # Extract columns from markdown table
            columns = self._extract_columns_from_table(table_content)
            
            # Extract relationships
            relationships = self._extract_relationships(table_content)
            
            if columns:
                table = Table(
                    name=table_name,
                    columns=columns,
                    description=description,
                    relationships=relationships
                )
                tables.append(table)
        
        return tables
    
    def _extract_description(self, content: str) -> str:
        """Extract description from the first paragraph"""
        lines = content.strip().split('\n')
        description_lines = []
        
        for line in lines:
            # Stop at the first table or heading
            if line.strip().startswith('|') or line.strip().startswith('#'):
                break
            if line.strip():
                description_lines.append(line.strip())
        
        return ' '.join(description_lines)
    
    def _extract_columns_from_table(self, content: str) -> List[Column]:
        """Extract column definitions from markdown table"""
        columns = []
        
        # Find markdown table
        table_pattern = r'\|(.+)\|'
        lines = content.split('\n')
        
        in_table = False
        header_found = False
        
        for line in lines:
            if '|' in line:
                if not in_table:
                    in_table = True
                    # This should be the header
                    if not header_found:
                        header_found = True
                        continue
                    # Skip separator line
                    if re.match(r'\|[\s\-:]+\|', line):
                        continue
                
                # Parse column row
                parts = [p.strip() for p in line.split('|') if p.strip()]
                
                if len(parts) >= 2:
                    column = self._parse_column_row(parts)
                    if column:
                        columns.append(column)
            elif in_table:
                # Table ended
                break
        
        return columns
    
    def _parse_column_row(self, parts: List[str]) -> Optional[Column]:
        """Parse a single column row from table"""
        if len(parts) < 2:
            return None
        
        name = parts[0].strip()
        data_type = parts[1].strip()
        
        # Parse additional properties
        nullable = True
        is_primary_key = False
        is_foreign_key = False
        description = ""
        
        # Check for NULL/NOT NULL
        if 'NOT NULL' in data_type.upper():
            nullable = False
            data_type = data_type.replace('NOT NULL', '').replace('not null', '').strip()
        
        # Check for keys in description or separate column
        if len(parts) > 2:
            key_info = parts[2].strip().upper() if len(parts) > 2 else ""
            if 'PK' in key_info or 'PRIMARY' in key_info:
                is_primary_key = True
            if 'FK' in key_info or 'FOREIGN' in key_info:
                is_foreign_key = True
            
            # Get description from last column
            if len(parts) > 3:
                description = parts[3].strip()
            elif len(parts) > 2 and not any(k in key_info for k in ['PK', 'FK', 'PRIMARY', 'FOREIGN']):
                description = parts[2].strip()
        
        return Column(
            name=name,
            data_type=data_type,
            nullable=nullable,
            is_primary_key=is_primary_key,
            is_foreign_key=is_foreign_key,
            description=description
        )
    
    def _extract_relationships(self, content: str) -> List[Dict[str, str]]:
        """Extract foreign key relationships from content"""
        relationships = []
        
        # Pattern to match relationship descriptions
        # e.g., "FK: department_id -> departments.department_id"
        fk_pattern = r'FK:\s*(\w+)\s*->\s*(\w+)\.(\w+)'
        
        for match in re.finditer(fk_pattern, content):
            relationships.append({
                'column': match.group(1),
                'references_table': match.group(2),
                'references_column': match.group(3)
            })
        
        return relationships
    
    def get_table(self, table_name: str) -> Optional[Table]:
        """Get a specific table by name"""
        return self.tables.get(table_name.lower())
    
    def get_all_tables(self) -> Dict[str, Table]:
        """Get all loaded tables"""
        return self.tables
    
    def get_table_names(self) -> List[str]:
        """Get list of all table names"""
        return list(self.tables.keys())
    
    def get_schema_summary(self) -> str:
        """Get a summary of the loaded schema"""
        summary = f"Database Schema Summary\n"
        summary += f"{'=' * 50}\n"
        summary += f"Total tables: {len(self.tables)}\n\n"
        
        for table_name, table in self.tables.items():
            summary += f"Table: {table.name}\n"
            if table.description:
                summary += f"  Description: {table.description}\n"
            summary += f"  Columns: {len(table.columns)}\n"
            
            # List primary keys
            pk_cols = table.get_primary_keys()
            if pk_cols:
                summary += f"  Primary Keys: {', '.join(pk_cols)}\n"
            
            # List foreign keys
            fk_cols = table.get_foreign_keys()
            if fk_cols:
                summary += f"  Foreign Keys: {', '.join(fk_cols)}\n"
            
            summary += "\n"
        
        return summary
    
    def export_schema_json(self, output_path: Optional[Path] = None) -> str:
        """Export schema as JSON"""
        schema_dict = {
            'metadata': self.metadata,
            'tables': {name: table.to_dict() for name, table in self.tables.items()}
        }
        
        json_str = json.dumps(schema_dict, indent=2, ensure_ascii=False)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"Schema exported to {output_path}")
        
        return json_str
    
    def validate_query_tables(self, query: str) -> tuple[bool, str]:
        """
        Validate that tables referenced in a query exist in the schema
        
        Returns:
            tuple: (is_valid, error_message)
        """
        # Extract table names from query
        table_pattern = r'\b(?:FROM|JOIN|INTO|UPDATE)\s+(\w+)'
        matches = re.findall(table_pattern, query, re.IGNORECASE)
        
        invalid_tables = []
        for table_name in matches:
            if table_name.lower() not in self.tables:
                invalid_tables.append(table_name)
        
        if invalid_tables:
            return False, f"Unknown tables: {', '.join(invalid_tables)}"
        
        return True, ""
    
    def get_context_for_llm(self) -> str:
        """Get schema context formatted for LLM understanding"""
        context = "Available Database Schema:\n\n"
        
        for table_name, table in self.tables.items():
            context += f"Table: {table.name}\n"
            if table.description:
                context += f"Description: {table.description}\n"
            
            context += "Columns:\n"
            for col in table.columns:
                col_desc = f"  - {col.name} ({col.data_type})"
                if col.is_primary_key:
                    col_desc += " [PK]"
                if col.is_foreign_key:
                    col_desc += " [FK]"
                if not col.nullable:
                    col_desc += " NOT NULL"
                if col.description:
                    col_desc += f" - {col.description}"
                context += col_desc + "\n"
            
            if table.relationships:
                context += "Relationships:\n"
                for rel in table.relationships:
                    context += f"  - {rel['column']} -> {rel['references_table']}.{rel['references_column']}\n"
            
            context += "\n"
        
        return context


# Global instance for easy access
_schema_loader = None

def get_schema_loader() -> SchemaLoader:
    """Get or create the global schema loader instance"""
    global _schema_loader
    if _schema_loader is None:
        _schema_loader = SchemaLoader()
    return _schema_loader

def reload_schema():
    """Reload the global schema"""
    loader = get_schema_loader()
    loader.reload_schema()