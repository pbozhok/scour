"""
Dependency Injection Container for the second-hand research agent.

Provides a simple, lightweight DI container for module dependencies
without external dependencies.
"""

from typing import Dict, Type, Any, Callable, Optional, Union
from dataclasses import dataclass


@dataclass
class Binding:
    """Represents a binding between an abstract type and a concrete implementation."""
    abstract: Type
    concrete: Optional[Union[Type, Callable[[], Any]]] = None
    instance: Optional[Any] = None
    singleton: bool = True


class Container:
    """
    Simple dependency injection container.
    
    Supports:
    - Singleton and transient bindings
    - Constructor injection
    - Lazy instantiation
    """
    
    def __init__(self):
        self._bindings: Dict[Type, Binding] = {}
        self._instances: Dict[Type, Any] = {}
    
    def bind(self, abstract: Type, concrete: Optional[Union[Type, Callable[[], Any]]] = None, 
             singleton: bool = True) -> None:
        """
        Bind an abstract type to a concrete implementation.
        
        Args:
            abstract: The abstract type (interface) to bind
            concrete: The concrete implementation (class or factory function)
            singleton: If True, reuse the same instance; if False, create new instance each time
        """
        if concrete is None:
            concrete = abstract
        
        self._bindings[abstract] = Binding(
            abstract=abstract,
            concrete=concrete,
            singleton=singleton
        )
    
    def bind_instance(self, abstract: Type, instance: Any) -> None:
        """
        Bind an abstract type to a pre-created instance.
        
        Args:
            abstract: The abstract type
            instance: The instance to use
        """
        self._bindings[abstract] = Binding(
            abstract=abstract,
            instance=instance,
            singleton=True
        )
    
    def get(self, abstract: Type, **kwargs) -> Any:
        """
        Get an instance of the requested type.
        
        Args:
            abstract: The abstract type to resolve
            **kwargs: Optional constructor arguments
            
        Returns:
            An instance of the requested type
            
        Raises:
            KeyError: If no binding exists for the type
        """
        if abstract not in self._bindings:
            raise KeyError(f"No binding found for {abstract}")
        
        binding = self._bindings[abstract]
        
        # If we have a pre-created instance, return it
        if binding.instance is not None:
            return binding.instance
        
        # Check if we already have a singleton instance
        if binding.singleton and abstract in self._instances:
            return self._instances[abstract]
        
        # Create a new instance
        if binding.concrete is None:
            instance = abstract(**kwargs)
        elif callable(binding.concrete) and not isinstance(binding.concrete, type):
            # It's a factory function
            instance = binding.concrete()
        else:
            # It's a class
            instance = binding.concrete(**kwargs)
        
        # Cache singleton instances
        if binding.singleton:
            self._instances[abstract] = instance
        
        return instance
    
    def get_all(self, abstract: Type) -> list:
        """
        Get all instances registered under a type.
        
        Useful when multiple implementations are bound to the same abstract type.
        
        Args:
            abstract: The abstract type
            
        Returns:
            List of all instances bound to this type
        """
        # This is a simplified approach - for full multi-binding support,
        # we'd need to track multiple bindings per type
        if abstract not in self._bindings:
            return []
        
        binding = self._bindings[abstract]
        if binding.instance is not None:
            return [binding.instance]
        
        # For singleton, return the cached instance
        if binding.singleton and abstract in self._instances:
            return [self._instances[abstract]]
        
        # Create new instance
        if binding.concrete is None:
            instance = abstract()
        elif callable(binding.concrete) and not isinstance(binding.concrete, type):
            instance = binding.concrete()
        else:
            instance = binding.concrete()
        
        if binding.singleton:
            self._instances[abstract] = instance
        
        return [instance]
    
    def resolve(self, abstract: Type) -> Any:
        """
        Alias for get() - resolve a dependency.
        
        Args:
            abstract: The abstract type to resolve
            
        Returns:
            An instance of the requested type
        """
        return self.get(abstract)
    
    def unbind(self, abstract: Type) -> bool:
        """
        Remove a binding.
        
        Args:
            abstract: The abstract type to unbind
            
        Returns:
            True if binding was removed, False if it didn't exist
        """
        if abstract in self._bindings:
            del self._bindings[abstract]
            return True
        return False
    
    def clear_cache(self) -> None:
        """Clear all cached singleton instances."""
        self._instances.clear()
    
    def has_binding(self, abstract: Type) -> bool:
        """Check if a binding exists for a type."""
        return abstract in self._bindings


# Global container instance
container = Container()


def register_llm_providers(container_instance: Container = None) -> None:
    """
    Register LLM providers with the DI container.
    
    This allows modules to request LLM clients by name via dependency injection.
    
    Args:
        container_instance: The container to register with (defaults to global container)
    """
    target_container = container_instance if container_instance is not None else container
    
    # Import here to avoid circular imports
    from llm.base import BaseLLMClient
    from llm.client import get_client, LLMClient
    from config import LLM_PROVIDERS
    
    # Register the factory function for BaseLLMClient
    # When someone requests BaseLLMClient, we'll need to know which backend
    # For now, we register the get_client factory
    # Individual modules will call get_client() with their configured backend
    
    # Register LLMClient as the abstract type
    target_container.bind(BaseLLMClient, concrete=get_client)
    target_container.bind(LLMClient, concrete=get_client)


# Note: register_llm_providers() is called manually to avoid circular imports
# Call this function after all modules are imported if needed
