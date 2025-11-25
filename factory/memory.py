"""
Vector database integration for RAG-enhanced code generation.

This module implements ChromaDB-based retrieval augmented generation (RAG)
to provide relevant context to the DSPy agents without overwhelming
their context windows.
"""

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings


def create_memory_store(persist_directory: str | None = None) -> chromadb.ClientAPI:
    """
    Create or connect to the ChromaDB memory store.

    ChromaDB runs embedded (in-process) for simplicity in the turnkey setup.
    For production deployments, consider using Qdrant with a separate container.

    Args:
        persist_directory: Optional directory for persistent storage.
                          If None, uses in-memory storage.

    Returns:
        A ChromaDB client instance
    """
    if persist_directory:
        return chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
    return chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))


def get_or_create_collection(
    client: chromadb.ClientAPI,
    name: str = "spec_chunks",
) -> chromadb.Collection:
    """
    Get or create a collection for storing spec document chunks.

    Args:
        client: The ChromaDB client
        name: Name of the collection

    Returns:
        The ChromaDB collection
    """
    return client.get_or_create_collection(
        name=name,
        metadata={"description": "Spec-Kit document chunks for RAG"},
    )


def index_document(
    collection: chromadb.Collection,
    document_path: Path,
    chunk_by_headers: bool = True,
) -> int:
    """
    Index a markdown document into the vector store.

    Splits the document by headers (##) and indexes each section
    as a separate chunk for fine-grained retrieval.

    Args:
        collection: The ChromaDB collection
        document_path: Path to the markdown document
        chunk_by_headers: If True, split by ## headers. Otherwise, use full doc.

    Returns:
        Number of chunks indexed
    """
    if not document_path.exists():
        return 0

    content = document_path.read_text()

    if chunk_by_headers:
        chunks = _split_by_headers(content)
    else:
        chunks = [content]

    # Generate unique IDs based on document path and chunk index
    doc_id = document_path.stem
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]

    # Add to collection (ChromaDB handles embedding automatically)
    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=[
            {"source": str(document_path), "chunk_index": i} for i in range(len(chunks))
        ],
    )

    return len(chunks)


def _split_by_headers(content: str) -> list[str]:
    """
    Split markdown content by level-2 headers (##).

    Args:
        content: The markdown content

    Returns:
        List of content chunks, one per section
    """
    chunks = []
    current_chunk: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## ") and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
        else:
            current_chunk.append(line)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks if chunks else [content]


def retrieve_context(
    collection: chromadb.Collection,
    query: str,
    n_results: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant context chunks for a given query.

    Args:
        collection: The ChromaDB collection
        query: The query string (e.g., task description)
        n_results: Maximum number of results to return

    Returns:
        List of result dictionaries with 'document' and 'metadata' keys
    """
    results = collection.query(query_texts=[query], n_results=n_results)

    context_items = []
    if results["documents"] and results["metadatas"]:
        for doc, metadata in zip(
            results["documents"][0], results["metadatas"][0], strict=False
        ):
            context_items.append({"document": doc, "metadata": metadata})

    return context_items


def build_context_string(
    collection: chromadb.Collection,
    query: str,
    agents_md_path: Path | None = None,
    n_results: int = 3,
) -> str:
    """
    Build a complete context string for DSPy agent input.

    Combines the root AGENTS.md with relevant spec chunks retrieved via RAG.

    Args:
        collection: The ChromaDB collection
        query: The query string for RAG retrieval
        agents_md_path: Path to AGENTS.md. Defaults to ./AGENTS.md
        n_results: Number of spec chunks to retrieve

    Returns:
        Combined context string
    """
    parts = []

    # Include AGENTS.md if available
    if agents_md_path is None:
        agents_md_path = Path("AGENTS.md")

    if agents_md_path.exists():
        parts.append("# Global Context (AGENTS.md)\n")
        parts.append(agents_md_path.read_text())
        parts.append("\n\n")

    # Include retrieved spec chunks
    context_items = retrieve_context(collection, query, n_results)
    if context_items:
        parts.append("# Relevant Specification Context\n")
        for item in context_items:
            source = item["metadata"].get("source", "unknown")
            parts.append(f"\n## From: {source}\n")
            parts.append(item["document"])
            parts.append("\n")

    return "".join(parts)
