"""
Utility functions for JSON extraction, price parsing, and text processing.
"""

import json
import re
from typing import Any, Optional


def extract_json(text: str) -> Optional[dict | list]:
    """
    Robustly extract JSON from a model response that may include
    markdown fences or surrounding prose.
    
    Args:
        text: The text potentially containing JSON
        
    Returns:
        Parsed JSON object/list or None if extraction fails
    """
    # Try to extract from markdown fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        text = fenced.group(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON by braces/brackets
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    return None


def parse_price(text: str) -> float:
    """
    Extract price amount from text like '4999 kr', '3.200 kr', '3 200 kr', '900 SEK', etc.
    Handles Danish/European number formats where . is thousand separator and , is decimal.
    
    Args:
        text: The text containing price information
        
    Returns:
        The parsed price as a float, or 0.0 if no valid price found
    """
    if not text:
        return 0.0
    
    text = text.strip()
    
    # Try to match pattern: digits (with optional separators) followed by kr/dkk/sek/eur
    # First try with currency symbol (more specific)
    match = re.search(r'(\d{1,3}[\.\s,])*\d+(?:[.,]\d{1,2})?\s*(?:kr|dkk|sek|eur|€|\$)', text, re.IGNORECASE)
    if not match:
        # Try without requiring currency
        match = re.search(r'(\d{1,3}[\.\s,])*\d+(?:[.,]\d{1,2})?', text)
    if match:
        # Extract the matched number part
        price_str = match.group(0)
        # Remove currency designations - keep digits, dots, commas, spaces
        price_str = re.sub(r'[^\d\.\,\s]', '', price_str)
        
        # Remove all whitespace (including non-breaking spaces, thin spaces, etc.)
        price_str = re.sub(r'\s', '', price_str)
        
        # Handle Danish format: dots are thousand separators, comma is decimal
        # If we have both dots and commas, dots are thousand separators
        if '.' in price_str and ',' in price_str:
            # Remove thousand separators (dots), keep comma as decimal
            price_str = price_str.replace('.', '')
            # Replace comma with dot for float parsing
            price_str = price_str.replace(',', '.')
        elif '.' in price_str:
            # Could be thousand separator (Danish: 12.999 = 12999) or decimal (12.99)
            # If we have multiple dots, they're thousand separators
            dots = price_str.count('.')
            if dots > 1:
                price_str = price_str.replace('.', '')
            elif ',' in price_str:
                # Has both dot and comma - dot is thousand separator
                price_str = price_str.replace('.', '')
                price_str = price_str.replace(',', '.')
            else:
                # Single dot - could be thousand separator or decimal
                # In Danish context, assume it's a thousand separator if the part before dot is 1-3 digits
                # and part after is 3 digits (e.g., "12.999")
                parts = price_str.split('.')
                if len(parts) == 2 and len(parts[0]) <= 3 and len(parts[1]) == 3:
                    # Likely thousand separator: 12.999 = 12999
                    price_str = parts[0] + parts[1]
        elif ',' in price_str:
            # Comma is decimal separator
            price_str = price_str.replace(',', '.')
        
        try:
            return float(price_str) if price_str else 0.0
        except ValueError:
            pass
    
    # Fallback: if no number found, try to extract all numbers and use the largest
    numbers = re.findall(r'\d+', text)
    if numbers:
        return float(max(numbers))
    
    return 0.0


def normalize_model_name(model_name: str) -> str:
    """
    Normalize a product model name for de-duplication.
    Converts variations like "Pixel 9a", "Pixel 9A", "Google Pixel 9a" to a canonical form.
    
    Rules:
    - Convert to lowercase
    - Remove common manufacturer prefixes (google, apple, samsung, etc.)
    - Remove special characters and extra whitespace
    - Normalize spaces and common abbreviations
    
    Args:
        model_name: The model name to normalize
        
    Returns:
        Normalized model name string
    """
    if not model_name:
        return ""
    
    name = model_name.strip().lower()
    
    # Remove common manufacturer prefixes that don't affect model identity
    # These are manufacturers that users might or might not include
    # Note: We don't remove "pixel" as it's the brand name itself
    manufacturer_prefixes = [
        'google ', 'apple ', 'samsung ', 'sony ', 'lg ', 'motorola ', 'oneplus ',
        'xiaomi ', 'huawei ', 'oppo ', 'vivo ', 'realme ', 'nokia ',
        'asus ', 'acer ', 'lenovo ', 'hp ', 'dell ', 'msi ',
    ]
    
    for prefix in manufacturer_prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
    
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Remove common punctuation that doesn't affect model identity
    name = re.sub(r'[\-\(\)\,;:]/?\s*', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Normalize common variations
    # e.g., "9a" vs "9 a" vs "9-A"
    name = re.sub(r'(\d)\s+([a-z])', r'\1\2', name)  # "9 a" -> "9a"
    name = re.sub(r'(\d)-([a-z])', r'\1\2', name)     # "9-a" -> "9a"
    
    # Normalize "pro max" vs "promax" etc.
    name = re.sub(r'(\w)\s+(\w)', r'\1\2', name)  # "pro max" -> "promax"
    
    # Normalize specific known patterns
    name = re.sub(r'iphone(\d+)', r'iphone\1', name)
    name = re.sub(r'galaxy[s\s]*(\w+)', r'galaxys\1', name)
    
    return name.strip()
