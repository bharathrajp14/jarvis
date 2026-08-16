# core/code_graph.py — Workspace Code Symbol Graph for BR JARVIS MK38
"""
AST-based symbol index over workspace Python sources.

Builds a lightweight code graph of definitions (classes, functions, methods) and
their references so the agent can answer "where is X defined?" and "who calls X?"
without shelling out to an external language server.
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS.CodeGraph")

# Directories that never contain first-party source worth indexing.
SKIP_DIRS = frozenset({
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules",
    "build", "dist", ".mypy_cache", ".pytest_cache", ".ruff_cache",
})


class SymbolDefinition(BaseModel):
    """A single class/function/method definition site."""

    name: str
    symbol_type: str = Field(description="One of: class, function, method")
    file_path: str
    line_number: int = Field(description="1-based line of the definition")
    end_line: Optional[int] = None
    docstring: Optional[str] = None
    parent: Optional[str] = Field(default=None, description="Enclosing class for methods")


class _SymbolVisitor(ast.NodeVisitor):
    """Collects definitions and Name/Attribute references from one module."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.definitions: List[SymbolDefinition] = []
        self.references: List[Dict[str, Any]] = []
        # Scope stack: a class name when inside a class body, None inside a function
        # body. Only the innermost frame decides method-vs-function, so a function
        # nested inside a method is correctly typed as a function.
        self._scope: List[Optional[str]] = []

    @property
    def _enclosing_class(self) -> Optional[str]:
        return self._scope[-1] if self._scope else None

    def _add_def(self, node: ast.AST, symbol_type: str) -> None:
        parent = self._enclosing_class
        self.definitions.append(
            SymbolDefinition(
                name=node.name,
                symbol_type=symbol_type,
                file_path=self.file_path,
                line_number=node.lineno,
                end_line=getattr(node, "end_lineno", None),
                docstring=ast.get_docstring(node),
                parent=parent,
            )
        )
        # The declaration itself counts as a reference, matching IDE
        # "find all references" behaviour.
        self._add_ref(node.name, node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add_def(node, "class")
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def _visit_func(self, node: ast.AST) -> None:
        self._add_def(node, "method" if self._enclosing_class else "function")
        self._scope.append(None)
        self.generic_visit(node)
        self._scope.pop()

    visit_FunctionDef = _visit_func  # type: ignore[assignment]
    visit_AsyncFunctionDef = _visit_func  # type: ignore[assignment]

    def _add_ref(self, name: str, node: ast.AST) -> None:
        self.references.append({
            "name": name,
            "file_path": self.file_path,
            "line_number": node.lineno,
            "column": node.col_offset,
        })

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._add_ref(node.id, node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load):
            self._add_ref(node.attr, node)
        self.generic_visit(node)


class WorkspaceCodeGraph:
    """In-memory symbol graph over one or more Python source trees."""

    def __init__(self) -> None:
        self._definitions: Dict[str, List[SymbolDefinition]] = {}
        self._references: Dict[str, List[Dict[str, Any]]] = {}
        self._indexed_files: set[str] = set()

    # ---------------------------------------------------------------- indexing

    def index_file(self, path: Path | str) -> int:
        """Index one Python file. Returns the number of definitions found."""
        path = Path(path)
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"⚠️ CodeGraph could not read {path}: {e}")
            return 0
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            logger.warning(f"⚠️ CodeGraph skipping {path} (syntax error line {e.lineno})")
            return 0

        file_key = str(path)
        self._forget_file(file_key)

        visitor = _SymbolVisitor(file_key)
        visitor.visit(tree)

        for definition in visitor.definitions:
            self._definitions.setdefault(definition.name, []).append(definition)
        for ref in visitor.references:
            self._references.setdefault(ref["name"], []).append(ref)

        self._indexed_files.add(file_key)
        return len(visitor.definitions)

    def index_directory(self, root: Path | str, pattern: str = "*.py") -> int:
        """Recursively index a source tree, skipping vendored/generated dirs."""
        root = Path(root)
        total = 0
        for path in sorted(root.rglob(pattern)):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            total += self.index_file(path)
        logger.info(f"📗 CodeGraph indexed {len(self._indexed_files)} files, {total} symbols under {root}")
        return total

    def _forget_file(self, file_key: str) -> None:
        """Drop prior entries for a file so re-indexing does not duplicate."""
        if file_key not in self._indexed_files:
            return
        for name, defs in list(self._definitions.items()):
            kept = [d for d in defs if d.file_path != file_key]
            if kept:
                self._definitions[name] = kept
            else:
                del self._definitions[name]
        for name, refs in list(self._references.items()):
            kept_refs = [r for r in refs if r["file_path"] != file_key]
            if kept_refs:
                self._references[name] = kept_refs
            else:
                del self._references[name]
        self._indexed_files.discard(file_key)

    # ----------------------------------------------------------------- queries

    def find_definition(self, name: str) -> List[SymbolDefinition]:
        """All definition sites for a symbol name."""
        return list(self._definitions.get(name, []))

    def find_references(self, name: str) -> List[Dict[str, Any]]:
        """All load-context reference sites for a symbol name, in source order."""
        refs = list(self._references.get(name, []))
        refs.sort(key=lambda r: (r["file_path"], r["line_number"], r["column"]))
        return refs

    def symbols_in_file(self, path: Path | str) -> List[SymbolDefinition]:
        """Every definition declared in a given file, ordered by line."""
        file_key = str(Path(path))
        found = [d for defs in self._definitions.values() for d in defs if d.file_path == file_key]
        found.sort(key=lambda d: d.line_number)
        return found

    def search(self, substring: str, limit: int = 25) -> List[SymbolDefinition]:
        """Case-insensitive fuzzy lookup over symbol names."""
        needle = substring.lower()
        hits = [d for name, defs in self._definitions.items() if needle in name.lower() for d in defs]
        hits.sort(key=lambda d: (len(d.name), d.name))
        return hits[:limit]

    def stats(self) -> Dict[str, int]:
        """Summary counters for diagnostics."""
        return {
            "files": len(self._indexed_files),
            "symbols": sum(len(v) for v in self._definitions.values()),
            "unique_names": len(self._definitions),
            "references": sum(len(v) for v in self._references.values()),
        }


_graph: Optional[WorkspaceCodeGraph] = None


def get_code_graph() -> WorkspaceCodeGraph:
    """Process-wide shared code graph instance."""
    global _graph
    if _graph is None:
        _graph = WorkspaceCodeGraph()
    return _graph
