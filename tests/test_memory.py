import sys
import os
import unittest
import json
import tempfile
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'agent'))

# Import directly from memory module
import memory
ConversationMemory = memory.ConversationMemory
MemoryManager = memory.MemoryManager


class TestConversationMemory(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.memory = ConversationMemory(max_messages=3)
    
    def test_add_messages(self):
        """Test adding messages to memory"""
        print("Testing message addition...")
        
        # Add user message
        self.memory.add_user_message("Hello, how are you?")
        self.assertEqual(len(self.memory.messages), 1)
        self.assertEqual(self.memory.messages[0]['role'], 'user')
        print("  [OK] User message added")
        
        # Add assistant message
        self.memory.add_assistant_message("I'm doing well, thank you!")
        self.assertEqual(len(self.memory.messages), 2)
        self.assertEqual(self.memory.messages[1]['role'], 'assistant')
        print("  [OK] Assistant message added")
        
        # Add system message
        self.memory.add_system_message("System notification")
        self.assertEqual(len(self.memory.messages), 3)
        self.assertEqual(self.memory.messages[2]['role'], 'system')
        print("  [OK] System message added")
    
    def test_max_messages_limit(self):
        """Test that memory respects max_messages limit"""
        print("Testing max messages limit...")
        
        # Add more messages than limit (max_messages=3, so 6 messages total)
        for i in range(8):
            if i % 2 == 0:
                self.memory.add_user_message(f"User message {i}")
            else:
                self.memory.add_assistant_message(f"Assistant message {i}")
        
        # Should only keep last 6 messages (3 pairs * 2)
        self.assertEqual(len(self.memory.messages), 6)
        print(f"  [OK] Memory limited to {len(self.memory.messages)} messages")
    
    def test_get_context(self):
        """Test getting conversation context"""
        print("Testing context retrieval...")
        
        self.memory.add_user_message("Question 1")
        self.memory.add_assistant_message("Answer 1")
        self.memory.add_system_message("System info")
        
        # Get context with system messages
        context = self.memory.get_context(include_system=True)
        self.assertEqual(len(context), 3)
        print("  [OK] Context with system messages retrieved")
        
        # Get context without system messages
        context = self.memory.get_context(include_system=False)
        self.assertEqual(len(context), 2)
        print("  [OK] Context without system messages retrieved")
    
    def test_get_last_messages(self):
        """Test getting last user/assistant messages"""
        print("Testing last message retrieval...")
        
        self.memory.add_user_message("First user message")
        self.memory.add_assistant_message("First assistant message")
        self.memory.add_user_message("Last user message")
        self.memory.add_assistant_message("Last assistant message")
        
        last_user = self.memory.get_last_user_message()
        self.assertEqual(last_user, "Last user message")
        print("  [OK] Last user message retrieved")
        
        last_assistant = self.memory.get_last_assistant_message()
        self.assertEqual(last_assistant, "Last assistant message")
        print("  [OK] Last assistant message retrieved")
    
    def test_clear_memory(self):
        """Test clearing memory"""
        print("Testing memory clear...")
        
        self.memory.add_user_message("Test message")
        self.memory.clear()
        
        self.assertEqual(len(self.memory.messages), 0)
        print("  [OK] Memory cleared")
    
    def test_save_and_load(self):
        """Test saving and loading conversation"""
        print("Testing save and load...")
        
        # Add some messages
        self.memory.add_user_message("User message")
        self.memory.add_assistant_message("Assistant response")
        self.memory.set_session_metadata("test_key", "test_value")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            self.memory.save_to_file(temp_file)
            print("  [OK] Conversation saved")
            
            # Create new memory and load
            new_memory = ConversationMemory()
            new_memory.load_from_file(temp_file)
            
            # Verify loaded data
            self.assertEqual(len(new_memory.messages), 2)
            self.assertEqual(new_memory.get_session_metadata("test_key"), "test_value")
            print("  [OK] Conversation loaded")
        finally:
            # Clean up
            Path(temp_file).unlink(missing_ok=True)
    
    def test_get_summary(self):
        """Test conversation summary"""
        print("Testing conversation summary...")
        
        self.memory.add_user_message("User 1")
        self.memory.add_assistant_message("Assistant 1")
        self.memory.add_user_message("User 2")
        
        summary = self.memory.get_summary()
        self.assertEqual(summary['user_messages'], 2)
        self.assertEqual(summary['assistant_messages'], 1)
        self.assertEqual(summary['total_messages'], 3)
        print("  [OK] Summary generated correctly")


class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.manager = MemoryManager()
    
    def test_session_management(self):
        """Test session creation and switching"""
        print("Testing session management...")
        
        # Default session should exist
        self.assertIn('default', self.manager.sessions)
        print("  [OK] Default session exists")
        
        # Create new session
        self.manager.create_session('test_session')
        self.assertIn('test_session', self.manager.sessions)
        print("  [OK] New session created")
        
        # Switch session
        self.manager.set_current_session('test_session')
        self.assertEqual(self.manager.current_session_id, 'test_session')
        print("  [OK] Session switched")
    
    def test_session_isolation(self):
        """Test that sessions are isolated"""
        print("Testing session isolation...")
        
        # Add message to default session
        default_session = self.manager.get_session('default')
        default_session.add_user_message("Default message")
        
        # Create and switch to new session
        self.manager.create_session('isolated')
        isolated_session = self.manager.get_session('isolated')
        
        # Verify isolation
        self.assertEqual(len(default_session.messages), 1)
        self.assertEqual(len(isolated_session.messages), 0)
        print("  [OK] Sessions are isolated")
    
    def test_delete_session(self):
        """Test session deletion"""
        print("Testing session deletion...")
        
        self.manager.create_session('to_delete')
        self.manager.delete_session('to_delete')
        
        self.assertNotIn('to_delete', self.manager.sessions)
        print("  [OK] Session deleted")
    
    def test_list_sessions(self):
        """Test listing sessions"""
        print("Testing session listing...")
        
        self.manager.create_session('session1')
        self.manager.create_session('session2')
        
        sessions = self.manager.list_sessions()
        self.assertIn('default', sessions)
        self.assertIn('session1', sessions)
        self.assertIn('session2', sessions)
        print(f"  [OK] Listed {len(sessions)} sessions")


if __name__ == '__main__':
    print("\n" + "="*50)
    print("MEMORY TESTS")
    print("="*50 + "\n")
    
    # Run tests
    unittest.main(verbosity=0, exit=False)