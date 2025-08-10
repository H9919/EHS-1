# services/embeddings.py - FIXED VERSION with clean logging and proper SBERT gating
import os
import numpy as np
from functools import lru_cache

# Check if SBERT should be enabled
ENABLE_SBERT = os.environ.get('ENABLE_SBERT', 'false').lower() == 'true'
SBERT_AVAILABLE = False

# Only import sentence_transformers if SBERT is enabled
if ENABLE_SBERT:
    try:
        from sentence_transformers import SentenceTransformer
        SBERT_AVAILABLE = True
        print("✓ SBERT embeddings enabled and available")
    except ImportError:
        print("⚠ SBERT requested but not available - using fallback embeddings")
        SBERT_AVAILABLE = False
else:
    # Only log once when module is imported
    print("ℹ SBERT embeddings disabled via environment variable")

@lru_cache(maxsize=1)
def get_model():
    """Get sentence transformer model only if SBERT is available"""
    if not SBERT_AVAILABLE:
        raise ImportError("SBERT not available - embeddings disabled")
    
    # Compact, fast model
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def embed_texts(texts):
    """Embed texts using SBERT if available, otherwise return zero vectors"""
    if not texts:
        return np.zeros((0, 384), dtype="float32")
    
    if not SBERT_AVAILABLE:
        # Return zero vectors as fallback
        return np.zeros((len(texts), 384), dtype="float32")
    
    try:
        model = get_model()
        embs = model.encode(texts, normalize_embeddings=True)
        return np.asarray(embs, dtype="float32")
    except Exception as e:
        print(f"ERROR: Failed to generate embeddings: {e}")
        # Return zero vectors as fallback
        return np.zeros((len(texts), 384), dtype="float32")

def embed_query(q: str):
    """Embed single query string"""
    if not SBERT_AVAILABLE:
        # Return zero vector as fallback
        return np.zeros(384, dtype="float32")
    
    try:
        model = get_model()
        v = model.encode([q], normalize_embeddings=True)[0]
        return np.asarray(v, dtype="float32")
    except Exception as e:
        print(f"ERROR: Failed to generate query embedding: {e}")
        # Return zero vector as fallback
        return np.zeros(384, dtype="float32")

def cosine_sim(a: np.ndarray, b: np.ndarray):
    """Calculate cosine similarity between normalized vectors"""
    try:
        # expects normalized vectors
        return float(np.dot(a, b))
    except Exception as e:
        print(f"ERROR: Failed to calculate cosine similarity: {e}")
        return 0.0

def is_sbert_available():
    """Check if SBERT embeddings are available"""
    return SBERT_AVAILABLE

def get_embedding_dim():
    """Get embedding dimension"""
    return 384  # Standard dimension for all-MiniLM-L6-v2
