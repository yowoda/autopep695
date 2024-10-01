import typing as t
from typing_extensions import *

P = ParamSpec("P")
DefaultP = ParamSpec("DefaultP", default=...)

def func(callback: t.Callable[P, t.Any]):
    ...

def func(callback: t.Callable[DefaultP, t.Any]) -> t.Callable[DefaultP, t.Any]:
    ...

def func_with_multiple_paramspecs(a: P, b: DefaultP):
    ...

class SomeClass(t.Generic[P, DefaultP]): ...