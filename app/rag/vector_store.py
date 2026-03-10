"""
FAISS Vector Store for RAG policy matching.
Uses sentence-transformers for embeddings and FAISS for similarity search.
"""
import os
import numpy as np
from typing import List, Dict, Any, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


class FAISSVectorStore:
    """Vector store using FAISS for policy document retrieval."""

    def __init__(self, embedding_model: str = 'all-MiniLM-L6-v2', index_path: str = None):
        self.embedding_model_name = embedding_model
        self.index_path = index_path
        self._model = None
        self._index = None
        self._documents: List[Dict[str, Any]] = []
        self._dimension = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        return self._model

    def build_index(self, documents: List[Dict[str, Any]]):
        """Build FAISS index from documents. Each doc needs 'text' field."""
        import faiss

        texts = [doc['text'] for doc in documents]
        embeddings = self.model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype='float32')

        self._dimension = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(self._dimension)  # Inner product (cosine with normalized vectors)

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        self._index.add(embeddings)

        self._documents = documents
        logger.info(f"Built FAISS index: {len(documents)} documents, dim={self._dimension}")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for most similar documents."""
        if self._index is None or not self._documents:
            return []

        import faiss

        query_embedding = self.model.encode([query], show_progress_bar=False)
        query_embedding = np.array(query_embedding, dtype='float32')
        faiss.normalize_L2(query_embedding)

        scores, indices = self._index.search(query_embedding, min(top_k, len(self._documents)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._documents):
                doc = self._documents[idx].copy()
                doc['similarity_score'] = float(score)
                results.append(doc)

        return results

    def save(self, path: str = None):
        """Save FAISS index to disk."""
        save_path = path or self.index_path
        if not save_path or self._index is None:
            return

        import faiss
        import json

        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
        faiss.write_index(self._index, save_path)

        # Save documents metadata
        meta_path = save_path + '.meta.json'
        with open(meta_path, 'w') as f:
            json.dump(self._documents, f)

        logger.info(f"Saved FAISS index to {save_path}")

    def load(self, path: str = None) -> bool:
        """Load FAISS index from disk."""
        load_path = path or self.index_path
        if not load_path or not os.path.exists(load_path):
            return False

        try:
            import faiss
            import json

            self._index = faiss.read_index(load_path)
            self._dimension = self._index.d

            meta_path = load_path + '.meta.json'
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    self._documents = json.load(f)

            logger.info(f"Loaded FAISS index from {load_path}: {self._index.ntotal} vectors")
            return True

        except Exception as e:
            logger.warning(f"Failed to load FAISS index: {e}")
            return False
