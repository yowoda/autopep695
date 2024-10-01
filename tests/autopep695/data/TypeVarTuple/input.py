import typing as t
from typing_extensions import TypeVarTuple, Unpack

As = TypeVarTuple("As")
Ts = TypeVarTuple("Ts", default=Unpack[tuple[int, ...]])

def func(a: tuple[Unpack[As]]):
    ...

def func(a: tuple[str, Unpack[Ts]]):
    ...

def func_with_multiple_tvartuples(a: tuple[Unpack[As]], b: tuple[Unpack[Ts]]):
    ...

class SomeClass(t.Generic[Unpack[Ts]], t.Protocol[Unpack[Ts]]):
    ...