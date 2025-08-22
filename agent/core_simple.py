from typing import List, Dict, Any, Optional
from llama_index.core import Settings, VectorStoreIndex
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
import sys
sys.path.append('..')
from utils import config_loader, get_logger, query_logger
from .memory import ConversationMemory, MemoryManager
from .tools import SQLQueryTool, RAGSearchTool


logger = get_logger(__name__)


class LLMAgent:
    """Simplified LLM Agent that uses direct LLM calls with RAG"""
    
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """
        Initialize the LLM Agent
        
        Args:
            memory_manager: Optional memory manager instance
        """
        self.config = config_loader.config
        self.ollama_config = self.config['ollama']
        self.agent_config = self.config['agent']
        
        # Initialize memory
        self.memory_manager = memory_manager or MemoryManager()
        
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Initialize embedding model
        self.embed_model = self._initialize_embeddings()
        
        # Set global settings for LlamaIndex
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        
        # Initialize tools
        self.rag_tool = RAGSearchTool()
        self.sql_tool = SQLQueryTool()
        
        # Initialize query engine
        self.query_engine = None
        self._initialize_query_engine()
        
        logger.info("LLM Agent initialized successfully")
    
    def _initialize_llm(self) -> Ollama:
        """Initialize Ollama LLM"""
        try:
            llm = Ollama(
                model=self.ollama_config['model'],
                base_url=f"{self.ollama_config['host']}:{self.ollama_config['port']}",
                temperature=self.ollama_config.get('temperature', 0.7),
                request_timeout=120.0,
                additional_kwargs={
                    "num_predict": self.ollama_config.get('max_tokens', 2048)
                }
            )
            
            logger.info(f"Initialized Ollama LLM with model: {self.ollama_config['model']}")
            return llm
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM: {str(e)}")
            raise
    
    def _initialize_embeddings(self) -> OllamaEmbedding:
        """Initialize Ollama embedding model"""
        try:
            embed_model = OllamaEmbedding(
                model_name=self.ollama_config.get('embedding_model', 'nomic-embed-text'),
                base_url=f"{self.ollama_config['host']}:{self.ollama_config['port']}"
            )
            
            logger.info(f"Initialized Ollama embeddings with model: {self.ollama_config.get('embedding_model')}")
            return embed_model
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama embeddings: {str(e)}")
            raise
    
    def _initialize_query_engine(self):
        """Initialize query engine for RAG"""
        try:
            # Try to load or build index
            from parsers import SchemaIndexBuilder
            builder = SchemaIndexBuilder()
            index = builder.load_index()
            
            if index is None:
                logger.warning("No existing index found, building new one...")
                index = builder.build_index()
            
            if index:
                # Create query engine from index
                self.query_engine = index.as_query_engine(
                    llm=self.llm,
                    similarity_top_k=5,
                    response_mode="compact"
                )
                logger.info("Initialized query engine")
            else:
                logger.warning("Could not initialize query engine")
                
        except Exception as e:
            logger.error(f"Failed to initialize query engine: {str(e)}")
    
    def chat(self, user_input: str) -> str:
        """
        Process user input and generate response
        
        Args:
            user_input: User's message
        
        Returns:
            Agent's response
        """
        try:
            # Add user message to memory
            memory = self.memory_manager.get_current_session()
            memory.add_user_message(user_input)
            
            # Log the conversation
            logger.info(f"User input: {user_input}")
            
            # Check if user is asking about SQL
            response_text = ""
            
            if any(word in user_input.lower() for word in ['select', 'sql', 'query', 'table', 'schema', 'database']):
                # Try RAG search first
                if self.query_engine:
                    try:
                        rag_response = self.query_engine.query(user_input)
                        response_text = str(rag_response)
                    except Exception as e:
                        logger.warning(f"RAG search failed: {e}")
                
                # If no good RAG response, use direct LLM
                if not response_text:
                    # Build context from memory
                    context = memory.get_context_string()
                    
                    # Create prompt
                    prompt = f"""You are a helpful database assistant. Based on the following database schema information:
                    
The database contains these tables:
- employees: Employee information (employee_id, first_name, last_name, email, phone, hire_date, job_title, salary, department_id, manager_id)
- departments: Department information (department_id, department_name, location, budget, head_count)  
- projects: Project information (project_id, project_name, description, start_date, end_date, status, budget, department_id, project_manager_id)
- customers: Customer information (customer_id, company_name, contact_name, contact_email, contact_phone, address, city, country, credit_limit, account_manager_id)
- orders: Order information (order_id, customer_id, order_date, required_date, shipped_date, status, total_amount, payment_method, shipping_address, notes, created_by)

Previous conversation:
{context}

User: {user_input}

Please provide a helpful response. If asked for SQL, only provide SELECT queries (no INSERT, UPDATE, DELETE, DROP, etc.).