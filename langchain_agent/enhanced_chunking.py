"""Enhanced chunking strategies for different document types and use cases.

This module provides intelligent chunking strategies that respect document structure,
semantic boundaries, and content type. It replaces the simple character-based
chunking with more sophisticated approaches.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

__all__ = [
    "ChunkingStrategy",
    "CharacterChunking",
    "SemanticChunking",
    "FileTypeChunking",
    "AdaptiveChunking",
    "chunk_document",
]


class ChunkingMode(Enum):
    """Different chunking modes for different use cases."""

    TRANSLATION = "translation"  # Large chunks for translation
    RAG = "rag"  # Small chunks for retrieval
    ANALYSIS = "analysis"  # Medium chunks for analysis
    SUMMARIZATION = "summarization"  # Variable chunks for summarization
    EXTRACTION = "extraction"  # Small chunks for precise extraction
    COMPARISON = "comparison"  # Balanced chunks for document comparison


@dataclass
class ChunkingConfig:
    """Configuration for chunking strategies."""

    mode: ChunkingMode = ChunkingMode.RAG
    max_chars: int = 20_000
    overlap: int = 200
    respect_sentences: bool = True
    respect_paragraphs: bool = True
    min_chunk_size: int = 1000
    max_chunk_size: int = 100_000


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str, config: ChunkingConfig) -> List[str]:
        """Chunk the text according to the strategy."""
        pass


class CharacterChunking(ChunkingStrategy):
    """Simple character-based chunking (original strategy)."""

    def chunk(self, text: str, config: ChunkingConfig) -> List[str]:
        """Break text into fixed-size character chunks with overlap."""
        if not text:
            return []

        chunks = []
        start = 0
        length = len(text)

        while start < length:
            end = min(start + config.max_chars, length)
            chunk = text[start:end]

            # Only add chunk if it meets minimum size
            if len(chunk) >= config.min_chunk_size:
                chunks.append(chunk)

            # Compute next start position with overlap
            if end == length:
                break
            start = end - config.overlap
            if start < 0:
                start = 0

        return chunks


class SemanticChunking(ChunkingStrategy):
    """Semantic-aware chunking that respects sentence and paragraph boundaries."""

    def chunk(self, text: str, config: ChunkingConfig) -> List[str]:
        """Chunk text while respecting semantic boundaries."""
        if not text:
            return []

        # Split into paragraphs first
        paragraphs = self._split_paragraphs(text)

        if config.mode == ChunkingMode.TRANSLATION:
            return self._chunk_for_translation(paragraphs, config)
        elif config.mode == ChunkingMode.RAG:
            return self._chunk_for_rag(paragraphs, config)
        elif config.mode == ChunkingMode.ANALYSIS:
            return self._chunk_for_analysis(paragraphs, config)
        elif config.mode == ChunkingMode.SUMMARIZATION:
            return self._chunk_for_summarization(paragraphs, config)
        elif config.mode == ChunkingMode.EXTRACTION:
            return self._chunk_for_extraction(paragraphs, config)
        elif config.mode == ChunkingMode.COMPARISON:
            return self._chunk_for_comparison(paragraphs, config)
        else:
            return self._chunk_for_analysis(paragraphs, config)

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split by double newlines or significant whitespace
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        # More sophisticated sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _chunk_for_translation(self, paragraphs: List[str], config: ChunkingConfig) -> List[str]:
        """Create large chunks for translation tasks."""
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # If adding this paragraph would exceed max size, start new chunk
            if len(current_chunk) + len(paragraph) > config.max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _chunk_for_rag(self, paragraphs: List[str], config: ChunkingConfig) -> List[str]:
        """Create small, overlapping chunks for RAG tasks."""
        chunks = []

        for paragraph in paragraphs:
            if len(paragraph) <= config.max_chars:
                # Paragraph fits in one chunk
                chunks.append(paragraph)
            else:
                # Paragraph needs to be split
                sentences = self._split_sentences(paragraph)
                current_chunk = ""

                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > config.max_chars:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence

                # Add the last chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())

        return chunks

    def _chunk_for_analysis(self, paragraphs: List[str], config: ChunkingConfig) -> List[str]:
        """Create medium-sized chunks for analysis tasks."""
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # For analysis, we want medium-sized chunks
            if len(current_chunk) + len(paragraph) > config.max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _chunk_for_summarization(self, paragraphs: List[str], config: ChunkingConfig) -> List[str]:
        """Create variable-sized chunks optimized for summarization."""
        # For summarization, we want coherent sections that maintain logical flow
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # Allow larger chunks for better context in summarization
            max_summary_chars = min(config.max_chars * 2, 50_000)
            if len(current_chunk) + len(paragraph) > max_summary_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _chunk_for_extraction(self, paragraphs: List[str], config: ChunkingConfig) -> List[str]:
        """Create small, precise chunks for content extraction."""
        chunks = []

        for paragraph in paragraphs:
            # For extraction, split into sentences for precision
            sentences = self._split_sentences(paragraph)
            current_chunk = ""

            for sentence in sentences:
                # Keep chunks small for precise extraction
                extraction_max_chars = min(config.max_chars, 5_000)
                if len(current_chunk) + len(sentence) > extraction_max_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence if current_chunk else sentence

            # Add the last chunk from this paragraph
            if current_chunk:
                chunks.append(current_chunk.strip())

        return chunks

    def _chunk_for_comparison(self, paragraphs: List[str], config: ChunkingConfig) -> List[str]:
        """Create balanced chunks for document comparison."""
        # Similar to analysis but with consistent sizing for fair comparison
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # Medium-sized chunks for balanced comparison
            if len(current_chunk) + len(paragraph) > config.max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


class FileTypeChunking(ChunkingStrategy):
    """File-type aware chunking that uses different strategies for different formats."""

    def __init__(self):
        self.strategies = {
            "pdf": self._chunk_pdf,
            "pptx": self._chunk_presentation,
            "json": self._chunk_json,
            "txt": self._chunk_text,
            "default": self._chunk_text,
        }

    def chunk(self, text: str, config: ChunkingConfig, file_type: str = "default") -> List[str]:
        """Chunk text based on file type."""
        strategy = self.strategies.get(file_type.lower(), self.strategies["default"])
        return strategy(text, config)

    def _chunk_pdf(self, text: str, config: ChunkingConfig) -> List[str]:
        """Chunk PDF text respecting page boundaries."""
        # PDF text often has page markers or clear page separations
        pages = re.split(r"\n\s*Page \d+\s*\n", text)
        if len(pages) == 1:
            # No clear page markers, fall back to semantic chunking
            semantic_chunker = SemanticChunking()
            return semantic_chunker.chunk(text, config)

        chunks = []
        for page in pages:
            if page.strip():
                # Chunk each page separately
                semantic_chunker = SemanticChunking()
                page_chunks = semantic_chunker.chunk(page.strip(), config)
                chunks.extend(page_chunks)

        return chunks

    def _chunk_presentation(self, text: str, config: ChunkingConfig) -> List[str]:
        """Chunk presentation text respecting slide boundaries."""
        # PowerPoint text often has slide markers
        slides = re.split(r"\n\s*Slide \d+\s*\n", text)
        if len(slides) == 1:
            # No clear slide markers, fall back to semantic chunking
            semantic_chunker = SemanticChunking()
            return semantic_chunker.chunk(text, config)

        chunks = []
        for slide in slides:
            if slide.strip():
                # Each slide becomes a chunk for presentations
                chunks.append(slide.strip())

        return chunks

    def _chunk_json(self, text: str, config: ChunkingConfig) -> List[str]:
        """Chunk JSON text respecting object boundaries."""
        try:
            import json

            data = json.loads(text)
            if isinstance(data, list):
                # For arrays, chunk by items
                chunks = []
                current_chunk = ""
                for item in data:
                    item_str = json.dumps(item, ensure_ascii=False)
                    if len(current_chunk) + len(item_str) > config.max_chars:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = item_str
                    else:
                        current_chunk += "\n" + item_str if current_chunk else item_str

                if current_chunk:
                    chunks.append(current_chunk.strip())
                return chunks
            else:
                # For single objects, use semantic chunking
                semantic_chunker = SemanticChunking()
                return semantic_chunker.chunk(text, config)
        except json.JSONDecodeError:
            # Fall back to semantic chunking if JSON parsing fails
            semantic_chunker = SemanticChunking()
            return semantic_chunker.chunk(text, config)

    def _chunk_text(self, text: str, config: ChunkingConfig) -> List[str]:
        """Chunk plain text using semantic chunking."""
        semantic_chunker = SemanticChunking()
        return semantic_chunker.chunk(text, config)


class AdaptiveChunking(ChunkingStrategy):
    """Adaptive chunking that adjusts strategy based on content analysis."""

    def chunk(self, text: str, config: ChunkingConfig) -> List[str]:
        """Adaptively choose the best chunking strategy."""
        # Analyze text characteristics
        text_stats = self._analyze_text(text)

        # Choose strategy based on analysis
        if text_stats["avg_paragraph_length"] > 5000:
            # Very long paragraphs, use character chunking
            strategy = CharacterChunking()
        elif text_stats["paragraph_count"] < 5:
            # Few paragraphs, use semantic chunking
            strategy = SemanticChunking()
        else:
            # Mixed content, use semantic chunking
            strategy = SemanticChunking()

        return strategy.chunk(text, config)

    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text characteristics to inform chunking strategy."""
        paragraphs = re.split(r"\n\s*\n", text)
        sentences = re.split(r"(?<=[.!?])\s+", text)

        return {
            "total_length": len(text),
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences),
            "avg_paragraph_length": len(text) / max(len(paragraphs), 1),
            "avg_sentence_length": len(text) / max(len(sentences), 1),
            "has_structure_markers": bool(re.search(r"(Page|Slide|Chapter|Section)", text)),
        }


def get_file_type(file_path: str) -> str:
    """Detect file type from path and content analysis."""
    if not file_path:
        return "txt"

    # Get extension
    ext = file_path.split(".")[-1].lower() if "." in file_path else "txt"

    # Map common extensions
    extension_map = {
        "pdf": "pdf",
        "pptx": "pptx",
        "ppt": "pptx",  # Handle older PowerPoint format
        "json": "json",
        "txt": "txt",
        "md": "txt",  # Markdown as text
        "rst": "txt",  # ReStructuredText as text
        "csv": "txt",  # CSV as text for now
        "xml": "txt",  # XML as text for now
    }

    return extension_map.get(ext, "txt")


def chunk_document(
    text: str, file_type: str = "txt", mode: ChunkingMode = ChunkingMode.RAG, config: Optional[ChunkingConfig] = None
) -> List[str]:
    """Main function to chunk documents using the best strategy."""

    if config is None:
        config = ChunkingConfig(mode=mode)

    # Normalize file type
    file_type = file_type.lower()

    # Print chunking strategy info
    print(f"🎯 Using {mode.value} chunking mode for {file_type.upper()} file")
    print(f"📏 Target chunk size: {config.max_chars:,} characters")

    # Choose chunking strategy based on file type and mode
    if file_type in ["pdf", "pptx", "json"]:
        print(f"🔧 Using file-type specific chunking for {file_type.upper()}")
        chunker = FileTypeChunking()
        chunks = chunker.chunk(text, config, file_type)
    elif mode == ChunkingMode.TRANSLATION:
        # For translation, use semantic chunking with large chunks
        config.max_chars = min(config.max_chars, 100_000)
        print("🔧 Using semantic chunking optimized for translation")
        chunker = SemanticChunking()
        chunks = chunker.chunk(text, config)
    else:
        # For other cases, use adaptive chunking
        print("🔧 Using adaptive chunking strategy")
        chunker = AdaptiveChunking()
        chunks = chunker.chunk(text, config)

    # Print chunking results
    if chunks:
        avg_chunk_size = sum(len(chunk) for chunk in chunks) / len(chunks)
        print(f"📊 Chunking complete: {len(chunks)} chunks, avg size: {avg_chunk_size:,.0f} chars")
        print(f"📈 Chunk size range: {min(len(chunk) for chunk in chunks):,} - {max(len(chunk) for chunk in chunks):,} chars")
    else:
        print("⚠️  No chunks created - document may be empty or too small")

    return chunks
