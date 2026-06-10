"""
Query pre-processor: generates multiple search keywords from a natural language user query.

This module converts user intent like "I want a powerful cheap phone" into
a list of search keywords like ["phone", "iphone", "android", "smartphone"]
that can be used to search on second-hand platforms.

The original user query is preserved for filtering/scoring to ensure
listings match the actual intent, not just the generated keywords.
"""

import re
from typing import Optional

from config import DEFAULT_MAX_KEYWORDS
from llm.client import LLMClient
from utils import extract_json


class QueryPreprocessor:
    """
    Pre-processes user queries to generate optimized search keywords.
    
    Uses LLM to understand user intent and generate relevant search terms
    that will be used on second-hand platforms. The original query is
    retained for the filtering and scoring stages.
    """
    
    def __init__(self, llm_client: LLMClient = None, debug: bool = False):
        """
        Initialize the query preprocessor.
        
        Args:
            llm_client: LLM client instance to use (optional, can be set later)
            debug: Whether to print debug information
        """
        self.llm_client = llm_client
        self.debug = debug
    
    def set_llm_client(self, llm_client: LLMClient):
        """Set the LLM client to use."""
        self.llm_client = llm_client
    
    def clean_query(self, query: str) -> str:
        """
        Clean and normalize a user query.
        
        Removes common prefixes and normalizes whitespace.
        
        Args:
            query: Raw user query
            
        Returns:
            Cleaned query string
        """
        # Normalize whitespace first
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Remove common prefixes in order of specificity
        # First, multi-word prefixes
        query = re.sub(
            r'^(i\s+(want|need|am\s+looking\s+for|would\s+like|search\s+for)\s*)',
            '',
            query,
            flags=re.IGNORECASE
        )
        query = re.sub(
            r'^(find\s+me\s*|get\s+me\s*|show\s+me\s*|where\s+can\s+i\s+find\s*)',
            '',
            query,
            flags=re.IGNORECASE
        )
        # Then single-word articles
        query = re.sub(
            r'^(a|an|the|some)\s+',
            '',
            query,
            flags=re.IGNORECASE
        )
        # Remove leading punctuation and whitespace
        query = re.sub(r'^[\s\-\?\!\.]+', '', query).strip()
        
        return query
    
    async def generate_keywords(self, query: str, max_keywords: int = DEFAULT_MAX_KEYWORDS) -> list[str]:
        """
        Generate search keywords from a user query using LLM.
        
        Takes a natural language query and generates multiple keywords
        that capture the user's intent. These keywords can be used
        individually or combined for searching on second-hand platforms.
        
        Args:
            query: The user's natural language query
            max_keywords: Maximum number of keywords to generate
            
        Returns:
            List of generated search keywords
            
        Example:
            Input: "I want a powerful cheap phone"
            Output: ["phone", "smartphone", "iphone", "android", 
                     "samsung galaxy", "cheap phone", "budget smartphone"]
        """
        if self.llm_client is None:
            from llm import get_client
            self.llm_client = get_client("gemini")
        
        cleaned_query = self.clean_query(query)
        
        prompt = f"""You are a shopping search assistant. The user wants to find second-hand items.

User query: "{cleaned_query}"

Your task: Generate search keywords that would be effective for finding
what the user wants on second-hand marketplaces (like DBA, Vinted, Tradera).

Guidelines:
- Generate {max_keywords} different search terms/keywords
- Include the main product category (e.g., "phone", "laptop")
- Include specific brands or models if mentioned or implied
- Include variations and synonyms (e.g., "phone" and "smartphone")
- Include related terms that capture the user's intent
- Keep keywords short (1-4 words each)
- ONLY use lowercase
- Do NOT include prices, colors, or very specific attributes
- Focus on what the user wants to buy, not where or how

Return ONLY a JSON object with this exact format:
{{"keywords": ["keyword1", "keyword2", ...]}}

Example:
If user query is "I need a good used laptop for work", output:
{{"keywords": ["laptop", "notebook", "macbook", "dell laptop", "hp laptop", "lenovo thinkpad", "business laptop", "used laptop", "work laptop", "office laptop"]}}

Now generate keywords for the user query:"""
        
        try:
            raw_response = await self.llm_client.chat(prompt, temperature=0.3, max_retries=3)
            
            # Try to extract JSON from response
            if self.debug:
                print(f"[debug] LLM response: {raw_response[:200]}...")

            parsed = extract_json(raw_response)
            
            if isinstance(parsed, dict) and "keywords" in parsed:
                keywords = parsed["keywords"]
                # Clean and filter keywords
                keywords = [self._clean_keyword(k) for k in keywords if self._clean_keyword(k)]
                # Deduplicate while preserving order (case-insensitive)
                seen = set()
                unique_keywords = []
                for kw in keywords:
                    kw_lower = kw.lower()
                    if kw_lower not in seen:
                        seen.add(kw_lower)
                        unique_keywords.append(kw)
                # Limit to max_keywords
                return unique_keywords[:max_keywords]
            elif isinstance(parsed, list):
                # If response is just a list
                keywords = [self._clean_keyword(k) for k in parsed if self._clean_keyword(k)]
                seen = set()
                unique_keywords = []
                for kw in keywords:
                    kw_lower = kw.lower()
                    if kw_lower not in seen:
                        seen.add(kw_lower)
                        unique_keywords.append(kw)
                return unique_keywords[:max_keywords]
            else:
                # Fallback: try to extract keywords from plain text
                if self.debug:
                    print(f"[debug] Failed to parse JSON, falling back to text extraction")
                return self._extract_keywords_from_text(raw_response, max_keywords)
                
        except Exception as e:
            if self.debug:
                print(f"[debug] Error generating keywords: {e}")
            # Return a simple fallback
            return self._generate_fallback_keywords(query, max_keywords)
    
    def _clean_keyword(self, keyword: str) -> str:
        """Clean a single keyword."""
        if not keyword or not isinstance(keyword, str):
            return ""
        # Convert to lowercase
        keyword = keyword.lower().strip()
        # Remove quotes and other punctuation from edges
        keyword = re.sub(r'^["\'\(\[\{\s]+', '', keyword)
        keyword = re.sub(r'["\'\)\]\}\s]+$', '', keyword)
        # Remove extra whitespace
        keyword = re.sub(r'\s+', ' ', keyword).strip()
        return keyword
    
    def _extract_keywords_from_text(self, text: str, max_keywords: int) -> list[str]:
        """Extract keywords from plain text response."""
        # Try to find lines that look like keywords
        lines = text.split('\n')
        keywords = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines, markdown, etc.
            if not line or line.startswith('```') or line.startswith('**') or line.startswith('---'):
                continue
            if line.startswith(('http://', 'https://')):
                continue
            # If line looks like a list item
            if line.startswith(('- ', '* ', '• ', '  - ', '  * ')):
                keyword = re.sub(r'^[\-\*•\s]+', '', line).strip()
                keyword = self._clean_keyword(keyword)
                if keyword and len(keyword) <= 50:
                    keywords.append(keyword)
            # Also try to extract from comma-separated values
            elif ',' in line and len(line) < 200:
                parts = [p.strip() for p in line.split(',')]
                for part in parts:
                    keyword = self._clean_keyword(part)
                    if keyword and len(keyword) <= 50:
                        keywords.append(keyword)
        
        # Deduplicate and limit (case-insensitive)
        seen = set()
        unique_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique_keywords.append(kw)
        
        return unique_keywords[:max_keywords]
    
    def _generate_fallback_keywords(self, query: str, max_keywords: int) -> list[str]:
        """Generate fallback keywords without LLM."""
        cleaned = self.clean_query(query)
        
        # Split into words
        words = cleaned.split()
        
        # If query is very short, just return it and variations
        if len(words) <= 2:
            return [cleaned]
        
        # Generate simple variations
        keywords = [cleaned]
        
        # Add without common adjectives
        common_adjectives = ['cheap', 'expensive', 'good', 'bad', 'new', 'used', 
                            'powerful', 'fast', 'slow', 'big', 'small',
                            'best', 'worst', 'top', 'high', 'low']
        
        for adj in common_adjectives:
            if adj in words:
                variant = ' '.join([w for w in words if w.lower() != adj])
                if variant and variant not in keywords:
                    keywords.append(variant)
        
        # Add shorter versions
        if len(words) > 2:
            for i in range(1, len(words)):
                variant = ' '.join(words[i:])
                if variant and variant not in keywords:
                    keywords.append(variant)
        
        return keywords[:max_keywords]
    
    async def generate_search_queries(
        self, 
        query: str, 
        max_keywords: int = DEFAULT_MAX_KEYWORDS,
        use_original: bool = True
    ) -> list[str]:
        """
        Generate a list of search queries to use on second-hand platforms.
        
        This is the main method that returns the queries to be used for scraping.
        
        Args:
            query: The user's natural language query
            max_keywords: Maximum number of generated keywords
            use_original: Whether to include the cleaned original query
            
        Returns:
            List of search queries to use for scraping
            
        Example:
            Input: "I want a powerful cheap phone"
            Output: ["powerful cheap phone", "phone", "smartphone", "iphone", ...]
        """
        keywords = await self.generate_keywords(query, max_keywords)
        
        # Include the cleaned original query
        cleaned_original = self.clean_query(query)
        
        # Check if cleaned_original is already in keywords (case-insensitive)
        cleaned_original_lower = cleaned_original.lower()
        has_original = any(kw.lower() == cleaned_original_lower for kw in keywords)
        
        if use_original and not has_original:
            # Prepend the original query
            result = [cleaned_original] + keywords
        else:
            result = keywords
        
        return result


async def preprocess_query(
    query: str,
    llm_backend: str = "gemini",
    max_keywords: int = DEFAULT_MAX_KEYWORDS,
    use_original: bool = True,
    debug: bool = False
) -> tuple[str, list[str]]:
    """
    Convenience function to pre-process a query.
    
    Args:
        query: User's natural language query
        llm_backend: LLM backend to use
        max_keywords: Maximum number of keywords to generate
        use_original: Whether to include cleaned original in results
        debug: Enable debug output
        
    Returns:
        Tuple of (cleaned_original_query, list_of_search_queries)
        
    Example:
        original, queries = await preprocess_query("I want a powerful cheap phone")
        # original = "powerful cheap phone"
        # queries = ["powerful cheap phone", "phone", "smartphone", "iphone", ...]
    """
    from llm import get_client
    llm_client = get_client(llm_backend)
    preprocessor = QueryPreprocessor(llm_client=llm_client, debug=debug)
    cleaned = preprocessor.clean_query(query)
    search_queries = await preprocessor.generate_search_queries(
        query, max_keywords, use_original
    )
    return cleaned, search_queries
