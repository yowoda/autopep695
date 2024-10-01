# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t
from typing_extensions import TypeAlias

from typing import TypeAlias as AliasTypeHint

Alias: t.TypeAlias = t.Union[str, int]

T = t.TypeVar("T")

NoneOr: TypeAlias = t.Optional[T]

StringifiedAlias: "TypeAlias" = None

class SomeClass:
    T = t.TypeVar("T", str, int)

    alias: t.TypeAlias = T

somealias: AliasTypeHint = str | int

ignored_alias: TypeAlias = None # pep695-ignore

IgnoredT = t.TypeVar("IgnoredT") # pep695-ignore

alias_with_ignored_param: t.TypeAlias = IgnoredT