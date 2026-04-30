#!/usr/bin/env python3
"""Convert PDFs to Markdown once. One-time preprocessing step."""

import logging
from pathlib import Path
from markitdown import MarkItDown

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def convert_all_pdfs():
    """Convert all PDFs in docs/ to markdown in docs/converted/."""
    docs_dir = Path("docs")
    converted_dir = docs_dir / "converted"
    converted_dir.mkdir(exist_ok=True)

    pdf_files = sorted(docs_dir.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDFs to convert")

    md = MarkItDown()
    converted_count = 0

    for pdf_path in pdf_files:
        md_path = converted_dir / f"{pdf_path.stem}.md"

        # Skip if already converted
        if md_path.exists():
            line_count = len(md_path.read_text().split("\n"))
            logger.info(f"✓ {pdf_path.name} → {line_count} lines (already converted)")
            continue

        logger.info(f"Converting {pdf_path.name}...")
        try:
            result = md.convert(str(pdf_path))
            md_path.write_text(result.text_content, encoding="utf-8")
            line_count = len(result.text_content.split("\n"))
            logger.info(f"✓ {pdf_path.name} → {line_count} lines")
            converted_count += 1
        except Exception as e:
            logger.error(f"Failed to convert {pdf_path.name}: {e}")

    logger.info(f"✓ Conversion complete. Converted {converted_count} new PDFs.")


if __name__ == "__main__":
    convert_all_pdfs()
