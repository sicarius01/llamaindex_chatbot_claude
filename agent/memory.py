from typing import List, Dict, Any, Optional
from collections import deque
import json
import sys
sys.path.append('..')
from utils import config_loader, get_logger


logger = get_logger(__name__)


class ConversationMemory:
    """Manage conversation history and context"""
    
    def __init__(self, max_messages: Optional[int] = None):
        """
        Initialize conversation memory
        
        Args:
            max_messages: Maximum number of messages to keep in memory.
                         If None, uses value from config
        """
        config = config_loader.get_section('agent')
        self.max_messages = max_messages or config.get('max_context_messages', 5)
        self.messages = deque(maxlen=self.max_messages * 2)  # *2 for user+assistant pairs
        self.full_history = []  # Keep full history for logging
        self.session_metadata = {}
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a message to the conversation history
        
        Args:
            role: 'user', 'assistant', or 'system'
            content: Message content
            metadata: Optional metadata (tool calls, timestamps, etc.)
        """
        message = {
            'role': role,
            'content': content,
            'metadata': metadata or {}
        }
        
        self.messages.append(message)
        self.full_history.append(message)
        
        logger.debug(f"Added {role} message to memory: {content[:100]}...")
    
    def add_user_message(self, content: str):
        """Add a user message to the conversation"""
        self.add_message('user', content)
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add an assistant message to the conversation"""
        self.add_message('assistant', content, metadata)
    
    def add_system_message(self, content: str):
        """Add a system message to the conversation"""
        self.add_message('system', content)
    
    def get_context(self, include_system: bool = True) -> List[Dict[str, str]]:
        """
        Get the current conversation context
        
        Args:
            include_system: Whether to include system messages
        
        Returns:
            List of message dictionaries
        """
        context = []
        for msg in self.messages:
            if not include_system and msg['role'] == 'system':
                continue
            context.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        return context
    
    def get_context_string(self, separator: str = "\n") -> str:
        """
        Get conversation context as a formatted string
        
        Args:
            separator: String to separate messages
        
        Returns:
            Formatted conversation string
        """
        lines = []
        for msg in self.get_context():
            role = msg['role'].capitalize()
            lines.append(f"{role}: {msg['content']}")
        
        return separator.join(lines)
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message"""
        for msg in reversed(self.messages):
            if msg['role'] == 'user':
                return msg['content']
        return None
    
    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message"""
        for msg in reversed(self.messages):
            if msg['role'] == 'assistant':
                return msg['content']
        return None
    
    def clear(self):
        """Clear the conversation memory"""
        self.messages.clear()
        logger.info("Conversation memory cleared")
    
    def save_to_file(self, filepath: str):
        """
        Save conversation history to a JSON file
        
        Args:
            filepath: Path to save the conversation
        """
        try:
            data = {
                'messages': list(self.messages),
                'full_history': self.full_history,
                'metadata': self.session_metadata
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Conversation saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save conversation: {str(e)}")
    
    def load_from_file(self, filepath: str):
        """
        Load conversation history from a JSON file
        
        Args:
            filepath: Path to load the conversation from
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.messages = deque(data['messages'], maxlen=self.max_messages * 2)
            self.full_history = data.get('full_history', list(self.messages))
            self.session_metadata = data.get('metadata', {})
            
            logger.info(f"Conversation loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load conversation: {str(e)}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation
        
        Returns:
            Dictionary containing conversation statistics
        """
        user_messages = sum(1 for msg in self.full_history if msg['role'] == 'user')
        assistant_messages = sum(1 for msg in self.full_history if msg['role'] == 'assistant')
        
        return {
            'total_messages': len(self.full_history),
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'current_context_size': len(self.messages),
            'max_context_size': self.max_messages * 2
        }
    
    def set_session_metadata(self, key: str, value: Any):
        """Set session metadata"""
        self.session_metadata[key] = value
    
    def get_session_metadata(self, key: str, default: Any = None) -> Any:
        """Get session metadata"""
        return self.session_metadata.get(key, default)


class MemoryManager:
    """Manage multiple conversation memories and sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationMemory] = {}
        self.current_session_id = 'default'
        self.sessions[self.current_session_id] = ConversationMemory()
    
    def create_session(self, session_id: str, max_messages: Optional[int] = None) -> ConversationMemory:
        """
        Create a new conversation session
        
        Args:
            session_id: Unique identifier for the session
            max_messages: Maximum messages for this session
        
        Returns:
            New ConversationMemory instance
        """
        if session_id in self.sessions:
            logger.warning(f"Session {session_id} already exists, overwriting")
        
        self.sessions[session_id] = ConversationMemory(max_messages)
        logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[ConversationMemory]:
        """Get a conversation session by ID"""
        return self.sessions.get(session_id)
    
    def set_current_session(self, session_id: str):
        """Set the current active session"""
        if session_id not in self.sessions:
            self.create_session(session_id)
        self.current_session_id = session_id
        logger.info(f"Switched to session: {session_id}")
    
    def get_current_session(self) -> ConversationMemory:
        """Get the current active session"""
        return self.sessions[self.current_session_id]
    
    def delete_session(self, session_id: str):
        """Delete a conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            
            # If we deleted the current session, switch to default
            if session_id == self.current_session_id:
                self.current_session_id = 'default'
                if 'default' not in self.sessions:
                    self.create_session('default')
    
    def list_sessions(self) -> List[str]:
        """List all available session IDs"""
        return list(self.sessions.keys())
    
    def clear_all_sessions(self):
        """Clear all conversation sessions"""
        self.sessions.clear()
        self.current_session_id = 'default'
        self.sessions[self.current_session_id] = ConversationMemory()
        logger.info("All sessions cleared")