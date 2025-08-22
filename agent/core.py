from typing import List, Dict, Any, Optional
import json
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool

from utils import config_loader, get_logger, query_logger
from .memory import ConversationMemory, MemoryManager
from .tools import get_all_tools, RAGSearchTool, SQLQueryTool


logger = get_logger(__name__)


class LLMAgent:
    """LlamaIndex-based LLM Agent with ReAct pattern and tools"""
    
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """Initialize the LLM Agent with LlamaIndex components"""
        self.config = config_loader.config
        self.ollama_config = self.config['ollama']
        self.agent_config = self.config['agent']
        
        # Initialize memory manager
        self.memory_manager = memory_manager or MemoryManager()
        
        # Initialize LlamaIndex components
        self._initialize_llama_index()
        
        # Initialize tools
        self.tools = get_all_tools()
        
        # Initialize agent
        self._initialize_agent()
        
        logger.info("LlamaIndex Agent initialized successfully")
    
    def _initialize_llama_index(self):
        """Initialize LlamaIndex Settings with Ollama models"""
        try:
            # Configure LLM
            llm = Ollama(
                model=self.ollama_config['model'],
                base_url=f"{self.ollama_config['host']}:{self.ollama_config['port']}",
                temperature=self.ollama_config.get('temperature', 0.7),
                request_timeout=120.0,
                additional_kwargs={
                    "num_predict": self.ollama_config.get('max_tokens', 2048)
                }
            )
            
            # Configure embedding model
            embed_model = OllamaEmbedding(
                model_name=self.ollama_config.get('embedding_model', 'nomic-embed-text'),
                base_url=f"{self.ollama_config['host']}:{self.ollama_config['port']}",
                embed_batch_size=10
            )
            
            # Set global settings
            Settings.llm = llm
            Settings.embed_model = embed_model
            Settings.chunk_size = self.config.get('rag', {}).get('chunk_size', 512)
            Settings.chunk_overlap = self.config.get('rag', {}).get('chunk_overlap', 50)
            
            self.llm = llm
            self.embed_model = embed_model
            
            logger.info(f"LlamaIndex initialized with model: {self.ollama_config['model']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LlamaIndex: {str(e)}")
            raise
    
    def _initialize_agent(self):
        """Initialize ReAct agent with tools and memory"""
        try:
            # Get system prompt from config
            system_prompt = self.agent_config.get('system_prompt', 
                "You are a helpful AI assistant specialized in database queries and information retrieval.")
            
            # Initialize chat memory
            memory = ChatMemoryBuffer.from_defaults(
                token_limit=self.ollama_config.get('max_tokens', 2048)
            )
            
            # Create ReAct agent with tools
            from llama_index.core.agent import FunctionCallingAgentWorker
            
            agent_worker = FunctionCallingAgentWorker.from_tools(
                tools=self.tools,
                llm=self.llm,
                verbose=self.agent_config.get('verbose', False),
                system_prompt=system_prompt
            )
            
            self.agent = agent_worker.as_agent()
            
            logger.info(f"ReAct agent initialized with {len(self.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
    
    def chat(self, user_input: str) -> str:
        """Process user input and generate response"""
        try:
            # Add user message to memory
            memory = self.memory_manager.get_current_session()
            memory.add_user_message(user_input)
            
            # Log the conversation
            logger.info(f"User input: {user_input}")
            
            # Build context from memory
            context = memory.get_context_string()  # Get context from memory
            
            # Use the ReAct agent to process the query
            logger.info("Processing with ReAct agent...")
            
            # Get response from agent
            response = self.agent.chat(user_input)
            
            # Extract text response
            if hasattr(response, 'response'):
                response_text = response.response
            else:
                response_text = str(response)
            
            # Clean up response text if needed
            response_text = response_text.strip()
            
            # Remove any remaining special characters that might cause encoding issues
            import re
            response_text = re.sub(r'[^\x00-\x7F\u0080-\u00FF\u4e00-\u9fff\uac00-\ud7af]+', '', response_text)
            
            # Handle errors and empty responses
            if response_text.startswith("Error:"):
                logger.error(f"Ollama returned error: {response_text}")
            elif not response_text:
                response_text = "I understand. How can I help you with database queries?"
            
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
        """Process user input and return structured response with tool outputs"""
        try:
            # Get response from agent
            agent_response = self.agent.chat(user_input)
            
            # Extract tool outputs if available
            tool_outputs = []
            if hasattr(agent_response, 'sources'):
                for source in agent_response.sources:
                    tool_outputs.append({
                        'tool': source.tool_name if hasattr(source, 'tool_name') else 'unknown',
                        'output': str(source.content) if hasattr(source, 'content') else str(source)
                    })
            
            # Get response text
            if hasattr(agent_response, 'response'):
                response_text = agent_response.response
            else:
                response_text = str(agent_response)
            
            # Add to memory
            memory = self.memory_manager.get_current_session()
            memory.add_user_message(user_input)
            memory.add_assistant_message(response_text)
            
            # Log the conversation
            query_logger.log_conversation(user_input, response_text)
            
            return {
                'response': response_text,
                'success': True,
                'session_id': self.memory_manager.current_session_id,
                'tool_outputs': tool_outputs
            }
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg)
            return {
                'response': error_msg,
                'success': False,
                'session_id': self.memory_manager.current_session_id,
                'tool_outputs': []
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