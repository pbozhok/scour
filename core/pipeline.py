"""
Module Pipeline for the second-hand research agent.

Provides a modular, extensible pipeline that processes queries through
a series of modules (scrapers, filters, processors, reviewers).
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Type
from dataclasses import dataclass, field

from core.module import Module, ModuleType, PipelineContext, PipelineError
from core.registry import ModuleRegistry, registry as global_registry
from core.logging import get_logger

logger = get_logger(__name__, module_name="core.pipeline")


@dataclass
class PipelineConfig:
    """Configuration for the pipeline execution."""
    query: str
    max_results: int = 20
    max_keywords: int = 8
    target_currency: str = "EUR"
    llm_backend: str = "gemini"
    skip_preprocess: bool = False
    skip_filter: bool = False
    skip_score: bool = False
    skip_reviews: bool = False
    debug: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for PipelineContext."""
        return {
            "query": self.query,
            "max_results": self.max_results,
            "max_keywords": self.max_keywords,
            "target_currency": self.target_currency,
            "llm_backend": self.llm_backend,
            "skip_preprocess": self.skip_preprocess,
            "skip_filter": self.skip_filter,
            "skip_score": self.skip_score,
            "skip_reviews": self.skip_reviews,
            "debug": self.debug,
        }


class Pipeline:
    """
    Orchestrates the execution of modules in the research pipeline.
    
    The pipeline processes a query through these stages in order:
    1. Pre-processing (optional): Query cleaning and keyword generation
    2. Scraping: Fetch listings from multiple platforms
    3. Processing: Price conversion, deduplication
    4. Filtering (1st pass): Keyword or LLM-based relevance filtering
    5. Processing: Description fetching
    6. Filtering (2nd pass): LLM-based filtering with full descriptions
    7. Processing: Model extraction
    8. Review aggregation: Fetch and summarize reviews
    9. Scoring: LLM-based ranking
    
    Each stage is implemented by one or more modules.
    """
    
    def __init__(self, registry: Optional[ModuleRegistry] = None):
        """
        Initialize the pipeline.
        
        Args:
            registry: Module registry to use (defaults to global registry)
        """
        self.registry = registry or global_registry
        self._modules: Dict[ModuleType, List[Module]] = {}
        self._preprocessor = None  # Query preprocessor (optional)
    
    def load_modules(self) -> None:
        """Load all modules from the registry."""
        self._modules = {}
        for module_type in ModuleType:
            modules = self.registry.get_modules(module_type)
            if modules:
                self._modules[module_type] = modules
        
        # Separately get preprocessor (only one expected)
        preprocessors = self.registry.get_modules(ModuleType.PREPROCESSOR)
        if preprocessors:
            self._preprocessor = preprocessors[0]
    
    async def execute(self, config: PipelineConfig) -> PipelineContext:
        """
        Execute the full pipeline with the given configuration.
        
        Args:
            config: Pipeline configuration
            
        Returns:
            PipelineContext with all results and metadata
        """
        # Create initial context
        context = PipelineContext(
            query=config.query,
            listings=[],
            config=config.to_dict(),
            errors=[],
            metadata={"pipeline_start": "start"}
        )
        
        logger.info("Pipeline started", extra={"query": config.query})
        
        try:
            # Load modules if not already loaded
            if not self._modules:
                self.load_modules()
            
            # Stage 0: Pre-processing (optional) - generates cleaned query and search keywords
            if not config.skip_preprocess and self._preprocessor:
                context = await self._execute_preprocessor(context)
                logger.info("Query pre-processed", extra={"original_query": context.get_metadata("original_query"), "cleaned_query": context.query})
            
            # Stage 1: Scraping - fetch listings from all platforms
            context = await self._execute_stage(ModuleType.SCRAPER, context)
            logger.info("Scraping complete", extra={"listing_count": len(context.listings)})
            
            # Stage 2: Processing - price conversion and deduplication only
            context = await self._execute_price_converters(context)
            context = await self._execute_deduplicators(context)
            logger.info("Prices converted and duplicates removed", extra={"listing_count": len(context.listings)})
            
            # Stage 3: Filtering (1st pass) - initial relevance filtering
            # When skip_filter=True, use keyword filter; otherwise use LLM filter
            context = await self._execute_filter_pass(context, use_llm=not config.skip_filter, pass_num=1)
            logger.info("First filtering pass complete", extra={"listing_count": len(context.listings)})
            
            # Stage 4: Processing - fetch descriptions for relevant items
            # Run only description fetcher, not all processors
            context = await self._execute_description_fetchers(context)
            logger.info("Descriptions fetched", extra={"listing_count": len(context.listings)})
            
            # Stage 5: Filtering (2nd pass) - filtering with full descriptions
            # Use the same filter type as pass 1
            context = await self._execute_filter_pass(context, use_llm=not config.skip_filter, pass_num=2)
            logger.info("Second filtering pass complete", extra={"listing_count": len(context.listings)})
            
            # Stage 6: Processing - extract product models
            context = await self._execute_model_extractors(context)
            logger.info("Product models extracted", extra={"listing_count": len(context.listings)})
            
            # Stage 7: Review aggregation - fetch and summarize reviews
            if not config.skip_reviews:
                context = await self._execute_stage(ModuleType.REVIEWER, context)
                logger.info("Reviews aggregated", extra={"listing_count": len(context.listings)})
            else:
                logger.info("Reviews skipped (--no-reviews flag)")
            
            # Stage 8: Scoring/Ranking - score and rank listings
            if not config.skip_score:
                context = await self._execute_stage(ModuleType.RANKER, context)
                logger.info("Listings scored and ranked", extra={"listing_count": len(context.listings)})
            else:
                logger.info("Scoring skipped (--no-score flag)")
            
            logger.info("Pipeline completed", 
                       extra={"final_listing_count": len(context.listings), "error_count": len(context.errors)})
            
        except Exception as e:
            logger.error("Pipeline failed", extra={"error": str(e), "error_type": type(e).__name__})
            context.add_error(
                module_name="pipeline",
                error_type="PIPELINE_ERROR",
                message=str(e)
            )
        
        return context
    
    async def _execute_preprocessor(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the query preprocessor to clean and expand the query.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context with preprocessed query and search queries
        """
        if not self._preprocessor:
            return context
        
        try:
            # Initialize if needed
            if not hasattr(self._preprocessor, '_initialized') or not self._preprocessor._initialized:
                self._preprocessor.initialize(context.config)
            
            # Execute the preprocessor module
            context = await self._preprocessor.execute(context)
            
        except Exception as e:
            context.add_error(
                module_name="preprocessor",
                error_type="PREPROCESSOR_ERROR",
                message=str(e),
                context={"query": context.query}
            )
        
        return context
    
    async def _execute_description_fetchers(self, context: PipelineContext) -> PipelineContext:
        """
        Execute only the description fetcher processors.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context
        """
        modules = self._modules.get(ModuleType.PROCESSOR, [])
        for module in modules:
            if module.name == "description-fetcher":
                try:
                    if not hasattr(module, '_initialized') or not module._initialized:
                        module.initialize(context.config)
                    context = await module.execute(context)
                except Exception as e:
                    logger.error("Description fetcher failed", extra={"error": str(e)})
                    context.add_error(
                        module_name=module.name,
                        error_type="PROCESSOR_ERROR",
                        message=str(e)
                    )
        return context
    
    async def _execute_model_extractors(self, context: PipelineContext) -> PipelineContext:
        """
        Execute only the model extractor processors.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context
        """
        modules = self._modules.get(ModuleType.PROCESSOR, [])
        for module in modules:
            if module.name == "model-extractor":
                try:
                    if not hasattr(module, '_initialized') or not module._initialized:
                        module.initialize(context.config)
                    context = await module.execute(context)
                except Exception as e:
                    logger.error("Model extractor failed", extra={"error": str(e)})
                    context.add_error(
                        module_name=module.name,
                        error_type="PROCESSOR_ERROR",
                        message=str(e)
                    )
        return context
    
    async def _execute_price_converters(self, context: PipelineContext) -> PipelineContext:
        """
        Execute only the price converter processors.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context
        """
        modules = self._modules.get(ModuleType.PROCESSOR, [])
        for module in modules:
            if module.name == "price-converter":
                try:
                    if not hasattr(module, '_initialized') or not module._initialized:
                        module.initialize(context.config)
                    context = await module.execute(context)
                except Exception as e:
                    logger.error("Price converter failed", extra={"error": str(e)})
                    context.add_error(
                        module_name=module.name,
                        error_type="PROCESSOR_ERROR",
                        message=str(e)
                    )
        return context
    
    async def _execute_deduplicators(self, context: PipelineContext) -> PipelineContext:
        """
        Execute only the deduplicator processors.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context
        """
        modules = self._modules.get(ModuleType.PROCESSOR, [])
        for module in modules:
            if module.name == "deduplicator":
                try:
                    if not hasattr(module, '_initialized') or not module._initialized:
                        module.initialize(context.config)
                    context = await module.execute(context)
                except Exception as e:
                    logger.error("Deduplicator failed", extra={"error": str(e)})
                    context.add_error(
                        module_name=module.name,
                        error_type="PROCESSOR_ERROR",
                        message=str(e)
                    )
        return context
    
    async def _execute_filter_pass(self, context: PipelineContext, use_llm: bool = True, pass_num: int = 1) -> PipelineContext:
        """
        Execute a single filter pass with the appropriate filter type.
        
        Args:
            context: The pipeline context
            use_llm: If True, use LLM filter; if False, use keyword filter
            pass_num: Which pass number (for logging)
            
        Returns:
            Modified context with filtered listings
        """
        modules = self._modules.get(ModuleType.FILTER, [])
        filter_module = None
        filter_type = "LLM" if use_llm else "keyword"
        
        # Select the appropriate filter
        if use_llm:
            for module in modules:
                if module.name == "llm-filter":
                    filter_module = module
                    break
        else:
            for module in modules:
                if module.name == "keyword-filter":
                    filter_module = module
                    break
        
        if filter_module:
            try:
                if not hasattr(filter_module, '_initialized') or not filter_module._initialized:
                    filter_module.initialize(context.config)
                context = await filter_module.execute(context)
                logger.info("Filter pass {} completed", extra={"pass_num": pass_num, "filter_type": filter_type})
            except Exception as e:
                logger.error("Filter pass {} failed", extra={"pass_num": pass_num, "filter_type": filter_type, "error": str(e)})
                context.add_error(
                    module_name=filter_module.name,
                    error_type="FILTER_ERROR",
                    message=str(e)
                )
        else:
            logger.warning("No filter module found", extra={"use_llm": use_llm, "pass_num": pass_num})
        
        return context
    
    async def _execute_stage(self, module_type: ModuleType, context: PipelineContext) -> PipelineContext:
        """
        Execute all modules of a specific type.
        
        Args:
            module_type: The type of modules to execute
            context: The pipeline context
            
        Returns:
            Updated pipeline context
        """
        modules = self._modules.get(module_type, [])
        
        if not modules:
            logger.debug("No modules for stage", stage=module_type.value)
            return context
        
        logger.info("Executing stage", extra={"stage": module_type.value, "module_count": len(modules)})
        
        # Execute all modules of this type
        for module in modules:
            try:
                logger.debug("Executing module", extra={"module_name": module.name, "module_type": module.module_type.value})
                
                # Initialize module if not already done
                if not hasattr(module, '_initialized') or not module._initialized:
                    module.initialize(context.config)
                
                # Execute the module
                context = await module.execute(context)
                
                logger.debug("Module completed", extra={"module_name": module.name, "listing_count": len(context.listings), "error_count": len(context.errors)})
                
            except Exception as e:
                logger.error("Module failed", extra={"module_name": module.name, "error": str(e)})
                context.add_error(
                    module_name=module.name,
                    error_type=f"{module.module_type.value}_ERROR",
                    message=str(e),
                    severity="ERROR"
                )
        
        return context
    
    async def execute_module(self, module: Module, context: PipelineContext) -> PipelineContext:
        """
        Execute a single module.
        
        Args:
            module: The module to execute
            context: The pipeline context
            
        Returns:
            Updated pipeline context
        """
        logger.debug("Executing single module", module_name=module.name)
        
        try:
            # Initialize if needed
            if not hasattr(module, '_initialized') or not module._initialized:
                module.initialize(context.config)
            
            context = await module.execute(context)
            
        except Exception as e:
            logger.error("Module execution failed", module_name=module.name, error=str(e))
            context.add_error(
                module_name=module.name,
                error_type=f"{module.module_type.value}_ERROR",
                message=str(e)
            )
        
        return context


def create_pipeline(config: Optional[PipelineConfig] = None) -> Pipeline:
    """
    Factory function to create a pipeline with optional configuration.
    
    Args:
        config: Optional pipeline configuration
        
    Returns:
        Configured Pipeline instance
    """
    return Pipeline()
