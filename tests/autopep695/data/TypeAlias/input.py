import typing_extensions as t

Alias: t.TypeAlias = str 

UsedT = t.TypeVar("UsedT")

AliasThatUsesT: t.TypeAlias = UsedT

def func(x: UsedT) -> UsedT:
    ...