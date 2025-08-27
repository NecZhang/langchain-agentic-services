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
    
    # Define intent patterns with their markers
    intent_patterns = {
        "translate": [
            "translate", "translation", "translate this", "translate the file",
            "please translate", "convert to", "in english", "in chinese"
        ],
        "summarize": [
            "summarize", "summary", "summarise", "key points", "main points",
            "executive summary", "brief", "overview", "gist", "essence"
        ],
        "analyze": [
            "analyze", "analyse", "analysis", "insights", "trends", "patterns",
            "examine", "evaluate", "assess", "review", "interpret", "findings"
        ],
        "extract": [
            "extract", "find all", "list all", "get all", "identify",
            "pull out", "collect", "gather", "retrieve", "locate"
        ],
        "compare": [
            "compare", "comparison", "contrast", "difference", "differences",
            "similar", "similarities", "versus", "vs", "against", "match"
        ]
    }
    
    # Check each intent pattern
    for intent, markers in intent_patterns.items():
        if any(marker in q for marker in markers):
            return intent
    
    # Default to Q&A
    return "qa"
