from __future__ import annotations

from typing import Iterable, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .schemas import RetrievedChunk, TextChunk


class LocalTfidfRetriever:
    def __init__(self, chunks: Iterable[TextChunk]) -> None:
        self.chunks: List[TextChunk] = list(chunks)
        if not self.chunks:
            raise ValueError("No chunks available for retrieval.")

        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.chunk_texts = [chunk.text for chunk in self.chunks]
        self.matrix = self.vectorizer.fit_transform(self.chunk_texts)

    def search(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix)[0]

        ranked = sorted(
            enumerate(scores),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]

        results: List[RetrievedChunk] = []
        for index, score in ranked:
            chunk = self.chunks[index]
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    page_num=chunk.page_num,
                    text=chunk.text,
                    score=float(score),
                )
            )
        return results
