"""DataTable widget for displaying and selecting chains."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable


class ChainList(Widget):
    """A DataTable-based chain browser widget."""

    DEFAULT_CSS = """
    ChainList {
        height: 1fr;
    }
    ChainList DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        table: DataTable = DataTable(id="chains-table", cursor_type="row")
        table.add_columns("Name", "Steps", "Conf.", "Type")
        yield table

    def load_chains(self, chains: list) -> None:
        """Populate the table from a list of Chain objects."""
        table = self.query_one("#chains-table", DataTable)
        table.clear()
        for i, chain in enumerate(chains):
            chain_type = "IDOR" if chain.is_multi_profile else "Regular"
            table.add_row(
                chain.name or f"chain-{i}",
                str(len(chain.steps)),
                f"{chain.confidence:.2f}",
                chain_type,
                key=str(i),
            )

    def get_selected_index(self) -> int | None:
        """Return the row index of the currently highlighted row."""
        try:
            table = self.query_one("#chains-table", DataTable)
            row_key = table.cursor_row
            return row_key
        except Exception:
            return None
