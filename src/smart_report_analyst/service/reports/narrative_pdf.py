"""Render markdown narrative text to PDF bytes using markdown-pdf (markdown-it-py + PyMuPDF).

Used by the ``generate_report_pdf`` Strands tool and the permanent save route to convert
report_builder output into a downloadable PDF.
"""

from __future__ import annotations

import io

from markdown_pdf import MarkdownPdf, Section


_CSS = """
body {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
}
h1 { font-size: 20pt; font-weight: bold; margin-bottom: 6pt; color: #0d2b52; }
h2 { font-size: 15pt; font-weight: bold; margin-top: 18pt; margin-bottom: 4pt; color: #0d2b52; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
h3 { font-size: 13pt; font-weight: bold; margin-top: 12pt; color: #1a3a6b; }
p  { margin: 6pt 0; }
ul, ol { margin: 6pt 0 6pt 18pt; padding: 0; }
li { margin-bottom: 3pt; }
table { border-collapse: collapse; width: 100%; margin: 10pt 0; font-size: 10pt; }
th { background: #0d2b52; color: white; padding: 5pt 8pt; text-align: left; }
td { border: 1px solid #ccc; padding: 4pt 8pt; }
tr:nth-child(even) td { background: #f4f6fa; }
code { background: #f0f0f0; padding: 1pt 4pt; border-radius: 2pt; font-size: 10pt; }
pre  { background: #f5f5f5; padding: 8pt; border-radius: 4pt; font-size: 9.5pt; overflow-x: auto; }
blockquote { border-left: 3px solid #0d2b52; margin: 8pt 0 8pt 8pt; padding-left: 12pt; color: #444; }
"""


def render_narrative_pdf(markdown_content: str, title: str = "") -> bytes:
    """Convert markdown text to PDF bytes.

    Args:
        markdown_content: Full markdown text (may include Title, Intro, Body, Summary sections).
        title: Optional document metadata title (embedded in PDF properties).

    Returns:
        Raw PDF bytes.
    """
    pdf = MarkdownPdf(toc_level=2)
    if title:
        pdf.meta["title"] = title
        pdf.meta["author"] = "Smart Report Analyst"

    pdf.add_section(Section(markdown_content, paper_size="A4"), user_css=_CSS)

    buf = io.BytesIO()
    pdf.save_bytes(buf)
    return buf.getvalue()
