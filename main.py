#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Fix Windows encoding issues
if sys.platform == 'win32':
    import codecs
    # Set console to UTF-8
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich import print as rprint

from utils import config_loader, get_logger, setup_logging
from agent import LLMAgent, AgentOrchestrator
from parsers import SchemaIndexBuilder


# Initialize logger
logger = setup_logging('main')

# Initialize Rich console for better CLI output
console = Console()


class ChatbotCLI:
    """Command-line interface for the LLM chatbot"""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the CLI
        
        Args:
            verbose: Whether to show verbose output
        """
        self.verbose = verbose
        self.agent = None
        self.orchestrator = AgentOrchestrator()
        
        # Update config if verbose mode
        if verbose:
            config_loader.update('agent.verbose', True)
    
    def display_welcome(self):
        """Display welcome message"""
        welcome_text = """
# LlamaIndex + Ollama Local LLM Agent

Welcome to the local LLM chatbot! This agent can:
* Search through database schema documentation
* Execute read-only SQL queries
* Provide intelligent responses based on your data

Type 'help' for available commands or start chatting!
        """
        try:
            console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="cyan"))
        except UnicodeEncodeError:
            # Fallback to simple text without markdown
            console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))
    
    def display_help(self):
        """Display help information"""
        help_table = Table(title="Available Commands", show_header=True, header_style="bold magenta")
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        
        commands = [
            ("help", "Show this help message"),
            ("exit / quit", "Exit the application"),
            ("clear", "Clear the conversation history"),
            ("save [filename]", "Save conversation to file"),
            ("load [filename]", "Load conversation from file"),
            ("rebuild", "Rebuild the RAG index"),
            ("sessions", "List all conversation sessions"),
            ("session [id]", "Switch to a different session"),
            ("summary", "Show conversation summary"),
            ("verbose", "Toggle verbose mode"),
            ("config", "Show current configuration"),
        ]
        
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
        
        console.print(help_table)
    
    def display_config(self):
        """Display current configuration"""
        config_table = Table(title="Current Configuration", show_header=True, header_style="bold green")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="white")
        
        config_items = [
            ("Ollama Model", config_loader.get('ollama.model')),
            ("Ollama Host", f"{config_loader.get('ollama.host')}:{config_loader.get('ollama.port')}"),
            ("Embedding Model", config_loader.get('ollama.embedding_model')),
            ("Vector Store", config_loader.get('vector_store.type')),
            ("Max Context Messages", config_loader.get('agent.max_context_messages')),
            ("Verbose Mode", str(self.verbose)),
            ("Log Level", config_loader.get('logging.level')),
        ]
        
        for setting, value in config_items:
            config_table.add_row(setting, str(value))
        
        console.print(config_table)
    
    def process_command(self, command: str) -> bool:
        """
        Process special commands
        
        Args:
            command: User input command
        
        Returns:
            True if should continue, False if should exit
        """
        cmd_parts = command.lower().split()
        
        if not cmd_parts:
            return True
        
        cmd = cmd_parts[0]
        
        # Exit commands
        if cmd in ['exit', 'quit']:
            console.print("[yellow]Goodbye![/yellow]")
            return False
        
        # Help command
        elif cmd == 'help':
            self.display_help()
        
        # Clear conversation
        elif cmd == 'clear':
            self.agent.reset_conversation()
            console.print("[green]Conversation cleared![/green]")
        
        # Save conversation
        elif cmd == 'save':
            filename = cmd_parts[1] if len(cmd_parts) > 1 else 'conversation.json'
            self.agent.save_conversation(filename)
            console.print(f"[green]Conversation saved to {filename}[/green]")
        
        # Load conversation
        elif cmd == 'load':
            if len(cmd_parts) > 1:
                filename = cmd_parts[1]
                try:
                    self.agent.load_conversation(filename)
                    console.print(f"[green]Conversation loaded from {filename}[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to load conversation: {str(e)}[/red]")
            else:
                console.print("[red]Please specify a filename to load[/red]")
        
        # Rebuild index
        elif cmd == 'rebuild':
            with console.status("[bold green]Rebuilding RAG index..."):
                try:
                    builder = SchemaIndexBuilder()
                    builder.build_index()
                    console.print("[green]RAG index rebuilt successfully![/green]")
                except Exception as e:
                    console.print(f"[red]Failed to rebuild index: {str(e)}[/red]")
        
        # List sessions
        elif cmd == 'sessions':
            sessions = self.agent.list_sessions()
            console.print(f"[cyan]Available sessions: {', '.join(sessions)}[/cyan]")
        
        # Switch session
        elif cmd == 'session':
            if len(cmd_parts) > 1:
                session_id = cmd_parts[1]
                self.agent.switch_session(session_id)
                console.print(f"[green]Switched to session: {session_id}[/green]")
            else:
                console.print("[red]Please specify a session ID[/red]")
        
        # Show summary
        elif cmd == 'summary':
            summary = self.agent.get_conversation_summary()
            summary_table = Table(title="Conversation Summary", show_header=False)
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="white")
            
            for key, value in summary.items():
                summary_table.add_row(key.replace('_', ' ').title(), str(value))
            
            console.print(summary_table)
        
        # Toggle verbose mode
        elif cmd == 'verbose':
            self.verbose = not self.verbose
            config_loader.update('agent.verbose', self.verbose)
            console.print(f"[green]Verbose mode: {self.verbose}[/green]")
        
        # Show config
        elif cmd == 'config':
            self.display_config()
        
        else:
            # Not a command, process as regular input
            return None
        
        return True
    
    def run_interactive(self):
        """Run the interactive CLI"""
        self.display_welcome()
        
        # Initialize agent
        console.print("[cyan]Initializing agent...[/cyan]")
        try:
            self.agent = self.orchestrator.get_current_agent()
            console.print("[green]Agent initialized successfully![/green]\n")
        except Exception as e:
            console.print(f"[red]Failed to initialize agent: {str(e)}[/red]")
            logger.error(f"Agent initialization failed: {str(e)}")
            return
        
        # Main interaction loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # Check for commands
                result = self.process_command(user_input)
                if result is False:  # Exit command
                    break
                elif result is True:  # Command processed
                    continue
                
                # Process as chat input
                with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10) as live:
                    if self.verbose:
                        response_data = self.agent.query(user_input)
                        response = response_data['response']
                        
                        # Show tool outputs if verbose
                        if response_data.get('tool_outputs'):
                            console.print("\n[dim]Tool Outputs:[/dim]")
                            for tool_output in response_data['tool_outputs']:
                                console.print(f"[dim]  - {tool_output['tool']}: {tool_output['output'][:200]}...[/dim]")
                    else:
                        response = self.agent.chat(user_input)
                
                # Display response
                console.print(f"\n[bold green]Assistant[/bold green]: {response}")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                continue
            except Exception as e:
                console.print(f"\n[red]Error: {str(e)}[/red]")
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
    
    def run_single_query(self, query: str):
        """
        Run a single query and exit
        
        Args:
            query: The query to process
        """
        try:
            # Initialize agent
            console.print("[cyan]Initializing agent...[/cyan]")
            self.agent = self.orchestrator.get_current_agent()
            
            # Process query
            with console.status("[bold green]Processing query..."):
                response = self.agent.chat(query)
            
            # Display response
            console.print(f"\n[bold green]Response:[/bold green] {response}")
            
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            logger.error(f"Query processing failed: {str(e)}", exc_info=True)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="LlamaIndex + Ollama Local LLM Agent CLI"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '-q', '--query',
        type=str,
        help='Single query to process (non-interactive mode)'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--rebuild-index',
        action='store_true',
        help='Rebuild the RAG index and exit'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config_loader.load_config(args.config)
    except Exception as e:
        console.print(f"[red]Failed to load configuration: {str(e)}[/red]")
        sys.exit(1)
    
    # Handle rebuild index
    if args.rebuild_index:
        console.print("[cyan]Rebuilding RAG index...[/cyan]")
        try:
            builder = SchemaIndexBuilder()
            builder.build_index()
            console.print("[green]RAG index rebuilt successfully![/green]")
        except Exception as e:
            console.print(f"[red]Failed to rebuild index: {str(e)}[/red]")
            sys.exit(1)
        sys.exit(0)
    
    # Initialize CLI
    cli = ChatbotCLI(verbose=args.verbose)
    
    # Run in appropriate mode
    if args.query:
        cli.run_single_query(args.query)
    else:
        cli.run_interactive()


if __name__ == "__main__":
    main()