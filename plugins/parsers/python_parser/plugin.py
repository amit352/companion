"""
Built-in Python parser plugin using tree-sitter.
Deterministic: same source → same AST every run.
"""
from pathlib import Path
from typing import Any

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from companion.sdk.base.parser_plugin import (
    ASTNode, Dependency, ParserOutput, ParserPlugin, Symbol,
)
from companion.sdk.base.plugin_base import PluginContext, PluginManifest, PluginType

PY_LANGUAGE = Language(tspython.language())


class Plugin(ParserPlugin):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)
        self._parser = Parser(PY_LANGUAGE)

    async def parse_file(self, file_path: str, source: str) -> ParserOutput:
        tree = self._parser.parse(source.encode())
        root = tree.root_node

        symbols: list[Symbol] = []
        dependencies: list[Dependency] = []
        ast_nodes: list[ASTNode] = []

        self._walk(root, source, file_path, symbols, dependencies, ast_nodes)

        return ParserOutput(
            ast=ast_nodes,
            symbols=symbols,
            dependencies=dependencies,
            language="python",
            file_path=file_path,
        )

    def _walk(
        self,
        node: Node,
        source: str,
        file_path: str,
        symbols: list[Symbol],
        deps: list[Dependency],
        ast_nodes: list[ASTNode],
    ) -> ASTNode:
        children_ast: list[ASTNode] = []

        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(Symbol(
                    name=name_node.text.decode(),
                    kind="function",
                    file_path=file_path,
                    line=node.start_point[0] + 1,
                    language="python",
                ))

        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(Symbol(
                    name=name_node.text.decode(),
                    kind="class",
                    file_path=file_path,
                    line=node.start_point[0] + 1,
                    language="python",
                ))

        elif node.type == "import_statement":
            for child in node.children:
                if child.type in ("dotted_name", "aliased_import"):
                    target = child.text.decode().split(" as ")[0].strip()
                    deps.append(Dependency(source=file_path, target=target, kind="import"))

        elif node.type == "import_from_statement":
            module_node = node.child_by_field_name("module_name")
            if module_node:
                deps.append(Dependency(
                    source=file_path,
                    target=module_node.text.decode(),
                    kind="import",
                    line=node.start_point[0] + 1,
                ))

        for child in node.children:
            child_ast = self._walk(child, source, file_path, symbols, deps, ast_nodes)
            children_ast.append(child_ast)

        ast_node = ASTNode(
            type=node.type,
            name=node.text.decode()[:80] if node.child_count == 0 else node.type,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            children=children_ast,
        )
        return ast_node
