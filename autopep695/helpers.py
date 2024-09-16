# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t
from typing_extensions import Unpack

import libcst as cst

T = t.TypeVar("T")

__all__: t.Sequence[str] = ("ensure_type", "make_clean_name")


def ensure_type(obj: object, *types: Unpack[tuple[type[T], ...]]) -> T:
    """
    `libcst.ensure_type` but it can compare a given object against multiple types
    """
    if not isinstance(obj, types):
        raise TypeError(
            f"Expected object of type {' | '.join(t.__name__ for t in types)!r}, got type {obj.__class__.__name__!r}"
        )

    return obj


def make_clean_name(name: str, variance: bool, private: bool) -> str:
    if private:
        name = name.lstrip("_")

    if variance:
        name = name.removesuffix("_co")
        name = name.removesuffix("_contra")

    return name


def get_code(*nodes: cst.CSTNode) -> str:
    reprs: list[str] = []
    module = cst.Module(body=())

    for node in nodes:
        reprs.append(module.code_for_node(node))

    return ", ".join(reprs)


def make_empty_IndentedBlock() -> cst.IndentedBlock:
    return cst.IndentedBlock(body=[cst.SimpleStatementLine([cst.Expr(cst.Ellipsis())])])
