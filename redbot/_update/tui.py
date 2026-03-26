from urllib.parse import urlparse

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, MarkdownViewer


# DEP-WARN
# Workaround for bug: https://github.com/Textualize/textual/issues/6039
class _MarkdownViewer(MarkdownViewer):
    async def go(self, location: str) -> None:
        url = urlparse(location)
        if url.scheme and url.scheme != "file":
            self.app.open_url(location)


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
