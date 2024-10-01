import typing as t
from typing_extensions import TypeVarTuple, Unpack

def func[*As](a: tuple[Unpack[As]]):
    ...

def func[*Ts = Unpack[tuple[int, ...]]](a: tuple[str, Unpack[Ts]]):
    ...

def func_with_multiple_tvartuples[*As, *Ts = Unpack[tuple[int, ...]]](a: tuple[Unpack[As]], b: tuple[Unpack[Ts]]):
    ...

class SomeClass[*Ts = Unpack[tuple[int, ...]]](t.Protocol):
    ...