from typing import Any, Dict, List

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective


class ChangelogContributors(SphinxDirective):
    has_content = True

    def run(self) -> List[nodes.Node]:
        contributors = [contributor for line in self.content for contributor in line.split()]

        comment_value = " ".join(contributors)
        line_nodes = []
        for contributor in contributors:
            if line_nodes:
                line_nodes.append(nodes.Text(", "))
            line_nodes.append(
                nodes.reference(
                    contributor,
                    f"@{contributor}",
                    internal=False,
                    refuri=f"https://github.com/sponsors/{contributor}",
                )
            )

        node = nodes.line_block(
            "",
            nodes.comment("", f"RED-CHANGELOG-CONTRIBUTORS: {comment_value}"),
            nodes.line("", "Thanks to all these amazing people who contributed to this release:"),
            nodes.line("", "", *line_nodes),
        )
        return [node]


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_directive("changelog-contributors", ChangelogContributors)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
