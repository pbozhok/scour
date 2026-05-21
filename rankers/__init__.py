"""
Rankers module - scoring and ranking implementations.

This module provides ranking functionality for the second-hand research agent.
All rankers inherit from Module which implements the Module interface.

Available rankers:
- RankerModule: Scores and ranks listings based on multiple factors

Usage:
    from rankers import RankerModule
"""

from .ranker_module import RankerModule

# Auto-register ranker with the global registry
from core.registry import registry

try:
    registry.register(RankerModule())
except:
    pass

__all__ = ["RankerModule"]
