import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from llama_index.core import Document
from llama_index.core.node_parser import SimpleNodeParser
import sys
sys.path.append('..')
from utils import config_loader, get_logger


logger = get_logger(__name__)


class MarkdownSchemaParser:
    """Parse Markdown files containing database schema information"""
    
    def __init__(self):
        self.config = config_loader.get_section('data')
        self.schema_path = Path(self.config.get('schema_path', './data/schema_docs'))
        self.file_extensions = self.config.get('file_extensions', ['.md'])
    
    def parse_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a single markdown file and extract schema information
        
        Args:
            file_path: Path to the markdown file
        
        Returns:
            Dictionary containing parsed schema information
        """
        try:
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
            
        except Exception as e:
            logger.error(f"Failed to parse markdown file {file_path}: {str(e)}")
            raise
    
    def _extract_tables(self, content: str) -> List[Dict[str, Any]]:
        """Extract table definitions from markdown content"""
        tables = []
        
        # Pattern to match table definitions (flexible format)
        # Example patterns:
        # ## Table: users
        # ### users table
        # # users
        table_pattern = r'#{1,3}\s+(?:Table:?\s+)?(\w+)(?:\s+table)?'
        
        # Pattern to match column definitions in tables
        # Supports markdown table format
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
        # Look for description before the table definition
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
    
    def _extract_metadata(self, content: str) -> Dict[str, str]:
        """Extract metadata from markdown front matter or headers"""
        metadata = {}
        
        # Check for YAML front matter
        if content.startswith('---'):
            front_matter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if front_matter_match:
                front_matter = front_matter_match.group(1)
                for line in front_matter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
        
        # Extract main title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        # Extract database name if mentioned
        db_match = re.search(r'(?:Database|DB|Schema):\s*(\w+)', content, re.IGNORECASE)
        if db_match:
            metadata['database'] = db_match.group(1)
        
        return metadata
    
    def parse_all_documents(self) -> List[Document]:
        """
        Parse all markdown documents in the schema path
        
        Returns:
            List of LlamaIndex Document objects
        """
        documents = []
        
        if not self.schema_path.exists():
            logger.warning(f"Schema path does not exist: {self.schema_path}")
            return documents
        
        # Find all markdown files
        for ext in self.file_extensions:
            for file_path in self.schema_path.glob(f'*{ext}'):
                try:
                    logger.info(f"Parsing schema document: {file_path}")
                    parsed_data = self.parse_markdown_file(file_path)
                    
                    # Create document text with structured information
                    doc_text = self._create_document_text(parsed_data)
                    
                    # Create metadata for the document (ChromaDB only accepts str, int, float, None)
                    doc_metadata = {
                        'source': str(file_path),
                        'file_name': file_path.name,
                        'tables': ', '.join([t['name'] for t in parsed_data['tables']]),  # Convert list to string
                        **parsed_data['metadata']
                    }
                    
                    # Create LlamaIndex Document
                    document = Document(
                        text=doc_text,
                        metadata=doc_metadata
                    )
                    documents.append(document)
                    
                    logger.info(f"Successfully parsed {file_path.name} with {len(parsed_data['tables'])} tables")
                    
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {str(e)}")
                    continue
        
        logger.info(f"Total documents parsed: {len(documents)}")
        return documents
    
    def _create_document_text(self, parsed_data: Dict[str, Any]) -> str:
        """Create structured text from parsed data for indexing"""
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
    
    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema information for a specific table
        
        Args:
            table_name: Name of the table
        
        Returns:
            Dictionary containing table schema or None if not found
        """
        documents = self.parse_all_documents()
        
        for doc in documents:
            parsed_data = self.parse_markdown_file(Path(doc.metadata['source']))
            for table in parsed_data['tables']:
                if table['name'].lower() == table_name.lower():
                    return table
        
        return None


class SchemaIndexBuilder:
    """Build and manage the vector index for schema documents"""
    
    def __init__(self):
        self.parser = MarkdownSchemaParser()
        self.logger = get_logger(__name__)
    
    def build_index(self) -> Any:
        """
        Build vector index from schema documents
        
        Returns:
            VectorStoreIndex object
        """
        from llama_index.core import VectorStoreIndex, StorageContext
        from llama_index.vector_stores.chroma import ChromaVectorStore
        from llama_index.embeddings.ollama import OllamaEmbedding
        import chromadb
        
        try:
            # Parse all documents
            documents = self.parser.parse_all_documents()
            
            if not documents:
                self.logger.warning("No documents found to index")
                return None
            
            # Setup ChromaDB
            config = config_loader.get_section('vector_store')
            chroma_client = chromadb.PersistentClient(path=config['path'])
            
            # Get or create collection
            collection_name = config.get('collection_name', 'db_schema_docs')
            try:
                collection = chroma_client.get_collection(collection_name)
                self.logger.info(f"Using existing collection: {collection_name}")
            except:
                collection = chroma_client.create_collection(collection_name)
                self.logger.info(f"Created new collection: {collection_name}")
            
            # Setup vector store
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # Setup embedding model
            ollama_config = config_loader.get_section('ollama')
            embed_model = OllamaEmbedding(
                model_name=ollama_config.get('embedding_model', 'nomic-embed-text'),
                base_url=f"{ollama_config['host']}:{ollama_config['port']}"
            )
            
            # Create index
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                embed_model=embed_model,
                show_progress=True
            )
            
            self.logger.info(f"Successfully built index with {len(documents)} documents")
            return index
            
        except Exception as e:
            self.logger.error(f"Failed to build index: {str(e)}")
            raise
    
    def load_index(self) -> Any:
        """
        Load existing index from storage
        
        Returns:
            VectorStoreIndex object or None if not found
        """
        from llama_index.core import VectorStoreIndex
        from llama_index.vector_stores.chroma import ChromaVectorStore
        from llama_index.embeddings.ollama import OllamaEmbedding
        import chromadb
        
        try:
            config = config_loader.get_section('vector_store')
            chroma_client = chromadb.PersistentClient(path=config['path'])
            
            collection_name = config.get('collection_name', 'db_schema_docs')
            collection = chroma_client.get_collection(collection_name)
            
            vector_store = ChromaVectorStore(chroma_collection=collection)
            
            # Setup embedding model
            ollama_config = config_loader.get_section('ollama')
            embed_model = OllamaEmbedding(
                model_name=ollama_config.get('embedding_model', 'nomic-embed-text'),
                base_url=f"{ollama_config['host']}:{ollama_config['port']}"
            )
            
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                embed_model=embed_model
            )
            
            self.logger.info("Successfully loaded existing index")
            return index
            
        except Exception as e:
            self.logger.warning(f"Could not load existing index: {str(e)}")
            return None