"""Simplified utilities for retrieval‑augmented generation (RAG).

This module implements basic chunking of large documents and a very
simple retrieval mechanism built on top of scikit‑learn's TF‑IDF
vectoriser and nearest neighbour search.  It is intended as a stand‑in
for full featured vector stores and embedding models when such
components are not available.  Because we cannot rely on external
libraries, these utilities operate purely on plain text.
"""

from __future__ import annotations

import json
import os
from typing import List, Tuple, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

__all__ = ["chunk_text", "RAGRetriever"]


def chunk_text(text: str, max_chars: int = 500_000, overlap: int = 200) -> List[str]:
    """Break a long string into overlapping chunks.

    Since we do not have access to a tokeniser, this function uses
    character counts to approximate token budgets.  It simply slices
    the input text at fixed intervals and introduces a configurable
    overlap between consecutive chunks.  The overlap helps the model
    capture context across boundaries.

    Parameters
    ----------
    text : str
        The text to be split.
    max_chars : int, optional
        Maximum number of characters per chunk.  Defaults to 500,000
        characters (roughly equivalent to 125k tokens assuming 4
        characters per token).
    overlap : int, optional
        Number of characters to repeat at the start of each chunk (except
        the first) to provide continuity.  Defaults to 200 characters.

    Returns
    -------
    List[str]
        A list of text chunks.
    """
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        chunk = text[start:end]
        chunks.append(chunk)
        # compute next start position with overlap
        if end == length:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


@dataclass
class RAGRetriever:
    """A tiny vector store and retriever for question answering.

    This class takes a list of strings (documents) on construction and
    uses a TF‑IDF vectoriser to embed them.  At query time it embeds
    the question using the same vectoriser and performs nearest
    neighbour search to identify the most relevant chunks.  It returns
    the indices of the top chunks along with their cosine distances.

    Parameters
    ----------
    texts : List[str]
        A list of pre‑chunked document strings to be indexed.
    max_features : int, optional
        Limits the vocabulary size of the TF‑IDF vectoriser.  A
        reasonable default of 50k features is used to keep memory
        footprint manageable.
    vectorizer : Optional[TfidfVectorizer]
        Preloaded vectorizer (if loading from cache).
    doc_vectors : Optional[np.ndarray]
        Precomputed document vectors (if loading from cache).
    nn : Optional[NearestNeighbors]
        Prebuilt NN index (if loading from cache).
    """

    texts: List[str]
    max_features: int = 50_000
    vectorizer: Optional[TfidfVectorizer] = None
    doc_vectors: Optional[any] = None
    nn: Optional[NearestNeighbors] = None

    def __post_init__(self) -> None:
        # If cache provided, assume ready
        if self.vectorizer is not None and self.doc_vectors is not None and self.nn is not None:
            return
        # Initialise the TF‑IDF vectoriser and fit on the documents
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=self.max_features)
        self.doc_vectors = self.vectorizer.fit_transform(self.texts)
        # Build a nearest neighbour index; metric='cosine' returns
        # distances in the range [0, 2] where smaller is better
        self.nn = NearestNeighbors(n_neighbors=min(3, len(self.texts)), metric="cosine")
        self.nn.fit(self.doc_vectors)

    def query(self, question: str, k: int = 3) -> List[Tuple[int, float]]:
        """Retrieve the indices of the ``k`` most similar documents.

        Parameters
        ----------
        question : str
            The user's question.
        k : int, optional
            Number of neighbours to return.  Defaults to 3.  If fewer
            documents are available, it returns as many as possible.

        Returns
        -------
        List[Tuple[int, float]]
            A list of tuples ``(index, distance)`` sorted by ascending
            distance (i.e. most similar first).
        """
        if not question:
            return []
        k = min(k, len(self.texts))
        query_vec = self.vectorizer.transform([question])
        distances, indices = self.nn.kneighbors(query_vec, n_neighbors=k)
        # Flatten arrays and zip together
        results = list(zip(indices[0].tolist(), distances[0].tolist()))
        # Already sorted by the knn implementation
        return results
