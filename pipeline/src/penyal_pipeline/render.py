"""Plain-text table rendering for CLI output."""

from collections.abc import Sequence


def format_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render rows as a left-aligned table with a header rule."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def line(cells: Sequence[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

    rule = "  ".join("-" * w for w in widths)
    return "\n".join([line(headers), rule, *(line(r) for r in rows)])


def human_bytes(n: int) -> str:
    """Format a byte count using decimal units (matches HTTP Content-Length reporting)."""
    value = float(n)
    for unit in ("B", "kB", "MB", "GB"):
        if value < 1000 or unit == "GB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1000
    raise AssertionError("unreachable")
