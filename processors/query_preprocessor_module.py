"""
Query preprocessor module - cleans and expands search queries.

Implements Module interface for the modular pipeline.
"""

from typing import List, Dict, Any
from rich.console import Console

from core.module import Module, ModuleType, PipelineContext
from core.logging import get_logger
from processors.query_preprocessor import QueryPreprocessor

console = Console()
logger = get_logger(__name__, module_name="processors.query_preprocessor_module")


class QueryPreprocessorModule(Module):
    """Pre-processes user queries to generate optimized search keywords."""
    
    name = "query-preprocessor"
    module_type = ModuleType.PREPROCESSOR
    version = "1.0.0"
    
    def __init__(self, llm_backend: str = "gemini", debug: bool = False):
        """
        Initialize the preprocessor.
        
        Args:
            llm_backend: The LLM backend to use (gemini or mistral)
            debug: Whether to print debug information
        """
        self.llm_backend = llm_backend
        self.debug = debug
        self._preprocessor = None
        self._initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization succeeded
        """
        self._initialized = True
        self.llm_backend = config.get("llm_backend", "gemini")
        self.debug = config.get("debug", False)
        
        try:
            from llm import get_client
            llm_client = get_client(self.llm_backend)
            self._preprocessor = QueryPreprocessor(llm_client=llm_client, debug=self.debug)
            logger.info("QueryPreprocessorModule initialized", extra={"llm_backend": self.llm_backend})
            return True
        except Exception as e:
            logger.error("Failed to initialize QueryPreprocessorModule", extra={"error": str(e)})
            return False
    
    def validate(self) -> bool:
        """
        Validate the module is properly configured.
        
        Returns:
            True if valid
        """
        return self._initialized and self._preprocessor is not None
    
    def cleanup(self) -> None:
        """Clean up any resources."""
        self._initialized = False
        self._preprocessor = None
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the query preprocessor module.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context with cleaned query and search queries
        """
        if not self._initialized:
            self.initialize(context.config)
        
        try:
            # Clean the query
            cleaned_query = self._preprocessor.clean_query(context.query)
            
            # Generate search queries
            max_keywords = context.config.get("max_keywords", 8)
            # Generate max_keywords - 1 additional keywords, then prepend cleaned query
            # This ensures total search queries = max_keywords
            additional_keywords = max_keywords - 1
            keywords = await self._preprocessor.generate_keywords(context.query, max_keywords=additional_keywords)
            
            # Build search queries: cleaned query + generated keywords
            search_queries = [cleaned_query] + keywords
            
            # Store in metadata
            context.set_metadata("cleaned_query", cleaned_query)
            context.set_metadata("search_queries", search_queries)
            context.set_metadata("original_query", context.query)
            
            # Update the query to use the cleaned version
            context.query = cleaned_query
            
            if self.debug:
                console.print(f"[blue]Preprocessor: {context.query} -> {cleaned_query}[/blue]")
                console.print(f"[blue]Search queries: {search_queries}[/blue]")
            
        except Exception as e:
            context.add_error(
                module_name=self.name,
                error_type="PREPROCESSOR_ERROR",
                message=str(e),
                context={"query": context.query}
            )
        
        return context
    
    def clean_query(self, query: str) -> str:
        """
        Clean and normalize a user query.
        
        Args:
            query: Raw user query
            
        Returns:
            Cleaned query string
        """
        if self._preprocessor:
            return self._preprocessor.clean_query(query)
        return query
    
    async def generate_search_queries(self, query: str, max_keywords: int = 8) -> List[str]:
        """
        Generate search queries from a user query.
        
        Args:
            query: The user's query
            max_keywords: Maximum number of keywords to generate
            
        Returns:
            List of search queries
        """
        if self._preprocessor:
            return await self._preprocessor.generate_search_queries(query, max_keywords)
        return [query]
