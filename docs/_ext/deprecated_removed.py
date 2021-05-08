"""
A Sphinx extension adding a ``deprecated-removed`` directive that works
similarly to CPython's directive with the same name.

The key difference is that instead of passing the version of planned removal,
the writer must provide the minimum amount of days that must pass
since the date of the release it was deprecated in.

Due to lack of a concrete release schedule for Red, this ensures that
we give enough time to people affected by the changes no matter
when the releases actually happen.

`DeprecatedRemoved` class is heavily based on
`sphinx.domains.changeset.VersionChange` class that is available at:
https://github.com/sphinx-doc/sphinx/blob/0949735210abaa05b6448e531984f159403053f4/sphinx/domains/changeset.py

Copyright 2007-2020 by the Sphinx team, see AUTHORS:
https://github.com/sphinx-doc/sphinx/blob/82f495fed386c798735adf675f867b95d61ee0e1/AUTHORS

The original copy was distributed under BSD License and this derivative work
is distributed under GNU GPL Version 3.
"""

import datetime
import multiprocessing
import subprocess
from typing import Any, Dict, List, Optional

from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective


class TagDateCache:
    def __init__(self) -> None:
        self._tags: Dict[str, datetime.date] = {}

    def _populate_tags(self) -> None:
        with _LOCK:
            if self._tags:
                return
            out = subprocess.check_output(
                ("git", "tag", "-l", "--format", "%(creatordate:raw)\t%(refname:short)"),
                text=True,
            )
            lines = out.splitlines(False)
            for line in lines:
                creator_date, tag_name = line.split("\t", maxsplit=1)
                timestamp = int(creator_date.split(" ", maxsplit=1)[0])
                self._tags[tag_name] = datetime.datetime.fromtimestamp(
                    timestamp, tz=datetime.timezone.utc
                ).date()

    def get_tag_date(self, tag_name: str) -> Optional[datetime.date]:
        self._populate_tags()
        return self._tags.get(tag_name)


_LOCK = multiprocessing.Manager().Lock()
_TAGS = TagDateCache()


class DeprecatedRemoved(SphinxDirective):
    has_content = True
    required_arguments = 2
    optional_arguments = 1
    final_argument_whitespace = True

    def run(self) -> List[nodes.Node]:
        # Some Sphinx stuff
        node = addnodes.versionmodified()
        node.document = self.state.document
        self.set_source_info(node)
        node["type"] = self.name
        node["version"] = tuple(self.arguments)
        if len(self.arguments) == 3:
            inodes, messages = self.state.inline_text(self.arguments[2], self.lineno + 1)
            para = nodes.paragraph(self.arguments[2], "", *inodes, translatable=False)
            self.set_source_info(para)
            node.append(para)
        else:
            messages = []

        # Text generation
        deprecation_version = self.arguments[0]
        minimum_days = int(self.arguments[1])
        tag_date = _TAGS.get_tag_date(deprecation_version)
        text = (
            f"Will be deprecated in version {deprecation_version},"
            " and removed in the first minor version that gets released"
            f" after {minimum_days} days since deprecation"
            if tag_date is None
            else f"Deprecated since version {deprecation_version},"
            " will be removed in the first minor version that gets released"
            f" after {tag_date + datetime.timedelta(days=minimum_days)}"
        )

        # More Sphinx stuff
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)
        classes = ["versionmodified"]
        if len(node):
            if isinstance(node[0], nodes.paragraph) and node[0].rawsource:
                content = nodes.inline(node[0].rawsource, translatable=True)
                content.source = node[0].source
                content.line = node[0].line
                content += node[0].children
                node[0].replace_self(nodes.paragraph("", "", content, translatable=False))

            node[0].insert(0, nodes.inline("", f"{text}: ", classes=classes))
        else:
            para = nodes.paragraph(
                "", "", nodes.inline("", f"{text}.", classes=classes), translatable=False
            )
            node.append(para)

        ret = [node]
        ret += messages

        return ret


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_directive("deprecated-removed", DeprecatedRemoved)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
    }
