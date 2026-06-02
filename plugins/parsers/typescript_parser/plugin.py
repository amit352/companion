"""
TypeScript / JavaScript parser plugin using tree-sitter.
Handles .ts, .tsx, .js, .jsx files.
"""
from tree_sitter import Language, Node, Parser
import tree_sitter_typescript as tsts

from feature_graph.sdk.base.parser_plugin import (
    ASTNode, Dependency, ParserOutput, ParserPlugin, Symbol,
)
from feature_graph.sdk.base.plugin_base import PluginManifest

TS_LANGUAGE = Language(tsts.language_typescript())
TSX_LANGUAGE = Language(tsts.language_tsx())


class Plugin(ParserPlugin):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)
        self._ts_parser = Parser(TS_LANGUAGE)
        self._tsx_parser = Parser(TSX_LANGUAGE)

    async def parse_file(self, file_path: str, source: str) -> ParserOutput:
        parser = self._tsx_parser if file_path.endswith((".tsx", ".jsx")) else self._ts_parser
        tree = parser.parse(source.encode())

        symbols: list[Symbol] = []
        dependencies: list[Dependency] = []

        self._walk(tree.root_node, source, file_path, symbols, dependencies)

        return ParserOutput(
            ast=[],
            symbols=symbols,
            dependencies=dependencies,
            language="typescript",
            file_path=file_path,
        )

    def _walk(
        self,
        node: Node,
        source: str,
        file_path: str,
        symbols: list[Symbol],
        deps: list[Dependency],
    ) -> None:
        if node.type in ("function_declaration", "function_expression", "arrow_function"):
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode() if name_node else "<anonymous>"
            symbols.append(Symbol(
                name=name,
                kind="function",
                file_path=file_path,
                line=node.start_point[0] + 1,
                language="typescript",
            ))

        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(Symbol(
                    name=name_node.text.decode(),
                    kind="class",
                    file_path=file_path,
                    line=node.start_point[0] + 1,
                    language="typescript",
                ))

        elif node.type in ("method_definition", "public_field_definition"):
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(Symbol(
                    name=name_node.text.decode(),
                    kind="method",
                    file_path=file_path,
                    line=node.start_point[0] + 1,
                    language="typescript",
                ))

        elif node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            if source_node:
                target = source_node.text.decode().strip("'\"")
                deps.append(Dependency(
                    source=file_path,
                    target=target,
                    kind="import",
                    line=node.start_point[0] + 1,
                ))

        elif node.type in ("export_statement",):
            # re-export: export { foo } from './bar'
            source_node = node.child_by_field_name("source")
            if source_node:
                target = source_node.text.decode().strip("'\"")
                deps.append(Dependency(source=file_path, target=target, kind="import"))

        for child in node.children:
            self._walk(child, source, file_path, symbols, deps)
