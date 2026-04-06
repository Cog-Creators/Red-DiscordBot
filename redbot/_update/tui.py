import enum

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.events import Click
from textual.widgets import Footer, Markdown, MarkdownViewer, Static
from typing_extensions import Self

from .changelog import Changelogs


# See https://github.com/Textualize/textual/discussions/6449
class MarkdownLinkTooltip(Static, inherit_css=False):
    DEFAULT_CSS = """
    MarkdownLinkTooltip {
        layer: _tooltips;
        margin: 1 0;
        padding: 1 2;
        background: $panel;
        width: auto;
        height: auto;
        constrain: inside inflect;
        max-width: 40;
        display: none;
        offset-x: -50%;
    }
    """


class _MarkdownViewer(MarkdownViewer):
    DEFAULT_CSS = """
    _MarkdownViewer {
        layers: default _tooltips;
    }
    """

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield MarkdownLinkTooltip()

    def on_markdown_link_clicked(self, message: Markdown.LinkClicked) -> None:
        # We don't want the default behavior of opening the browser/navigating to a file on click.
        message.prevent_default()

        tooltip = self.get_child_by_type(MarkdownLinkTooltip)
        tooltip.display = True
        # You can't cycle over the links in MarkdownViewer (see Textualize/textual#3555)
        # so using mouse position is fine.
        # Textualize/textual#3555: https://github.com/Textualize/textual/discussions/3555
        tooltip.absolute_offset = self.app.mouse_position
        # For some reason, links only render correctly when Text has a span over the whole text
        # with a link but not when Text just has a style applied to it directly, i.e.:
        #   Text(message.href, style=f"link {message.href}")
        # will not work.
        tooltip.update(Text().append(message.href, style=f"link {message.href}"))

    def on_click(self, message: Click) -> None:
        tooltip = self.get_child_by_type(MarkdownLinkTooltip)
        tooltip.display = False


class ChangelogReaderResult(enum.Enum):
    QUIT = enum.auto()
    CONTINUE = enum.auto()


class ChangelogReaderApp(App[ChangelogReaderResult], inherit_bindings=False):
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding(key="ctrl+c", action="quit", description="Exit redbot-update"),
        Binding(key="q", action="continue", description="Finish reading the changelog"),
    ]

    def __init__(self, markdown_content: str) -> None:
        self.markdown_content = markdown_content
        super().__init__()

    @classmethod
    def from_changelogs(cls, changelogs: Changelogs) -> Self:
        if not changelogs:
            return cls("")

        parts = []
        contributors = sorted(
            {
                contributor
                for changelog in changelogs.values()
                for contributor in changelog.contributors
            }
        )
        if contributors:
            contributor_thanks = (
                "# Thanks to our contributors \N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16}\n"
                "**The releases below were made with help from the following people:**  \n"
            )
            contributor_thanks += ", ".join(
                f"[@{contributor}](https://github.com/sponsors/{contributor})"
                for contributor in contributors
            )
            parts.append(contributor_thanks)

        parts.append("# Read before updating")
        for changelog in reversed(changelogs.values()):
            if changelog.read_before_updating_section:
                parts.append(f"## {changelog.version}")
                parts.append(changelog.read_before_updating_section)

        parts.append("# User changelog")
        for changelog in reversed(changelogs.values()):
            if changelog.user_changelog_section:
                parts.append(f"## {changelog.version}")
                parts.append(changelog.user_changelog_section)

        return cls("\n".join(parts))

    def compose(self) -> ComposeResult:
        markdown_viewer = _MarkdownViewer(
            self.markdown_content, show_table_of_contents=True, open_links=False
        )
        markdown_viewer.code_indent_guides = False
        yield markdown_viewer
        yield Footer()

    def action_quit(self) -> None:
        self.exit(ChangelogReaderResult.QUIT)

    def action_continue(self) -> None:
        self.exit(ChangelogReaderResult.CONTINUE)
