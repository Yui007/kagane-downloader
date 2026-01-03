"""
Retry decorator with exponential backoff
"""

import time
from functools import wraps
from typing import Callable, TypeVar, Any

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    delays: tuple[int, ...] = (2, 5, 10),
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator that retries a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delays: Tuple of delay times in seconds for each retry
        exceptions: Tuple of exception types to catch
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = delays[min(attempt, len(delays) - 1)]
                        time.sleep(delay)
                    else:
                        raise
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry state")
        
        return wrapper
    return decorator


class RetryContext:
    """Context manager for retry logic with progress tracking"""
    
    def __init__(
        self, 
        max_retries: int = 3, 
        delays: tuple[int, ...] = (2, 5, 10),
        on_retry: Callable[[int, Exception], None] | None = None
    ):
        self.max_retries = max_retries
        self.delays = delays
        self.on_retry = on_retry
        self.attempt = 0
    
    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            self.attempt = attempt
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.delays[min(attempt, len(self.delays) - 1)]
                    
                    if self.on_retry:
                        self.on_retry(attempt + 1, e)
                    
                    time.sleep(delay)
                else:
                    raise
        
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry state")
