from typing import List, Dict, Any, Optional
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.agent import ReActAgent
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
import sys
sys.path.append('..')
from utils import config_loader, get_logger, query_logger
from .memory import ConversationMemory, MemoryManager
from .tools import get_all_tools


logger = get_logger(__name__)


class LLMAgent:
    """Core agent that orchestrates LLM, tools, and memory"""
    
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
        self.tools = get_all_tools()
        
        # Initialize agent
        self.agent = self._initialize_agent()
        
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
    
    def _initialize_agent(self) -> ReActAgent:
        """Initialize ReAct agent with tools"""
        try:
            # Get current conversation memory
            memory = self.memory_manager.get_current_session()
            
            # Build context from memory
            context_messages = memory.get_context()
            context_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context_messages[-4:]])  # Last 2 exchanges
            
            # Create system prompt with context
            system_prompt = self.agent_config.get('system_prompt', 
                "You are a helpful AI assistant specialized in database queries and information retrieval.")
            
            if context_str:
                system_prompt += f"\n\nPrevious conversation context:\n{context_str}"
            
            # Create ReAct agent using constructor
            agent = ReActAgent(
                tools=self.tools,
                llm=self.llm,
                verbose=self.agent_config.get('verbose', True),
                max_iterations=10
            )
            
            logger.info("Initialized ReAct agent with tools")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
    
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
            
            # Reinitialize agent with updated context
            self.agent = self._initialize_agent()
            
            # Get response from agent using run method
            import asyncio
            response = asyncio.run(self.agent.run(user_input))
            
            # Extract response text
            response_text = str(response)
            
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
        try:
            # Add user message to memory
            memory = self.memory_manager.get_current_session()
            memory.add_user_message(user_input)
            
            # Reinitialize agent with updated context
            self.agent = self._initialize_agent()
            
            # Get response from agent using run method
            import asyncio
            response = asyncio.run(self.agent.run(user_input))
            
            # Extract response and metadata
            response_text = str(response)
            
            # Get tool outputs if any
            tool_outputs = []
            if hasattr(response, 'sources'):
                for source in response.sources:
                    tool_outputs.append({
                        'tool': source.tool_name if hasattr(source, 'tool_name') else 'unknown',
                        'output': str(source.content) if hasattr(source, 'content') else str(source)
                    })
            
            # Add assistant response to memory with metadata
            metadata = {
                'tool_outputs': tool_outputs,
                'sources_count': len(tool_outputs)
            }
            memory.add_assistant_message(response_text, metadata)
            
            # Log the conversation
            query_logger.log_conversation(user_input, response_text)
            
            return {
                'response': response_text,
                'tool_outputs': tool_outputs,
                'success': True,
                'session_id': self.memory_manager.current_session_id
            }
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            logger.error(error_msg)
            return {
                'response': error_msg,
                'tool_outputs': [],
                'success': False,
                'error': str(e),
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
        # Reinitialize agent with loaded context
        self.agent = self._initialize_agent()
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation"""
        memory = self.memory_manager.get_current_session()
        return memory.get_summary()
    
    def switch_session(self, session_id: str):
        """Switch to a different conversation session"""
        self.memory_manager.set_current_session(session_id)
        # Reinitialize agent with new session context
        self.agent = self._initialize_agent()
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