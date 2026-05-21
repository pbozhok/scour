"""
Core module for the second-hand research agent.

Provides the modular architecture foundation:
- Module base classes and interfaces
- Module registry for auto-discovery
- Dependency injection container
- Structured logging
- Pipeline context
"""

from core.module import (
    Module,
    ModuleType,
    PipelineContext,
    PipelineError,
)
from core.registry import ModuleRegistry, registry
from core.injection import Container, container
from core.logging import (
    JSONFormatter,
    setup_logger,
    get_logger,
    get_console_logger,
)
from core.pipeline import Pipeline, PipelineConfig, create_pipeline

__all__ = [
    # Module classes
    'Module',
    'ModuleType',
    'PipelineContext',
    'PipelineError',
    # Pipeline
    'Pipeline',
    'PipelineConfig',
    'create_pipeline',
    # Registry
    'ModuleRegistry',
    'registry',
    # Injection
    'Container',
    'container',
    # Logging
    'JSONFormatter',
    'setup_logger',
    'get_logger',
    'get_console_logger',
]
