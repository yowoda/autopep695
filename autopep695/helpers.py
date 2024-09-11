# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t
from typing_extensions import Unpack

T = t.TypeVar("T")

__all__: t.Sequence[str] = ("ensure_type",)


def ensure_type(obj: object, *types: Unpack[tuple[type[T], ...]]) -> T:
    """
    `libcst.ensure_type` but it can compare a given object against multiple types
    """
    if not isinstance(obj, types):
        raise TypeError(
            f"Expected object of type {' | '.join(t.__name__ for t in types)!r}, got type {obj.__class__.__name__!r}"
        )

    return obj
