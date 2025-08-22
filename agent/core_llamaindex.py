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
                request_timeout=300.0,  # Increased timeout to 5 minutes
                additional_kwargs={
                    "num_predict": self.ollama_config.get('max_tokens', 512),  # Reduced for faster response
                    "stop": ["User:", "\n\n\n"]  # Add stop sequences
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
            
            # Build context from memory
            context = memory.get_context_string()
            
            # Check if user is asking about SQL or database
            is_db_query = any(word in user_input.lower() for word in ['select', 'sql', 'query', 'table', 'schema', 'database', 'employees', 'departments', 'orders'])
            
            # Create prompt based on query type
            if is_db_query:
                prompt = f"""You are a helpful database assistant specializing in SQL queries.

Available tables:
- employees: Employee information (employee_id, first_name, last_name, email, phone, hire_date, job_title, salary, department_id, manager_id)
- departments: Department information (department_id, department_name, location, budget, head_count)
- projects: Project information (project_id, project_name, description, start_date, end_date, status, budget, department_id, project_manager_id)
- customers: Customer information (customer_id, company_name, contact_name, contact_email, contact_phone, address, city, country, credit_limit, account_manager_id)
- orders: Order information (order_id, customer_id, order_date, required_date, shipped_date, status, total_amount, payment_method, shipping_address, notes, created_by)

Context: {context}

User: {user_input}

Response (provide SQL queries if asked, only SELECT statements allowed):"""
            else:
                prompt = f"""You are a helpful assistant. Keep responses concise and friendly.

Context: {context}

User: {user_input}

Response:"""
            
            # Get response from LLM with error handling
            try:
                logger.info("Calling Ollama LLM...")
                response = self.llm.complete(prompt)
                response_text = str(response).strip()
                
                # Handle empty responses
                if not response_text or response_text == "Empty Response":
                    response_text = "I understand your message. How can I help you with database queries today?"
                    
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                response_text = "I apologize, but I'm having trouble processing your request. Please try again."
            
            # Add assistant response to memory
            memory.add_assistant_message(response_text)
            
            # Log the response
            logger.info(f"Agent response: {response_text[:200]}...")
            query_logger.log_conversation(user_input, response_text)
            
            return response_text
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def query(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and return structured response with metadata
        
        Args:
            user_input: User's message
        
        Returns:
            Dictionary with response and metadata
        """
        response = self.chat(user_input)
        return {
            'response': response,
            'success': not response.startswith("Error"),
            'session_id': self.memory_manager.current_session_id
        }
    
    def reset_conversation(self):
        """Reset the current conversation"""
        memory = self.memory_manager.get_current_session()
        memory.clear()
        logger.info("Conversation reset")
    
    def save_conversation(self, filepath: str):
        """Save current conversation to file"""
        memory = self.memory_manager.get_current_session()
        memory.save_to_file(filepath)
    
    def load_conversation(self, filepath: str):
        """Load conversation from file"""
        memory = self.memory_manager.get_current_session()
        memory.load_from_file(filepath)
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation"""
        memory = self.memory_manager.get_current_session()
        return memory.get_summary()
    
    def switch_session(self, session_id: str):
        """Switch to a different conversation session"""
        self.memory_manager.set_current_session(session_id)
        logger.info(f"Switched to session: {session_id}")
    
    def list_sessions(self) -> List[str]:
        """List all available sessions"""
        return self.memory_manager.list_sessions()


class AgentOrchestrator:
    """High-level orchestrator for managing multiple agents"""
    
    def __init__(self):
        self.agents: Dict[str, LLMAgent] = {}
        self.current_agent_id = 'default'
        self.agents[self.current_agent_id] = LLMAgent()
    
    def create_agent(self, agent_id: str) -> LLMAgent:
        """Create a new agent instance"""
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already exists, overwriting")
        
        self.agents[agent_id] = LLMAgent()
        logger.info(f"Created new agent: {agent_id}")
        return self.agents[agent_id]
    
    def get_agent(self, agent_id: str) -> Optional[LLMAgent]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)
    
    def set_current_agent(self, agent_id: str):
        """Set the current active agent"""
        if agent_id not in self.agents:
            self.create_agent(agent_id)
        self.current_agent_id = agent_id
        logger.info(f"Switched to agent: {agent_id}")
    
    def get_current_agent(self) -> LLMAgent:
        """Get the current active agent"""
        return self.agents[self.current_agent_id]
    
    def delete_agent(self, agent_id: str):
        """Delete an agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Deleted agent: {agent_id}")
            
            # If we deleted the current agent, switch to default
            if agent_id == self.current_agent_id:
                self.current_agent_id = 'default'
                if 'default' not in self.agents:
                    self.create_agent('default')
    
    def list_agents(self) -> List[str]:
        """List all available agent IDs"""
        return list(self.agents.keys())