from __future__ import annotations

from dataclasses import dataclass
import logging
import typing as t

import libcst as cst
from libcst import matchers as m
from libcst.metadata import PositionProvider, CodeRange

from pep695.ux import BOLD, RESET, YELLOW, RED, GREEN, BLUE
from pep695.base import BaseVisitor, RemoveGenericBaseMixin

if t.TYPE_CHECKING:
    from pep695.base import TypeClassCollection


@dataclass(frozen=True)
class Diagnostic:
    message: str
    file_path: str
    line: int
    column: int
    old_code: str
    new_code: str

    def format(self) -> str:
        old_code_lines = self._format_code("- ", self.old_code.strip())
        new_code_lines = self._format_code("+ ", self.new_code.strip())
        return (
            f"\n{BOLD}{BLUE}{self.file_path}{RESET}:{BOLD}{YELLOW}{self.line}{RESET}:{BOLD}{YELLOW}{self.column}{RESET}: {self.message}\n"
            + f"{BOLD}{RED}{old_code_lines}\n"
            + f"{GREEN}{new_code_lines}{RESET}\n"
        )

    def _format_code(self, leading_text: str, code: str) -> str:
        return "\n".join(f"{leading_text}{line}" for line in code.splitlines())


class FixFormattingTransformer(m.MatcherDecoratableTransformer):
    def __init__(self, type_collection: TypeClassCollection) -> None:
        self._type_collection = type_collection

        super().__init__()

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        return updated_node.with_changes(
            body=cst.IndentedBlock(
                body=[cst.SimpleStatementLine([cst.Expr(cst.Ellipsis())])]
            )
        )

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        return updated_node.with_changes(
            body=cst.IndentedBlock(
                body=[cst.SimpleStatementLine([cst.Expr(cst.Ellipsis())])]
            )
        )


class FixClassDefFormattingTransformer(
    FixFormattingTransformer, RemoveGenericBaseMixin
): ...


class CheckPEP695Visitor(BaseVisitor):
    def __init__(self, file_path: str, *, silent: bool) -> None:
        self._file_path = file_path
        self._errors: int = 0
        self._silent = silent
        self._empty_module = cst.Module(body=())

        super().__init__()

    @property
    def errors(self) -> int:
        return self._errors

    def visit_Assign(self, node: cst.Assign) -> None:
        if self._should_ignore_statement(node):
            return

        if isinstance(node.value, cst.Call):
            self._is_typeparam_assign(node.value)

    def _gen_diagnostic(
        self, old_node: cst.CSTNode, message: str, new_node: cst.CSTNode
    ) -> t.Optional[Diagnostic]:
        self._errors += 1
        if self._silent:
            return

        metadata = self.get_metadata(PositionProvider, old_node)
        assert isinstance(metadata, CodeRange)
        pos = metadata.start
        old_node = cst.ensure_type(
            old_node.visit(FixFormattingTransformer(self._type_collection)), cst.CSTNode
        )
        new_node = cst.ensure_type(
            new_node.visit(FixClassDefFormattingTransformer(self._type_collection)),
            cst.CSTNode,
        )
        return Diagnostic(
            message=message,
            file_path=self._file_path,
            line=pos.line,
            column=pos.column,
            old_code=self._empty_module.code_for_node(old_node),
            new_code=self._empty_module.code_for_node(new_node),
        )

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        new_node = super().leave_AnnAssign(node, node)
        if not isinstance(new_node, cst.TypeAlias):
            return

        if self._silent:
            self._errors += 1
            return

        report = self._gen_diagnostic(
            node,
            "Found type alias declared using old TypeAlias annotation syntax",
            new_node,
        )
        assert report is not None
        logging.error("%s", report.format())

    def _report_if_requires_change(
        self, node: t.Union[cst.FunctionDef, cst.ClassDef], message: str
    ) -> None:
        typevars = self._new_typevars_for_node[node]
        paramspecs = self._new_paramspecs_for_node[node]
        typevartuples = self._new_typevartuples_for_node[node]

        if not any((typevars, paramspecs, typevartuples)):
            return

        if self._silent:
            self._errors += 1
            return

        new_node = t.cast(
            cst.CSTNode,
            self._add_typeparameters(
                node,
                node,
                typevars,
                paramspecs,
                typevartuples,
            ),
        )

        diagnostic = self._gen_diagnostic(node, message, new_node)
        assert diagnostic is not None
        logging.error("%s", diagnostic.format())

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        super().visit_ClassDef(node)
        self._report_if_requires_change(
            node, "Found generic class declared using old type parameter syntax"
        )

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        super().visit_FunctionDef(node)
        self._report_if_requires_change(
            node, "Found generic function declared using old type parameter syntax"
        )
