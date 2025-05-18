"""
Command line parameters management for the Document Loader application.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import click
from threading import local


# Thread-local storage for CLI params
_params_store = local()


@dataclass
class CommandLineParams:
    """Container for all command line parameters used across the application."""
    
    # Global flags
    verbose: bool = False
    log_level: str = "INFO"
    
    # Command-specific parameters
    kb_name: Optional[str] = None
    source_type: Optional[str] = None
    source_config: Optional[Dict[str, Any]] = None
    rag_type: Optional[str] = None
    rag_config: Optional[Dict[str, Any]] = None
    path: Optional[str] = None
    recursive: bool = True
    table: bool = False
    update_db: bool = False
    limit: int = 10
    run_once: bool = False
    no_schema: bool = False
    create_db: bool = False
    
    # Raw command line arguments
    raw_args: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, **kwargs):
        """Update parameters with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            self.raw_args[key] = value
    
    @classmethod
    def from_context(cls, ctx: click.Context) -> 'CommandLineParams':
        """Create CommandLineParams from Click context."""
        params = cls()
        
        # Extract global options from parent contexts
        while ctx:
            if ctx.params:
                params.update(**ctx.params)
            ctx = ctx.parent
            
        return params
    
    def get_log_level(self) -> str:
        """Get the effective log level based on verbose flag."""
        if self.verbose:
            return "DEBUG"
        return self.log_level


def init_params(ctx: click.Context) -> CommandLineParams:
    """Initialize parameters from Click context and store in thread-local."""
    params = CommandLineParams.from_context(ctx)
    _params_store.params = params
    return params


def get_params() -> CommandLineParams:
    """Get the current command line parameters."""
    if not hasattr(_params_store, 'params'):
        # If not initialized, return default params
        _params_store.params = CommandLineParams()
    return _params_store.params


def update_params(**kwargs):
    """Update current parameters with new values."""
    params = get_params()
    params.update(**kwargs)