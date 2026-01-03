"""
Filename sanitization for Windows
"""

import re


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    Sanitize a string to be safe for Windows filenames.
    
    Args:
        name: The filename to sanitize
        max_length: Maximum length for the filename
        
    Returns:
        Sanitized filename safe for Windows
    """
    # Replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*~\[\]{}]', '_', name)
    
    # Replace multiple underscores with single
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Strip leading/trailing spaces and underscores
    sanitized = sanitized.strip(' _')
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip(' _')
    
    # Handle empty result
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized
