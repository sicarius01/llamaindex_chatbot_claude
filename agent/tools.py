import re
import sqlparse
from typing import List, Dict, Any, Optional, Tuple
from llama_index.core.tools import FunctionTool, ToolMetadata
from llama_index.core.tools.types import ToolOutput
import sys
sys.path.append('..')
from utils import config_loader, get_logger, query_logger
from parsers import SchemaIndexBuilder


logger = get_logger(__name__)


class SQLValidator:
    """Validate SQL queries for safety"""
    
    # Dangerous keywords that modify data
    DANGEROUS_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
        'TRUNCATE', 'REPLACE', 'MERGE', 'CALL', 'EXEC', 'EXECUTE'
    ]
    
    @classmethod
    def is_safe_query(cls, query: str) -> Tuple[bool, str]:
        """
        Check if a SQL query is safe (read-only)
        
        Args:
            query: SQL query string
        
        Returns:
            Tuple of (is_safe, reason)
        """
        # Check if write operations are allowed (should always be False per requirements)
        config = config_loader.get_section('sql')
        if config.get('allow_write', False):
            return False, "Write operations are disabled for security"
        
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


class RAGSearchTool:
    """Tool for RAG-based document search"""
    
    def __init__(self):
        self.index_builder = SchemaIndexBuilder()
        self.index = None
        self.config = config_loader.get_section('rag')
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize or load the vector index"""
        try:
            # Try to load existing index
            self.index = self.index_builder.load_index()
            
            # If no index exists, build one
            if self.index is None:
                logger.info("No existing index found, building new index...")
                self.index = self.index_builder.build_index()
        except Exception as e:
            logger.error(f"Failed to initialize RAG index: {str(e)}")
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using RAG
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of search results with metadata
        """
        if self.index is None:
            logger.error("RAG index not initialized")
            return []
        
        try:
            # Use configured top_k if not specified
            if top_k is None:
                top_k = self.config.get('top_k', 5)
            
            # Create query engine with Ollama
            from llama_index.core import Settings
            from llama_index.llms.ollama import Ollama
            
            # Set Ollama as LLM for query engine
            Settings.llm = Ollama(
                model=config_loader.get('ollama.model'),
                base_url=f"{config_loader.get('ollama.host')}:{config_loader.get('ollama.port')}"
            )
            
            query_engine = self.index.as_query_engine(
                similarity_top_k=top_k,
                response_mode="no_text"  # Return nodes only, not synthesized response
            )
            
            # Execute search
            response = query_engine.query(query)
            
            # Extract results
            results = []
            for node in response.source_nodes:
                results.append({
                    'text': node.text,
                    'score': node.score,
                    'metadata': node.metadata,
                    'source': node.metadata.get('source', 'Unknown')
                })
            
            # Log search operation
            query_logger.log_rag_search(query, results)
            
            return results
            
        except Exception as e:
            logger.error(f"RAG search failed: {str(e)}")
            query_logger.log_tool_call('rag_search', {'query': query}, error=e)
            return []
    
    def get_schema_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema information for a specific table
        
        Args:
            table_name: Name of the table
        
        Returns:
            Schema information or None
        """
        query = f"table schema columns {table_name}"
        results = self.search(query, top_k=3)
        
        # Look for exact table match in results
        for result in results:
            if table_name.lower() in result['text'].lower():
                return {
                    'table_name': table_name,
                    'schema_text': result['text'],
                    'source': result['source']
                }
        
        return None
    
    def rebuild_index(self):
        """Rebuild the vector index from scratch"""
        try:
            logger.info("Rebuilding RAG index...")
            self.index = self.index_builder.build_index()
            logger.info("RAG index rebuilt successfully")
        except Exception as e:
            logger.error(f"Failed to rebuild index: {str(e)}")


class SQLQueryTool:
    """Tool for executing safe SQL queries"""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize SQL query tool
        
        Args:
            connection_string: Database connection string (if None, uses config)
        """
        config = config_loader.get_section('sql')
        self.connection_string = connection_string or config.get('connection_string', '')
        self.max_results = config.get('max_results', 100)
        self.validator = SQLValidator()
        
        # Note: Actual database connection would be implemented here
        # For now, this is a placeholder that would need proper DB adapter
        self.connection = None
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a SQL query if it's safe
        
        Args:
            query: SQL query to execute
        
        Returns:
            Dictionary with results or error information
        """
        try:
            # Validate query safety
            is_safe, reason = self.validator.is_safe_query(query)
            if not is_safe:
                error_msg = f"Query rejected: {reason}"
                logger.warning(error_msg)
                query_logger.log_sql_query(query, error=Exception(error_msg))
                return {
                    'success': False,
                    'error': error_msg,
                    'query': query
                }
            
            # Sanitize query
            sanitized_query = self.validator.sanitize_query(query)
            
            # Add LIMIT if not present (for safety)
            if 'LIMIT' not in sanitized_query.upper():
                sanitized_query = f"{sanitized_query} LIMIT {self.max_results}"
            
            # Log the query attempt
            logger.info(f"Executing SQL query: {sanitized_query[:100]}...")
            
            # Execute query (placeholder - actual implementation would use real DB connection)
            # This is where you would connect to your actual database
            results = self._execute_database_query(sanitized_query)
            
            # Log successful execution
            query_logger.log_sql_query(sanitized_query, result=results)
            
            return {
                'success': True,
                'data': results,
                'query': sanitized_query,
                'row_count': len(results) if isinstance(results, list) else 0
            }
            
        except Exception as e:
            error_msg = f"Query execution failed: {str(e)}"
            logger.error(error_msg)
            query_logger.log_sql_query(query, error=e)
            return {
                'success': False,
                'error': error_msg,
                'query': query
            }
    
    def _execute_database_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Placeholder for actual database query execution
        
        Args:
            query: SQL query to execute
        
        Returns:
            Query results as list of dictionaries
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Connect to the database using self.connection_string
        # 2. Execute the query
        # 3. Fetch and return results
        
        logger.warning("Database connection not configured. Returning mock data.")
        return [
            {"message": "Database connection not configured"},
            {"note": "Please configure SQL connection_string in config.yaml"}
        ]
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            # Placeholder for connection test
            # Would actually test the database connection here
            if not self.connection_string:
                logger.warning("No database connection string configured")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False


def create_rag_search_function() -> FunctionTool:
    """Create a LlamaIndex FunctionTool for RAG search"""
    rag_tool = RAGSearchTool()
    
    def rag_search_wrapper(query: str, top_k: int = 5) -> str:
        """
        Search documentation using RAG
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            Formatted search results
        """
        results = rag_tool.search(query, top_k)
        
        if not results:
            return "No relevant documents found."
        
        # Format results for LLM consumption
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"Result {i} (Score: {result.get('score', 'N/A')}):\n"
                f"Source: {result.get('source', 'Unknown')}\n"
                f"Content: {result['text'][:500]}..."
            )
        
        return "\n\n".join(formatted_results)
    
    return FunctionTool.from_defaults(
        fn=rag_search_wrapper,
        name="rag_search",
        description="Search through database schema documentation using semantic search"
    )


def create_sql_query_function() -> FunctionTool:
    """Create a LlamaIndex FunctionTool for SQL queries"""
    sql_tool = SQLQueryTool()
    
    def sql_query_wrapper(query: str) -> str:
        """
        Execute a read-only SQL query
        
        Args:
            query: SQL SELECT query to execute
        
        Returns:
            Query results or error message
        """
        result = sql_tool.execute_query(query)
        
        if not result['success']:
            return f"Query failed: {result['error']}"
        
        # Format results for LLM consumption
        data = result.get('data', [])
        if not data:
            return "Query executed successfully but returned no results."
        
        # Convert results to readable format
        if isinstance(data, list) and len(data) > 0:
            # Assuming data is list of dicts
            import json
            return f"Query returned {len(data)} rows:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        
        return str(data)
    
    return FunctionTool.from_defaults(
        fn=sql_query_wrapper,
        name="sql_query",
        description="Execute a read-only SQL query (SELECT, SHOW, DESCRIBE only). Write operations are not allowed."
    )


def get_all_tools() -> List[FunctionTool]:
    """Get all available tools for the agent"""
    return [
        create_rag_search_function(),
        create_sql_query_function()
    ]