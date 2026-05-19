from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Set

from docutils import nodes
from docutils.io import StringOutput
from docutils.nodes import Element

from sphinx.application import Sphinx
from sphinx.builders.text import TextBuilder
from sphinx.writers.text import TextWriter
from sphinx.util import logging
from sphinx.util.docutils import SphinxTranslator

logger = logging.getLogger(__name__)


class PromptTranslator(SphinxTranslator):
    builder: PromptBuilder

    def __init__(self, document: nodes.document, builder: PromptBuilder) -> None:
        super().__init__(document, builder)
        self.body = ""
        self.prompts: List[Dict[str, str]] = []

    def visit_document(self, node: Element) -> None:
        pass

    def depart_document(self, node: Element) -> None:
        if not self.prompts:
            self.body = ""
            return
        if self.builder.out_suffix.endswith(".json"):
            self.body = json.dumps(self.prompts, indent=4)
        else:
            self.body = "\n".join(prompt["content"] for prompt in self.prompts)

    def unknown_visit(self, node: Element) -> None:
        pass

    def unknown_departure(self, node: Element) -> None:
        pass

    def visit_prompt(self, node: Element) -> None:
        self.prompts.append(
            {
                "language": node.attributes["language"],
                "prompts": node.attributes["prompts"],
                "modifiers": node.attributes["modifiers"],
                "rawsource": node.rawsource,
                "content": node.children[0],
            }
        )


class PromptWriter(TextWriter):
    def translate(self) -> None:
        visitor = self.builder.create_translator(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = visitor.body


class prompt(nodes.literal_block):
    pass


class PromptBuilder(TextBuilder):
    """Extract prompts from documents."""

    format = "json"
    epilog = "The files with prompts are in %(outdir)s."

    out_suffix = ".json"
    default_translator_class = PromptTranslator
    writer: PromptWriter

    def init(self) -> None:
        sphinx_prompt = __import__("sphinx-prompt")

        def run(self) -> List[prompt]:
            self.assert_has_content()
            rawsource = "\n".join(self.content)
            language = self.options.get("language") or "text"
            prompts = [
                p
                for p in (
                    self.options.get("prompts") or sphinx_prompt.PROMPTS.get(language, "")
                ).split(",")
                if p
            ]
            modifiers = [
                modifier for modifier in self.options.get("modifiers", "").split(",") if modifier
            ]
            content = rawsource
            if "auto" in modifiers:
                parts = []
                for line in self.content:
                    for p in prompts:
                        if line.startswith(p):
                            line = line[len(p) + 1 :].rstrip()
                    parts.append(line)
                content = "\n".join(parts)
            node = prompt(
                rawsource,
                content,
                directive_content=self.content,
                language=language,
                prompts=self.options.get("prompts") or sphinx_prompt.PROMPTS.get(language, ""),
                modifiers=modifiers,
            )
            return [node]

        sphinx_prompt.PromptDirective.run = run

    def prepare_writing(self, docnames: Set[str]) -> None:
        del docnames
        self.writer = PromptWriter(self)

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        self.writer.write(doctree, StringOutput(encoding="utf-8"))
        if not self.writer.output:
            # don't write empty files
            return

        filename = os.path.join(self.outdir, docname.replace("/", os.path.sep) + self.out_suffix)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.writer.output)
        except OSError as err:
            logger.warning("error writing file %s: %s", filename, err)


class JsonPromptBuilder(PromptBuilder):
    name = "jsonprompt"
    out_suffix = ".json"


class TextPromptBuilder(PromptBuilder):
    name = "textprompt"
    out_suffix = ".txt"


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_builder(JsonPromptBuilder)
    app.add_builder(TextPromptBuilder)

    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
