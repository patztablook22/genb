from typing import Callable, Generic, TypeVar, Optional, overload, Any, Awaitable
import inspect
from dataclasses import dataclass
from genbot.job_manager import JobUnit

@overload
def job(function: Callable) -> JobUnit: ...

@overload
def job(function: Optional[Callable] = None,
        name: Optional[str] = None, 
        description: Optional[str] = None,
        ) -> Callable[[Callable], JobUnit]: ...

def job(function: Optional[Callable] = None, 
        name: Optional[str] = None, 
        description: Optional[str] = None,
        ):

    def decorator(function: Callable):
        nonlocal name, description
        global _jobs

        if not function:
            raise ValueError('function must be provided')

        if not name:
            name = function.__name__

        if not description:
            description = function.__doc__ if function.__doc__ else ''

        job =  JobUnit(name=name,
                       description=description,
                       function=function)

        return job

    if function:
        return decorator(function)
    else:
        return decorator
