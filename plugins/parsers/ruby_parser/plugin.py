"""Ruby parser using tree-sitter."""
import tree_sitter_ruby as tsruby
from tree_sitter import Language, Node, Parser

from companion.sdk.base.parser_plugin import Dependency, ParserOutput, ParserPlugin, Symbol
from companion.sdk.base.plugin_base import PluginManifest

RB_LANGUAGE = Language(tsruby.language())


class Plugin(ParserPlugin):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)
        self._parser = Parser(RB_LANGUAGE)

    async def parse_file(self, file_path: str, source: str) -> ParserOutput:
        tree = self._parser.parse(source.encode())
        symbols, deps = [], []
        self._walk(tree.root_node, file_path, symbols, deps)
        return ParserOutput(ast=[], symbols=symbols, dependencies=deps,
                            language="ruby", file_path=file_path)

    def _walk(self, node: Node, fp: str, symbols: list, deps: list) -> None:
        if node.type == "class":
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(Symbol(name=name_node.text.decode(), kind="class",
                                      file_path=fp, line=node.start_point[0]+1, language="ruby"))

        elif node.type == "module":
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(Symbol(name=name_node.text.decode(), kind="module",
                                      file_path=fp, line=node.start_point[0]+1, language="ruby"))

        elif node.type in ("method", "singleton_method"):
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(Symbol(name=name_node.text.decode(), kind="function",
                                      file_path=fp, line=node.start_point[0]+1, language="ruby"))

        elif node.type == "call":
            # require 'something' or require_relative 'something'
            method_node = node.child_by_field_name("method")
            args_node   = node.child_by_field_name("arguments")
            if method_node and method_node.text.decode() in ("require", "require_relative") and args_node:
                for child in args_node.children:
                    if child.type in ("string", "simple_symbol"):
                        target = child.text.decode().strip("'\":")
                        deps.append(Dependency(source=fp, target=target, kind="import",
                                               line=node.start_point[0]+1))
        for child in node.children:
            self._walk(child, fp, symbols, deps)
