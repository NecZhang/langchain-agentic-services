"""A very simple intent recogniser for user queries.

This module exports a single function, :func:`detect_intent`, which
examines a user query and attempts to classify it into one of a
predefined set of task types.  For this prototype we only
distinguish between translation requests and question answering
(retrieval‑augmented generation).  The logic is deliberately simple
and rule based; you may wish to replace it with a more sophisticated
classifier or a call to an LLM for a production system.
"""

from __future__ import annotations

from typing import Literal

__all__ = ["detect_intent"]


def detect_intent(query: str) -> Literal["translate", "qa", "summarize", "analyze", "extract", "compare"]:
    """Determine the user's intent from their query.

    The function lowers the query string and searches for key phrases
    indicating different intents. It checks for translation, summarization,
    analysis, extraction, and comparison requests, defaulting to Q&A.

    Parameters
    ----------
    query : str
        The user's query string.

    Returns
    -------
    Literal["translate", "qa", "summarize", "analyze", "extract", "compare"]
        The detected intent.
    """
    q = (query or "").lower()

    # Translation markers
    translation_markers = [
        "translate",
        "translation",
        "translate this",
        "translate the file",
        "please translate",
        "convert to",
        "in english",
        "in chinese",
    ]
    for marker in translation_markers:
        if marker in q:
            return "translate"

    # Summarization markers
    summarization_markers = [
        "summarize",
        "summary",
        "summarise",
        "key points",
        "main points",
        "executive summary",
        "brief",
        "overview",
        "gist",
        "essence",
    ]
    for marker in summarization_markers:
        if marker in q:
            return "summarize"

    # Analysis markers
    analysis_markers = [
        "analyze",
        "analyse",
        "analysis",
        "insights",
        "trends",
        "patterns",
        "examine",
        "evaluate",
        "assess",
        "review",
        "interpret",
        "findings",
    ]
    for marker in analysis_markers:
        if marker in q:
            return "analyze"

    # Extraction markers
    extraction_markers = [
        "extract",
        "find all",
        "list all",
        "get all",
        "identify",
        "pull out",
        "collect",
        "gather",
        "retrieve",
        "locate",
    ]
    for marker in extraction_markers:
        if marker in q:
            return "extract"

    # Comparison markers
    comparison_markers = [
        "compare",
        "comparison",
        "contrast",
        "difference",
        "differences",
        "similar",
        "similarities",
        "versus",
        "vs",
        "against",
        "between",
    ]
    for marker in comparison_markers:
        if marker in q:
            return "compare"

    # Default to Q&A
    return "qa"
