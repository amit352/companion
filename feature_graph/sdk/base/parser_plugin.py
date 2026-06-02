from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from .plugin_base import PluginBase, PluginContext


class ASTNode(BaseModel):
    type: str
    name: str
    start_line: int
    end_line: int
    children: list["ASTNode"] = []
    metadata: dict[str, Any] = {}


class Symbol(BaseModel):
    name: str
    kind: str  # function | class | method | variable | constant
    file_path: str
    line: int
    language: str
    docstring: str | None = None
    visibility: str = "public"


class Dependency(BaseModel):
    source: str
    target: str
    kind: str  # import | call | inherit | implement
    line: int | None = None


class ParserOutput(BaseModel):
    ast: list[ASTNode]
    symbols: list[Symbol]
    dependencies: list[Dependency]
    language: str
    file_path: str


class ParserPlugin(PluginBase):
    """
    Plugin type 4.1: Parses language-specific source code into AST, symbols, dependencies.
    Implementations should wrap tree-sitter grammars (same approach as Understand-Anything).
    """

    @abstractmethod
    async def parse_file(self, file_path: str, source: str) -> ParserOutput:
        """Parse a single source file. Must be deterministic — same input → same output."""

    async def execute(self, context: PluginContext, inputs: dict[str, Any]) -> dict[str, Any]:
        file_path: str = inputs["file_path"]
        source: str = inputs["source"]
        result = await self.parse_file(file_path, source)
        return result.model_dump()
