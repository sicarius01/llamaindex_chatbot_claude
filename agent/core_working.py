"""
Working version of LLM Agent with direct Ollama integration
This version focuses on stability and functionality
"""
from typing import List, Dict, Any, Optional
import json
from llama_index.core import Settings, VectorStoreIndex
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.tools import FunctionTool

from utils import config_loader, get_logger, query_logger
from .memory import ConversationMemory, MemoryManager
from .tools import get_all_tools, RAGSearchTool, SQLQueryTool
from parsers.schema_loader import get_schema_loader

logger = get_logger(__name__)


class LLMAgent:
    """Simple but working LLM Agent with Ollama and Tools"""
    
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """Initialize the LLM Agent"""
        self.config = config_loader.config
        self.ollama_config = self.config['ollama']
        self.agent_config = self.config['agent']
        
        # Initialize memory manager
        self.memory_manager = memory_manager or MemoryManager()
        
        # Initialize Ollama LLM
        self._initialize_ollama()
        
        # Initialize tools
        self._initialize_tools()
        
        # Load schema context
        self.schema_loader = get_schema_loader()
        
        logger.info("LLM Agent initialized successfully")
    
    def _initialize_ollama(self):
        """Initialize Ollama LLM"""
        try:
            self.llm = Ollama(
                model=self.ollama_config['model'],
                base_url=f"{self.ollama_config['host']}:{self.ollama_config['port']}",
                temperature=self.ollama_config.get('temperature', 0.7),
                request_timeout=120.0
            )
            
            self.embed_model = OllamaEmbedding(
                model_name=self.ollama_config.get('embedding_model', 'nomic-embed-text'),
                base_url=f"{self.ollama_config['host']}:{self.ollama_config['port']}"
            )
            
            logger.info(f"Ollama initialized with model: {self.ollama_config['model']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {str(e)}")
            raise
    
    def _initialize_tools(self):
        """Initialize available tools"""
        self.rag_tool = RAGSearchTool()
        self.sql_tool = SQLQueryTool()
        logger.info("Tools initialized: RAG Search, SQL Query")
    
    def _build_prompt(self, user_input: str, context: str = "") -> str:
        """Build prompt with schema context and conversation history"""
        # Get schema context
        schema_context = self.schema_loader.get_context_for_llm()
        
        # Get system prompt
        system_prompt = self.agent_config.get('system_prompt', 
            "You are a helpful AI assistant specialized in database queries.")
        
        # Build complete prompt
        prompt = f"""{system_prompt}

Available Database Schema:
{schema_context}

Instructions:
- For database queries, provide SQL SELECT statements only
- Never use INSERT, UPDATE, DELETE, DROP, or other write operations
- Use the schema information above to write accurate queries

{context}

User: {user_input}
Assistant: """
        
        return prompt
    
    def chat(self, user_input: str) -> str:
        """Process user input and generate response"""
        try:
            # Add user message to memory
            memory = self.memory_manager.get_current_session()
            memory.add_user_message(user_input)
            
            # Log the conversation
            logger.info(f"User input: {user_input}")
            
            # Get conversation context
            context = memory.get_context_string(include_system=False)
            
            # Check if user is asking about SQL/database
            is_db_query = any(word in user_input.lower() for word in [
                'select', 'sql', 'query', 'table', 'schema', 'database',
                'employee', 'department', 'customer', 'order', 'product'
            ])
            
            # Try to search relevant documents if it's a DB query
            search_results = ""
            if is_db_query:
                try:
                    results = self.rag_tool.search(user_input, top_k=3)
                    if results:
                        search_results = "\nRelevant documentation found:\n"
                        for r in results[:2]:
                            search_results += f"- {r['text'][:200]}...\n"
                except Exception as e:
                    logger.warning(f"RAG search failed: {str(e)}")
            
            # Build prompt
            full_context = context
            if search_results:
                full_context += search_results
            
            prompt = self._build_prompt(user_input, full_context)
            
            # Get response from Ollama
            logger.info("Calling Ollama LLM...")
            response = self.llm.complete(prompt)
            
            # Extract text
            if hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = str(response)
            
            # Clean response
            response_text = response_text.strip()
            
            # If response contains SQL, validate it
            if 'SELECT' in response_text.upper():
                # Extract SQL from response
                import re
                sql_pattern = r'```sql\s*(.*?)\s*```|SELECT\s+.*?(?:;|$)'
                sql_matches = re.findall(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
                
                for sql_match in sql_matches:
                    sql_query = sql_match if isinstance(sql_match, str) else sql_match[0]
                    if sql_query:
                        # Validate SQL
                        from agent.tools import SQLValidator
                        is_safe, reason = SQLValidator.is_safe_query(sql_query)
                        if not is_safe:
                            response_text += f"\n\n⚠️ 주의: 이 쿼리는 보안상 실행할 수 없습니다: {reason}"
            
            # Handle empty response
            if not response_text:
                response_text = "죄송합니다. 응답을 생성할 수 없습니다. 다시 시도해주세요."
            
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
        """Process user input and return structured response"""
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