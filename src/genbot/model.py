from typing import Callable, Generic, Optional, overload
from genbot.model_manager import ModelUnit
import inspect
from dataclasses import dataclass


@overload
def model(constructor: Callable) -> ModelUnit: ...

@overload
def model(constructor: Optional[Callable] = None,
          name: Optional[str] = None, 
          description: Optional[str] = None,
          default: bool = False
          ) -> Callable[[Callable], ModelUnit]: ...

def model(constructor: Optional[Callable] = None, 
          name: Optional[str] = None, 
          description: Optional[str] = None,
          default: bool = False
          ):

    def decorator(constructor: Callable):
        nonlocal name, description, default
        global _units, _default_unit

        if not constructor:
            raise ValueError('model constructor must be provided')

        if not name:
            name = constructor.__name__

        if not description:
            description = constructor.__doc__ if constructor.__doc__ else ''

        unit =  ModelUnit(name=name,
                          description=description,
                          constructor=constructor,
                          default=default)

        return unit

    if constructor:
        return decorator(constructor)
    else:
        return decorator
