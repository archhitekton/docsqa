#!/usr/bin/env python3
"""Download corpus PDFs from corpus.csv into ./docs/"""

import csv
import os
from pathlib import Path
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_corpus():
    """Download PDFs from corpus.csv into ./docs/ directory."""
    corpus_path = Path("corpus.csv")
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    if not corpus_path.exists():
        logger.error(f"corpus.csv not found at {corpus_path.absolute()}")
        return

    with open(corpus_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row["title"]
            url = row["pdf_url"]

            # Replace spaces with underscores in filename
            filename = title.replace(" ", "_") + ".pdf"
            filepath = docs_dir / filename

            if filepath.exists():
                logger.info(f"Skipped (exists): {title}")
                continue

            try:
                logger.info(f"Downloading: {title}")
                response = requests.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    stream=True,
                    timeout=30,
                )
                response.raise_for_status()

                with open(filepath, "wb") as pdf:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            pdf.write(chunk)

                logger.info(f"Downloaded: {title}")

            except requests.RequestException as e:
                logger.error(f"Failed to download {title}: {e}")
                if filepath.exists():
                    filepath.unlink()


if __name__ == "__main__":
    seed_corpus()
    print(f"✓ Corpus ready in ./docs/ — run 'make ingest' next")
