from typing import List, Dict, Any, Optional
import requests
import json
from utils import config_loader, get_logger, query_logger
from .memory import ConversationMemory, MemoryManager


logger = get_logger(__name__)


class LLMAgent:
    """Simple LLM Agent using direct Ollama API calls"""
    
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """Initialize the LLM Agent"""
        self.config = config_loader.config
        self.ollama_config = self.config['ollama']
        self.agent_config = self.config['agent']
        
        # Initialize memory
        self.memory_manager = memory_manager or MemoryManager()
        
        # Build Ollama API URL
        self.ollama_url = f"{self.ollama_config['host']}:{self.ollama_config['port']}/api/generate"
        
        logger.info("LLM Agent initialized successfully")
    
    def _call_ollama(self, prompt: str, timeout: int = 60) -> str:
        """Call Ollama API directly"""
        data = {
            "model": self.ollama_config['model'],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.ollama_config.get('temperature', 0.7),
                "num_predict": self.ollama_config.get('max_tokens', 512),
                "stop": ["User:", "\n\n\n"]
            }
        }
        
        try:
            response = requests.post(
                self.ollama_url,
                json=data,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return "Error: Failed to get response from Ollama"
                
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {timeout} seconds")
            return "Error: Request timed out. Please try again."
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            return f"Error: {str(e)}"
    
    def chat(self, user_input: str) -> str:
        """Process user input and generate response"""
        try:
            # Add user message to memory
            memory = self.memory_manager.get_current_session()
            memory.add_user_message(user_input)
            
            # Log the conversation
            logger.info(f"User input: {user_input}")
            
            # Build context from memory
            context = memory.get_context_string(max_messages=4)  # Limit context to last 4 messages
            
            # Check if user is asking about SQL or database
            is_db_query = any(word in user_input.lower() for word in ['select', 'sql', 'query', 'table', 'schema', 'database', 'employees', 'departments', 'orders'])
            
            # Create prompt based on query type
            if is_db_query:
                prompt = f"""You are a helpful database assistant. The database has these tables:
- employees (employee_id, first_name, last_name, email, phone, hire_date, job_title, salary, department_id, manager_id)
- departments (department_id, department_name, location, budget, head_count)
- projects (project_id, project_name, description, start_date, end_date, status, budget, department_id, project_manager_id)
- customers (customer_id, company_name, contact_name, contact_email, contact_phone, address, city, country, credit_limit, account_manager_id)
- orders (order_id, customer_id, order_date, required_date, shipped_date, status, total_amount, payment_method, shipping_address, notes, created_by)

User: {user_input}
Assistant: """
            else:
                # Simple prompt for general queries
                if context:
                    prompt = f"""Previous conversation:
{context}

User: {user_input}
Assistant: """
                else:
                    prompt = f"""User: {user_input}
Assistant: """
            
            # Get response from Ollama
            logger.info("Calling Ollama API...")
            response_text = self._call_ollama(prompt, timeout=60)
            
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