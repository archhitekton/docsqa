import re
import tiktoken
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """Markdown section with heading path."""
    heading_path: str
    text: str


@dataclass
class Chunk:
    """Text chunk with metadata."""
    heading_path: str
    text: str


def parse_sections(markdown: str) -> list[Section]:
    """Parse markdown into sections by H1-H3 heading boundaries.

    Returns list of Section(heading_path, text) where heading_path is
    the breadcrumb trail of headings containing the section.
    """
    sections = []
    current_heading_path = ""
    current_text_lines = []

    heading_stack = []  # Track active heading levels: [("# title", 1), ("## subtitle", 2)]

    for line in markdown.split("\n"):
        # Match H1-H3 headings
        match = re.match(r"^(#{1,3})\s+(.+)$", line)

        if match:
            # Save previous section if it has text
            if current_text_lines:
                text = "\n".join(current_text_lines).strip()
                if text:
                    sections.append(Section(heading_path=current_heading_path, text=text))
                current_text_lines = []

            # Update heading stack
            level = len(match.group(1))  # 1 for #, 2 for ##, 3 for ###
            title = match.group(2).strip()

            # Remove headings of same or greater level from stack
            heading_stack = [(h, l) for h, l in heading_stack if l < level]
            heading_stack.append((title, level))

            # Build heading path from stack
            current_heading_path = " > ".join([h for h, _ in heading_stack])
        else:
            # Regular content line
            current_text_lines.append(line)

    # Save final section
    if current_text_lines:
        text = "\n".join(current_text_lines).strip()
        if text:
            sections.append(Section(heading_path=current_heading_path, text=text))

    logger.debug(f"Parsed {len(sections)} sections from markdown")
    return sections


def chunk_section(section: Section, max_tokens: int = 500, overlap: int = 50) -> list[Chunk]:
    """Chunk a section using sliding window on tokens.

    If section fits in max_tokens, returns single chunk.
    Otherwise applies sliding window with step = max_tokens - overlap.
    """
    text = section.text.strip()
    if not text:
        return []

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    if len(tokens) <= max_tokens:
        # Fits in one chunk
        return [Chunk(heading_path=section.heading_path, text=text)]

    # Sliding window
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens).strip()

        if chunk_text:
            chunks.append(Chunk(heading_path=section.heading_path, text=chunk_text))

        # Advance by (max_tokens - overlap)
        start = end - overlap

        # Prevent infinite loop: if we can't advance, break
        if start <= 0 or start >= len(tokens):
            break

    return chunks


def chunk_document(markdown: str, max_tokens: int = 500, overlap: int = 50) -> list[Chunk]:
    """Convert markdown document to list of chunks.

    1. Parse into sections (split on H1-H3 boundaries)
    2. Chunk each section (sliding window within section)
    Result: chunks never span two headings.
    """
    sections = parse_sections(markdown)

    chunks = []
    for section in sections:
        section_chunks = chunk_section(section, max_tokens=max_tokens, overlap=overlap)
        chunks.extend(section_chunks)

    logger.info(f"Created {len(chunks)} chunks from {len(sections)} sections")
    return chunks
