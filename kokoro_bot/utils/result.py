from typing import TypeVar, Generic, Optional

T = TypeVar('T')

class Result(Generic[T]):
    """Enhanced Result class with type hints"""
    def __init__(self, value: Optional[T] = None, error: Optional[str] = None):
        self.value = value
        self.error = error
        self.success = error is None
        
    @staticmethod
    def ok(value: T) -> 'Result[T]':
        return Result(value=value)
        
    @staticmethod
    def err(error: str) -> 'Result[T]':
        return Result(error=error)