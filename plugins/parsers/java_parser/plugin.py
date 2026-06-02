"""Java parser using tree-sitter."""
import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser

from companion.sdk.base.parser_plugin import Dependency, ParserOutput, ParserPlugin, Symbol
from companion.sdk.base.plugin_base import PluginManifest

JAVA_LANGUAGE = Language(tsjava.language())


class Plugin(ParserPlugin):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)
        self._parser = Parser(JAVA_LANGUAGE)

    async def parse_file(self, file_path: str, source: str) -> ParserOutput:
        tree = self._parser.parse(source.encode())
        symbols, deps = [], []
        self._walk(tree.root_node, file_path, symbols, deps)
        return ParserOutput(ast=[], symbols=symbols, dependencies=deps,
                            language="java", file_path=file_path)

    def _walk(self, node: Node, fp: str, symbols: list, deps: list) -> None:
        if node.type in ("class_declaration", "interface_declaration", "enum_declaration"):
            name_node = node.child_by_field_name("name")
            kind = {"class_declaration": "class", "interface_declaration": "interface",
                    "enum_declaration": "class"}.get(node.type, "class")
            if name_node:
                symbols.append(Symbol(name=name_node.text.decode(), kind=kind,
                                      file_path=fp, line=node.start_point[0]+1, language="java"))

        elif node.type == "method_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(Symbol(name=name_node.text.decode(), kind="function",
                                      file_path=fp, line=node.start_point[0]+1, language="java"))

        elif node.type == "import_declaration":
            path_node = node.child_by_field_name("name")
            if path_node:
                deps.append(Dependency(source=fp, target=path_node.text.decode(),
                                       kind="import", line=node.start_point[0]+1))
        for child in node.children:
            self._walk(child, fp, symbols, deps)
