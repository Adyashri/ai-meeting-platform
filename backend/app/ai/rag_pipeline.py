"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       rag_pipeline.py  —  RAG: Chat With Your Meeting                       ║
║       Owner: Urvashi Waghmare  |  AI/ML Pipeline Lead                       ║
║       Module 7 from the Project Roadmap                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS FILE DOES:
  Implements a Retrieval-Augmented Generation (RAG) pipeline that lets users
  ask natural language questions about their meeting and get accurate answers.

  Example:
    User: "What was decided about the sprint deadline?"
    → RAG finds the 3 most relevant transcript excerpts
    → Gemini reads those excerpts and answers accurately

  This is the same technology used by:
    - Notion AI ("Ask about this document")
    - Microsoft Copilot ("Summarise this meeting")
    - Confluence AI ("Search your wiki")

THE 7-STEP RAG PIPELINE:

  SETUP (runs once after meeting ends, via Celery background task):
    Step 1 — CHUNKING:
      Split the transcript into overlapping chunks of ~5 sentences each.
      Overlap = the last 1 sentence of chunk N is also the first of chunk N+1.
      WHY OVERLAP? Avoids losing context at chunk boundaries.

    Step 2 — EMBEDDING:
      Convert each chunk to a 384-dimensional vector using sentence-transformers.
      Each vector captures the semantic MEANING of the chunk, not just keywords.
      "deadline extension" and "postpone the due date" → similar vectors.

    Step 3 — INDEXING:
      Store all vectors in a FAISS index (fast approximate nearest-neighbor search).
      FAISS can search millions of vectors in milliseconds.
      Save the index to disk as {meeting_id}.index so it persists.

  QUERY (runs each time a user asks a question):
    Step 4 — EMBED QUESTION:
      Convert the user's question to a vector using the same embedding model.

    Step 5 — SEARCH:
      FAISS finds the top-K chunks whose vectors are most similar to the question.
      "Most similar" = smallest cosine distance in 384-dimensional space.

    Step 6 — RETRIEVE:
      Fetch the actual text of those top-K chunks from our stored chunks list.

    Step 7 — GENERATE:
      Send: chunks + question → Gemini
      Gemini reads ONLY those chunks and answers the question from them.
      This prevents hallucination — Gemini can only say what's in the chunks.

INSTALL:
  pip install faiss-cpu
  pip install sentence-transformers
  pip install langchain
  pip install numpy
"""

import logging
import os
import json
import re
import pickle
import time
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  EMBEDDING MODEL MANAGER
#  Loads sentence-transformers model once and caches it.
# ═════════════════════════════════════════════════════════════════════════════

class EmbeddingManager:
    """
    Manages the sentence-transformers embedding model.

    MODEL: all-MiniLM-L6-v2
      - Small (80MB), fast (< 100ms per chunk on CPU)
      - 384 dimensions (good balance of quality vs speed)
      - Trained on 1 billion sentence pairs
      - Free, runs locally — no API calls

    WHY NOT USE GEMINI EMBEDDINGS?
      Gemini embeddings API has rate limits.
      sentence-transformers runs locally — unlimited, instant.
    """

    def __init__(self):
        self._model = None

    def get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading sentence-transformers model...")
                start = time.time()
                # Download ~80MB on first use, cached to ~/.cache/huggingface/
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info(f"✅ Embedding model loaded in {time.time()-start:.1f}s")
            except ImportError:
                logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
                raise
        return self._model

    def embed(self, texts: list) -> np.ndarray:
        """
        Converts a list of text strings into a 2D numpy array of embeddings.

        Args:
            texts: list of strings to embed

        Returns:
            np.ndarray shape: (len(texts), 384)
            Each row is the embedding vector for one text.
        """
        model = self.get_model()
        # convert_to_numpy=True returns numpy array (needed by FAISS)
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.astype("float32")   # FAISS requires float32


# Global embedding manager
embedding_manager = EmbeddingManager()


# ═════════════════════════════════════════════════════════════════════════════
#  SETUP PHASE: BUILD THE FAISS INDEX
#  Called by the Celery worker after a meeting ends.
# ═════════════════════════════════════════════════════════════════════════════

def build_rag_index(meeting_id: int, transcript: str) -> dict:
    """
    Builds and saves the FAISS vector index for a meeting's transcript.
    This is the SETUP phase — run once after the meeting ends.

    Args:
        meeting_id: unique ID of the meeting (used as filename)
        transcript: full meeting transcript text

    Returns:
        dict with build statistics:
        {
            "chunk_count": 47,
            "index_size_bytes": 76248,
            "build_time": 12.3,
            "index_path": "./faiss_store/42.index",
        }
    """
    if not transcript or len(transcript.strip()) < 200:
        logger.warning(f"Transcript too short for RAG indexing: meeting {meeting_id}")
        return {"chunk_count": 0, "error": "Transcript too short"}

    logger.info(f"Building RAG index for meeting {meeting_id}...")
    start_time = time.time()

    # ── Step 1: Chunk the transcript ─────────────────────────────────────────
    chunks = _chunk_transcript(transcript)
    logger.info(f"Created {len(chunks)} chunks from transcript")

    if not chunks:
        return {"chunk_count": 0, "error": "No chunks created"}

    # ── Step 2: Embed all chunks ──────────────────────────────────────────────
    logger.info("Generating embeddings for chunks...")
    embeddings = embedding_manager.embed(chunks)
    # embeddings.shape = (num_chunks, 384)

    # ── Step 3: Build FAISS index ─────────────────────────────────────────────
    import faiss

    # IndexFlatIP = flat index with inner product similarity
    # For normalised vectors, inner product = cosine similarity
    # "Flat" means exhaustive search — exact, not approximate
    # For < 10,000 chunks this is fast enough (< 1ms query time)
    dimension = embeddings.shape[1]   # 384
    index = faiss.IndexFlatIP(dimension)

    # Normalise vectors for cosine similarity
    # (FAISS inner product on normalised vectors = cosine similarity)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    # ── Step 4: Save index and chunks to disk ─────────────────────────────────
    index_path, chunks_path = _get_storage_paths(meeting_id)

    # Save FAISS binary index
    faiss.write_index(index, index_path)

    # Save the actual chunk texts (needed to retrieve text when searching)
    with open(chunks_path, "wb") as f:
        pickle.dump(chunks, f)

    elapsed = time.time() - start_time
    index_size = os.path.getsize(index_path)

    logger.info(
        f"✅ RAG index built for meeting {meeting_id}: "
        f"{len(chunks)} chunks, {index_size} bytes, {elapsed:.1f}s"
    )

    return {
        "chunk_count": len(chunks),
        "index_size_bytes": index_size,
        "build_time": round(elapsed, 2),
        "index_path": index_path,
        "dimension": dimension,
    }


# ═════════════════════════════════════════════════════════════════════════════
#  QUERY PHASE: ANSWER A QUESTION
#  Called each time a user types a question in the ChatWithMeeting component.
# ═════════════════════════════════════════════════════════════════════════════

def answer_question(
    meeting_id: int,
    question: str,
    top_k: int = 5,
    language: str = "en",
) -> dict:
    """
    Answers a user's question about the meeting using the RAG pipeline.
    This is the QUERY phase — called every time the user asks something.

    Args:
        meeting_id: which meeting to search
        question: the user's natural language question
        top_k: how many transcript chunks to retrieve (5 is a good default)
        language: response language

    Returns:
        dict:
        {
            "answer": "The team decided to extend the sprint deadline by 2 days...",
            "sources": [
                {
                    "text": "[00:34:12] Pallavi: I propose we extend the deadline...",
                    "score": 0.87,
                    "rank": 1,
                },
                ...
            ],
            "question": "What was decided about the sprint deadline?",
            "retrieval_time": 0.023,
            "generation_time": 2.1,
        }
    """
    if not question or len(question.strip()) < 3:
        return {"answer": "Please enter a valid question.", "sources": []}

    logger.info(f"RAG query for meeting {meeting_id}: '{question}'")
    total_start = time.time()

    # ── Step 4: Embed the question ─────────────────────────────────────────────
    question_embedding = embedding_manager.embed([question])   # shape: (1, 384)

    # ── Step 5: Search FAISS ──────────────────────────────────────────────────
    retrieval_start = time.time()
    try:
        import faiss

        index_path, chunks_path = _get_storage_paths(meeting_id)

        if not os.path.exists(index_path):
            return {
                "answer": (
                    "The meeting index is not ready yet. "
                    "It is still being processed — please try again in a minute."
                ),
                "sources": [],
            }

        # Load the FAISS index from disk
        index = faiss.read_index(index_path)

        # Load the chunk texts
        with open(chunks_path, "rb") as f:
            chunks = pickle.load(f)

        # Normalise the question embedding for cosine similarity
        faiss.normalize_L2(question_embedding)

        # Search: returns distances (D) and indices (I) of top_k nearest chunks
        # D[0] = array of similarity scores (higher = more similar)
        # I[0] = array of chunk indices in our `chunks` list
        D, I = index.search(question_embedding, min(top_k, len(chunks)))

        # ── Step 6: Retrieve the matching chunks ───────────────────────────────
        retrieved_chunks = []
        sources = []

        for rank, (score, idx) in enumerate(zip(D[0], I[0])):
            if idx < 0 or idx >= len(chunks):
                continue    # FAISS returns -1 for invalid results

            chunk_text = chunks[idx]
            retrieved_chunks.append(chunk_text)

            sources.append({
                "text": chunk_text,
                "score": round(float(score), 4),    # cosine similarity score
                "rank": rank + 1,
            })

        retrieval_time = time.time() - retrieval_start
        logger.info(
            f"Retrieved {len(retrieved_chunks)} chunks in {retrieval_time:.3f}s "
            f"(top score: {sources[0]['score'] if sources else 0:.3f})"
        )

        if not retrieved_chunks:
            return {
                "answer": "I couldn't find relevant information in the meeting transcript.",
                "sources": [],
                "question": question,
            }

    except Exception as e:
        logger.error(f"FAISS search failed: {e}", exc_info=True)
        return {"answer": "Search failed. Please try again.", "sources": [], "error": str(e)}

    # ── Step 7: Generate answer with Gemini ───────────────────────────────────
    generation_start = time.time()
    try:
        from app.ai.gemini_service import generate_rag_answer

        answer = generate_rag_answer(
            question=question,
            context_chunks=retrieved_chunks,
            language=language,
        )
        generation_time = time.time() - generation_start

    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        answer = f"Found relevant content but couldn't generate answer: {str(e)}"
        generation_time = 0

    total_time = time.time() - total_start

    return {
        "answer": answer,
        "sources": sources,
        "question": question,
        "retrieval_time": round(retrieval_time, 3),
        "generation_time": round(generation_time, 3),
        "total_time": round(total_time, 3),
        "chunks_searched": index.ntotal if 'index' in locals() else 0,
    }


def delete_meeting_index(meeting_id: int) -> bool:
    """
    Deletes the FAISS index and chunks file for a meeting.
    Called when a meeting is permanently deleted.

    Args:
        meeting_id: the meeting to delete index for

    Returns:
        True if deleted successfully
    """
    index_path, chunks_path = _get_storage_paths(meeting_id)
    deleted = False

    for path in [index_path, chunks_path]:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted: {path}")
            deleted = True

    return deleted


def check_index_exists(meeting_id: int) -> bool:
    """
    Checks if the FAISS index for a meeting has been built.
    Used by the frontend to show/hide the "Chat with Meeting" feature.
    """
    index_path, _ = _get_storage_paths(meeting_id)
    return os.path.exists(index_path)


# ═════════════════════════════════════════════════════════════════════════════
#  CHUNKING — Step 1 of the pipeline
# ═════════════════════════════════════════════════════════════════════════════

def _chunk_transcript(
    transcript: str,
    chunk_size: int = 5,        # sentences per chunk
    overlap: int = 1,           # sentences of overlap between chunks
) -> list:
    """
    Splits the transcript into overlapping chunks of sentences.

    WHY OVERLAP?
      If a task is mentioned at the boundary between sentences 5 and 6,
      without overlap it would be split across two chunks and retrieval
      might miss it. Overlap ensures boundary content appears in both chunks.

    WHY SENTENCES NOT TOKENS?
      Sentence boundaries are natural for meeting content.
      A chunk of 5 sentences ≈ 100-200 tokens — ideal for Gemini's context.

    Args:
        transcript: full transcript text
        chunk_size: number of sentences per chunk
        overlap: number of sentences shared between adjacent chunks

    Returns:
        list of text strings, each being chunk_size sentences
    """
    if not transcript:
        return []

    # ── Split into sentences ───────────────────────────────────────────────────
    # We split on periods, exclamation marks, and question marks
    # But we keep timestamp markers like [00:02:34] intact
    sentences = []

    # First, split by line (each transcript line is usually one utterance)
    lines = [l.strip() for l in transcript.split("\n") if l.strip()]

    for line in lines:
        # Each line might have multiple sentences — split further
        # Pattern: split on . ! ? but NOT on Mr. Mrs. etc.
        line_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\[])', line)
        sentences.extend([s.strip() for s in line_sentences if s.strip()])

    if not sentences:
        return [transcript]  # fallback: one big chunk

    # ── Create overlapping chunks ──────────────────────────────────────────────
    chunks = []
    step = chunk_size - overlap   # step forward by (chunk_size - overlap)

    for i in range(0, len(sentences), step):
        chunk_sentences = sentences[i: i + chunk_size]
        chunk_text = " ".join(chunk_sentences)

        # Minimum quality check: chunk must have meaningful content
        if len(chunk_text) > 30:
            chunks.append(chunk_text)

        # Stop if we've covered all sentences
        if i + chunk_size >= len(sentences):
            break

    logger.debug(f"Chunked transcript: {len(sentences)} sentences → {len(chunks)} chunks")
    return chunks


def _get_storage_paths(meeting_id: int) -> tuple:
    """
    Returns the file paths for a meeting's FAISS index and chunks.

    Files stored as:
      ./faiss_store/{meeting_id}.index   — the FAISS binary index
      ./faiss_store/{meeting_id}.chunks  — pickled list of chunk texts

    Args:
        meeting_id: unique meeting identifier

    Returns:
        (index_path, chunks_path) tuple
    """
    from app.config import settings

    store_dir = settings.FAISS_STORE_PATH
    os.makedirs(store_dir, exist_ok=True)

    index_path  = os.path.join(store_dir, f"{meeting_id}.index")
    chunks_path = os.path.join(store_dir, f"{meeting_id}.chunks")

    return index_path, chunks_path


def get_index_stats(meeting_id: int) -> dict:
    """
    Returns statistics about a meeting's FAISS index.
    Used by the admin dashboard to monitor index health.
    """
    index_path, chunks_path = _get_storage_paths(meeting_id)

    if not os.path.exists(index_path):
        return {"exists": False, "meeting_id": meeting_id}

    try:
        import faiss
        index = faiss.read_index(index_path)

        with open(chunks_path, "rb") as f:
            chunks = pickle.load(f)

        return {
            "exists": True,
            "meeting_id": meeting_id,
            "total_vectors": index.ntotal,
            "dimension": index.d,
            "chunk_count": len(chunks),
            "index_size_bytes": os.path.getsize(index_path),
            "chunks_size_bytes": os.path.getsize(chunks_path),
        }
    except Exception as e:
        return {"exists": True, "meeting_id": meeting_id, "error": str(e)}