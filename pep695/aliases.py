from __future__ import annotations

import typing as t

import libcst as cst
from libcst import matchers as m

__all__: t.Sequence[str] = ("AliasCollection", "get_qualified_name")


class AliasCollection(set[str]):
    def add_if_not_none(self, alias: t.Optional[str]) -> None:
        if alias is not None:
            self.add(alias)


def get_qualified_name(node: cst.BaseExpression) -> str:
    if m.matches(node, m.Attribute(value=m.Name(), attr=m.Name())):
        node = t.cast(cst.Attribute, node)
        name = cst.ensure_type(node.value, cst.Name).value + "." + node.attr.value

    elif isinstance(node, cst.Name):
        name = node.value

    else:
        name = ""

    return name
