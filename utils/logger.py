import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from .config_loader import config_loader


def setup_logging(name: str = None) -> logging.Logger:
    """
    Setup logging configuration from config file
    
    Args:
        name: Logger name. If None, returns root logger
    
    Returns:
        Configured logger instance
    """
    config = config_loader.get_section('logging')
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set logging level
    log_level = getattr(logging, config.get('level', 'INFO').upper())
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler without rotation (to avoid Windows file lock issues)
    log_file = Path(config.get('file', './logs/agent.log'))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Use basic FileHandler instead of RotatingFileHandler
    file_handler = logging.FileHandler(
        log_file,
        mode='a',  # Append mode
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return setup_logging(name)


class QueryLogger:
    """Special logger for SQL queries and tool calls"""
    
    def __init__(self):
        self.logger = get_logger('query_logger')
    
    def log_sql_query(self, query: str, result: Optional[any] = None, error: Optional[Exception] = None):
        """Log SQL query execution"""
        if error:
            self.logger.error(f"SQL Query Failed:\n{query}\nError: {str(error)}")
        else:
            self.logger.info(f"SQL Query Executed:\n{query}")
            if result is not None:
                self.logger.debug(f"Query Result: {result}")
    
    def log_tool_call(self, tool_name: str, input_data: dict, output: any = None, error: Optional[Exception] = None):
        """Log tool execution"""
        if error:
            self.logger.error(f"Tool '{tool_name}' Failed:\nInput: {input_data}\nError: {str(error)}")
        else:
            self.logger.info(f"Tool '{tool_name}' Called:\nInput: {input_data}")
            if output is not None:
                self.logger.debug(f"Tool Output: {output}")
    
    def log_conversation(self, user_input: str, agent_response: str):
        """Log conversation turns"""
        self.logger.info(f"User: {user_input}")
        self.logger.info(f"Agent: {agent_response}")
    
    def log_rag_search(self, query: str, results: list):
        """Log RAG search operations"""
        self.logger.info(f"RAG Search Query: {query}")
        self.logger.debug(f"Found {len(results)} results")
        for i, result in enumerate(results[:3]):  # Log top 3 results
            self.logger.debug(f"Result {i+1}: {str(result)[:200]}...")


# Create global query logger instance
query_logger = QueryLogger()