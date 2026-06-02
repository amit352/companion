from abc import abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from .plugin_base import PluginBase, PluginContext


class DocFormat(StrEnum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"


class DocType(StrEnum):
    SRS = "srs"
    ADR = "adr"
    API_DOCS = "api_docs"
    ARCHITECTURE = "architecture"
    SEQUENCE_DIAGRAM = "sequence_diagram"
    README = "readme"


class GeneratedDoc(BaseModel):
    title: str
    doc_type: DocType
    format: DocFormat
    content: str
    metadata: dict[str, Any] = {}


class DocumentationPlugin(PluginBase):
    """Plugin type 4.3: Generates technical documentation from graph data."""

    @abstractmethod
    async def generate(
        self,
        doc_type: DocType,
        format: DocFormat,
        graph_context: dict[str, Any],
    ) -> GeneratedDoc:
        """Generate a document of the given type from graph context."""

    async def execute(self, context: PluginContext, inputs: dict[str, Any]) -> dict[str, Any]:
        result = await self.generate(
            doc_type=DocType(inputs["doc_type"]),
            format=DocFormat(inputs["format"]),
            graph_context=inputs["graph_context"],
        )
        return result.model_dump()
