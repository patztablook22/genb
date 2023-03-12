from dataclasses import dataclass
from typing import Any, Optional, Callable
from types import ModuleType
import inspect
import importlib
import warnings

@dataclass
class BaseUnit:
    name: str
    description: str

BaseUnitBuilder = Callable[[Any], dict[str, BaseUnit]]

class RecursiveBaseUnitBuilder:
    def __call__(self, source: Any) -> dict[str, BaseUnit]:
        units = {}
        self._call_recursive(source, units, 0)
        return units

    def from_dict(self, d, units, level):
        raise NotImplementedError

    def from_module(self, module, units, level):
        raise NotImplementedError

    def from_payload(self, payload, units, level):
        raise NotImplementedError

    def _call_recursive(self, source, units, level):
        if isinstance(source, ModuleType):
            self.from_module(source, units, level + 1)

        elif isinstance(source, dict):
            for nname, obj in source.items():
                name = str(nname)
                assert obj, name

                self.from_dict({'name': name, 'payload': obj}, units, level + 1)

        elif isinstance(source, list):
            for elem in source:
                if isinstance(elem, dict):
                    self.from_dict(elem, units, level + 1)

                elif inspect.ismodule(elem):
                    self._call_recursive(elem, units, level + 1)

                else:
                    self.from_payload(elem, units, level + 1)
        else:
            self.from_payload(source, units, level)

class BaseUnitManager:
    def __init__(self, 
                 source: Any,
                 builder: BaseUnitBuilder,
                 ):

        self._source = source
        self._builder = builder
        self.build()

    @property
    def units(self):
        return self._units

    def reload(self):
        def reload_recursive(arr):
            for elem in arr:
                if inspect.ismodule(elem):
                    importlib.reload(elem)
                elif isinstance(elem, list):
                    reload_recursive(elem)

        reload_recursive([self._source])
        self.build()

    def build(self):
        self._units = self._builder(self._source)
