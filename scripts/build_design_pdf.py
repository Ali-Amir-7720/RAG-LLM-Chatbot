from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fpdf import FPDF  # fpdf2


@dataclass(frozen=True)
class Style:
    font: str
    size: int
    leading: float


STYLES = {
    # Fonts are registered in build_pdf(); use only registered family names here.
    "title": Style("UI", 18, 1.35),
    "h1": Style("UI", 16, 1.35),
    "h2": Style("UI", 13, 1.45),
    "h3": Style("UI", 11, 1.45),
    "body": Style("UI", 10, 1.55),
    "code": Style("Mono", 9, 1.45),
}


class Pdf(FPDF):
    def header(self) -> None:
        # Keep header minimal; title is rendered from content.
        self.set_draw_color(230, 230, 230)
        self.set_line_width(0.2)
        self.line(self.l_margin, 12, self.w - self.r_margin, 12)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("UI", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"{self.page_no()}", align="C")


def iter_blocks(md_lines: Iterable[str]) -> Iterable[tuple[str, list[str]]]:
    """
    Very small markdown block parser (headings, lists, code fences, paragraphs).
    Returns (kind, lines).
    """
    buf: list[str] = []
    in_code = False

    def flush_paragraph() -> tuple[str, list[str]] | None:
        nonlocal buf
        if not buf:
            return None
        out = ("p", buf)
        buf = []
        return out

    for raw in md_lines:
        line = raw.rstrip("\n")

        if line.strip().startswith("```"):
            if in_code:
                # end code
                in_code = False
                yield ("code", buf)
                buf = []
                continue

            # start code
            maybe_para = flush_paragraph()
            if maybe_para:
                yield maybe_para
            in_code = True
            buf = []
            continue

        if in_code:
            buf.append(line)
            continue

        if not line.strip():
            maybe_para = flush_paragraph()
            if maybe_para:
                yield maybe_para
            continue

        if line.startswith("# "):
            maybe_para = flush_paragraph()
            if maybe_para:
                yield maybe_para
            yield ("h1", [line[2:].strip()])
            continue
        if line.startswith("## "):
            maybe_para = flush_paragraph()
            if maybe_para:
                yield maybe_para
            yield ("h2", [line[3:].strip()])
            continue
        if line.startswith("### "):
            maybe_para = flush_paragraph()
            if maybe_para:
                yield maybe_para
            yield ("h3", [line[4:].strip()])
            continue

        if line.startswith("---"):
            maybe_para = flush_paragraph()
            if maybe_para:
                yield maybe_para
            yield ("hr", [])
            continue

        if line.startswith("- ") or line.startswith("  - "):
            # list item(s): gather contiguous list lines
            maybe_para = flush_paragraph()
            if maybe_para:
                yield maybe_para
            items = [line]
            continue_list = True
            # NOTE: we cannot "peek" easily without reading ahead, so we store and
            # handle list aggregation outside; simplest approach is to treat each
            # list line as its own block and keep rendering consistent.
            yield ("li", items)
            continue

        # default paragraph line
        buf.append(line)

    if in_code and buf:
        yield ("code", buf)
        buf = []
    maybe_para = flush_paragraph()
    if maybe_para:
        yield maybe_para


def strip_inline_md(text: str) -> str:
    # Keep it intentionally simple: remove backticks and bold markers.
    return (
        text.replace("**", "")
        .replace("`", "")
    )


def write_heading(pdf: Pdf, text: str, level: str) -> None:
    style = STYLES[level]
    pdf.ln(4)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font(style.font, "B", style.size)
    pdf.multi_cell(0, style.size * 0.45 * style.leading, strip_inline_md(text))
    pdf.ln(1)


def write_paragraph(pdf: Pdf, lines: list[str]) -> None:
    style = STYLES["body"]
    pdf.set_text_color(40, 40, 40)
    pdf.set_font(style.font, "", style.size)
    text = strip_inline_md(" ".join(line.strip() for line in lines))
    pdf.multi_cell(0, style.size * 0.45 * style.leading, text)
    pdf.ln(1)


def write_list_item(pdf: Pdf, line: str) -> None:
    style = STYLES["body"]
    indent = 4 if line.startswith("  - ") else 0
    content = line[4:] if indent else line[2:]
    content = strip_inline_md(content.strip())

    pdf.set_font(style.font, "", style.size)
    pdf.set_text_color(40, 40, 40)

    x = pdf.get_x()
    y = pdf.get_y()
    pdf.set_x(x + indent)
    pdf.cell(3, style.size * 0.45 * style.leading, chr(8226))  # bullet
    pdf.set_x(x + indent + 4)
    pdf.multi_cell(0, style.size * 0.45 * style.leading, content)
    pdf.set_xy(x, max(y, pdf.get_y()))
    pdf.ln(0.5)


def write_code(pdf: Pdf, lines: list[str]) -> None:
    style = STYLES["code"]
    pdf.ln(1.5)
    pdf.set_fill_color(248, 248, 248)
    pdf.set_draw_color(230, 230, 230)
    pdf.set_font(style.font, "", style.size)
    pdf.set_text_color(20, 20, 20)

    # Draw a light box by using a filled multicell with borders.
    text = "\n".join(lines).rstrip()
    if not text:
        return
    pdf.multi_cell(
        0,
        style.size * 0.45 * style.leading,
        text,
        border=1,
        fill=True,
    )
    pdf.ln(1.5)


def write_hr(pdf: Pdf) -> None:
    pdf.ln(2)
    pdf.set_draw_color(220, 220, 220)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)


def build_pdf(md_path: Path, pdf_path: Path) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    lines = md_text.splitlines()

    pdf = Pdf(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(left=14, top=16, right=14)
    pdf.add_page()

    # Register Unicode fonts (Windows system fonts).
    # These cover curly quotes, dashes, bullets, etc. which core PDF fonts can't.
    fonts_dir = Path(r"C:\Windows\Fonts")
    ui_regular = fonts_dir / "segoeui.ttf"
    ui_bold = fonts_dir / "segoeuib.ttf"
    mono_regular = fonts_dir / "consola.ttf"

    if not ui_regular.exists():
        raise SystemExit(f"Missing font: {ui_regular}")
    if not ui_bold.exists():
        raise SystemExit(f"Missing font: {ui_bold}")
    if not mono_regular.exists():
        raise SystemExit(f"Missing font: {mono_regular}")

    pdf.add_font("UI", style="", fname=str(ui_regular))
    pdf.add_font("UI", style="B", fname=str(ui_bold))
    pdf.add_font("Mono", style="", fname=str(mono_regular))

    # Title: first H1 becomes "title" style.
    first_h1_used = False

    for kind, block_lines in iter_blocks(lines):
        if kind == "h1":
            if not first_h1_used:
                write_heading(pdf, block_lines[0], "title")
                first_h1_used = True
            else:
                write_heading(pdf, block_lines[0], "h1")
            continue
        if kind == "h2":
            write_heading(pdf, block_lines[0], "h2")
            continue
        if kind == "h3":
            write_heading(pdf, block_lines[0], "h3")
            continue
        if kind == "p":
            write_paragraph(pdf, block_lines)
            continue
        if kind == "li":
            write_list_item(pdf, block_lines[0])
            continue
        if kind == "code":
            write_code(pdf, block_lines)
            continue
        if kind == "hr":
            write_hr(pdf)
            continue

    pdf.output(str(pdf_path))


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    md_path = repo_root / "docs" / "rag_llm_workflow.md"
    pdf_path = repo_root / "docs" / "rag_llm_workflow.pdf"

    if not md_path.exists():
        raise SystemExit(f"Missing input markdown: {md_path}")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(md_path, pdf_path)
    print(f"Wrote: {pdf_path}")


if __name__ == "__main__":
    main()

