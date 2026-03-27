from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.events import Click
from textual.widgets import Footer, Markdown, MarkdownViewer, Static


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


class MarkdownViewerApp(App):
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
    ]

    def __init__(self, markdown_content: str) -> None:
        self.markdown_content = markdown_content
        super().__init__()

    def compose(self) -> ComposeResult:
        markdown_viewer = _MarkdownViewer(
            self.markdown_content, show_table_of_contents=True, open_links=False
        )
        markdown_viewer.code_indent_guides = False
        yield markdown_viewer
        yield Footer()
