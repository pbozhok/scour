"""
Module Registry for the second-hand research agent.

Provides automatic discovery, registration, and lifecycle management
for all pipeline modules (scrapers, filters, processors, reviewers, LLM clients).
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type, Any

from core.module import Module, ModuleType, PipelineError


class ModuleRegistry:
    """
    Central registry for all pipeline modules.
    
    Provides:
    - Automatic module discovery from designated directories
    - Module registration and lifecycle management
    - Module retrieval by name or type
    - Validation of all registered modules
    """
    
    def __init__(self):
        self._modules: Dict[str, Module] = {}
        self._modules_by_type: Dict[ModuleType, List[Module]] = {}
        self._discovery_paths: Dict[ModuleType, str] = {
            ModuleType.PREPROCESSOR: "",  # Preprocessors are registered manually
            ModuleType.SCRAPER: "scrapers",
            ModuleType.PROCESSOR: "processors",
            ModuleType.FILTER: "filters",
            ModuleType.REVIEWER: "reviewers",
            ModuleType.RANKER: "rankers",
            ModuleType.LLM: "llm",
        }
        # Initialize modules_by_type with empty lists for all types
        for t in ModuleType:
            self._modules_by_type[t] = []
    
    def register(self, module: Module) -> None:
        """
        Register a module with the registry.
        
        Args:
            module: The module instance to register
            
        Raises:
            ValueError: If module name is not unique
        """
        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' is already registered")
        
        self._modules[module.name] = module
        self._modules_by_type[module.module_type].append(module)
    
    def unregister(self, module_name: str) -> bool:
        """
        Unregister a module by name.
        
        Args:
            module_name: The name of the module to unregister
            
        Returns:
            True if module was found and unregistered, False otherwise
        """
        if module_name not in self._modules:
            return False
        
        module = self._modules.pop(module_name)
        self._modules_by_type[module.module_type].remove(module)
        return True
    
    def get_module(self, module_name: str) -> Optional[Module]:
        """
        Get a registered module by name.
        
        Args:
            module_name: The name of the module
            
        Returns:
            The module instance, or None if not found
        """
        return self._modules.get(module_name)
    
    def get_modules(self, module_type: Optional[ModuleType] = None) -> List[Module]:
        """
        Get all registered modules, optionally filtered by type.
        
        Args:
            module_type: Optional module type filter
            
        Returns:
            List of module instances
        """
        if module_type is not None:
            return list(self._modules_by_type.get(module_type, []))
        return list(self._modules.values())
    
    def load_all(self) -> Dict[str, List[str]]:
        """
        Discover and load all modules from designated directories.
        
        Returns:
            Dictionary mapping module type to list of loaded module names
        """
        loaded = {}
        
        for module_type, directory in self._discovery_paths.items():
            if not directory:
                continue
            
            module_names = self._discover_modules_in_directory(directory, module_type)
            loaded[module_type.value] = module_names
            
            for name in module_names:
                try:
                    module = self._import_module(directory, name, module_type)
                    if module:
                        self.register(module)
                except Exception as e:
                    # Log error but continue with other modules
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to load module {name} from {directory}: {e}")
        
        return loaded
    
    def _discover_modules_in_directory(self, directory: str, module_type: ModuleType) -> List[str]:
        """
        Discover all Python modules in a directory.
        
        Args:
            directory: The directory path (relative to project root)
            module_type: The expected module type
            
        Returns:
            List of module names (without .py extension)
        """
        modules = []
        
        try:
            path = Path(directory)
            if not path.exists():
                return modules
            
            for finder, name, ispkg in pkgutil.iter_modules([str(path)]):
                if not ispkg and name != "__init__":
                    modules.append(name)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to discover modules in {directory}: {e}")
        
        return modules
    
    def _import_module(self, directory: str, module_name: str, module_type: ModuleType) -> Optional[Module]:
        """
        Import and instantiate a module from a directory.
        
        Args:
            directory: The directory path
            module_name: The module name (without .py)
            module_type: The expected module type
            
        Returns:
            Module instance if successfully imported and instantiated, None otherwise
        """
        try:
            # Import the module
            module = importlib.import_module(f"{directory}.{module_name}")
            
            # Find the first class that inherits from Module
            for name, obj in vars(module).items():
                if (
                    isinstance(obj, type) 
                    and issubclass(obj, Module) 
                    and obj is not Module
                ):
                    # Instantiate and return
                    instance = obj()
                    return instance
            
            return None
            
        except ImportError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to import {directory}.{module_name}: {e}")
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error importing {directory}.{module_name}: {e}")
            return None
    
    def validate_all(self) -> List[str]:
        """
        Validate all registered modules.
        
        Returns:
            List of error messages for invalid modules (empty if all valid)
        """
        errors = []
        
        for name, module in self._modules.items():
            try:
                if not module.validate():
                    errors.append(f"{name}: validation failed")
            except Exception as e:
                errors.append(f"{name}: validation error - {e}")
        
        return errors
    
    def get_module_class(self, module_name: str) -> Optional[Type[Module]]:
        """
        Get the class of a registered module.
        
        Args:
            module_name: The name of the module
            
        Returns:
            The module class, or None if not found
        """
        module = self.get_module(module_name)
        if module:
            return type(module)
        return None


# Global registry instance
registry = ModuleRegistry()
