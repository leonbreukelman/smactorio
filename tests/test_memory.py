"""Tests for factory.memory module."""

from pathlib import Path

import pytest

from factory.memory import (
    _split_by_headers,
    build_context_string,
    create_memory_store,
    get_or_create_collection,
    index_document,
    retrieve_context,
)

# Mark tests that require network access
requires_network = pytest.mark.skip(
    reason="ChromaDB needs to download embedding model; skipped in offline environment"
)


class TestCreateMemoryStore:
    """Tests for the create_memory_store function."""

    def test_create_ephemeral_store(self):
        """Test creating an ephemeral (in-memory) store."""
        client = create_memory_store()
        assert client is not None
        # Should be able to list collections
        collections = client.list_collections()
        assert isinstance(collections, list)

    def test_create_persistent_store(self, tmp_path: Path):
        """Test creating a persistent store."""
        persist_dir = str(tmp_path / "chromadb")
        client = create_memory_store(persist_directory=persist_dir)
        assert client is not None


class TestGetOrCreateCollection:
    """Tests for the get_or_create_collection function."""

    def test_create_new_collection(self):
        """Test creating a new collection."""
        client = create_memory_store()
        collection = get_or_create_collection(client, "test_collection")
        assert collection.name == "test_collection"

    def test_get_existing_collection(self):
        """Test getting an existing collection."""
        client = create_memory_store()
        collection1 = get_or_create_collection(client, "same_name")
        collection2 = get_or_create_collection(client, "same_name")
        assert collection1.name == collection2.name


class TestSplitByHeaders:
    """Tests for the _split_by_headers function."""

    def test_split_with_headers(self):
        """Test splitting content by level-2 headers."""
        content = """# Main Title

Introduction text.

## Section One

Content of section one.

## Section Two

Content of section two.
"""
        chunks = _split_by_headers(content)
        assert len(chunks) == 3
        assert "Introduction text" in chunks[0]
        assert "## Section One" in chunks[1]
        assert "## Section Two" in chunks[2]

    def test_no_headers(self):
        """Test content with no headers."""
        content = "Just plain text without any headers."
        chunks = _split_by_headers(content)
        assert len(chunks) == 1
        assert chunks[0] == content


class TestIndexDocument:
    """Tests for the index_document function."""

    @requires_network
    def test_index_markdown_document(self, tmp_path: Path):
        """Test indexing a markdown document."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text("""# Test Document

## Section A

Content A

## Section B

Content B
""")

        client = create_memory_store()
        collection = get_or_create_collection(client, "test_index")

        chunks = index_document(collection, doc_path)
        assert chunks == 3  # Intro + Section A + Section B

    def test_index_nonexistent_document(self, tmp_path: Path):
        """Test indexing a document that doesn't exist."""
        doc_path = tmp_path / "missing.md"

        client = create_memory_store()
        collection = get_or_create_collection(client, "test_missing")

        chunks = index_document(collection, doc_path)
        assert chunks == 0


class TestRetrieveContext:
    """Tests for the retrieve_context function."""

    @requires_network
    def test_retrieve_from_indexed_content(self, tmp_path: Path):
        """Test retrieving context from indexed content."""
        doc_path = tmp_path / "spec.md"
        doc_path.write_text("""# Specification

## User Authentication

Users must be able to log in with email and password.

## Database Design

Use PostgreSQL for the database backend.
""")

        client = create_memory_store()
        collection = get_or_create_collection(client, "test_retrieve")
        index_document(collection, doc_path)

        results = retrieve_context(collection, "login authentication", n_results=1)
        assert len(results) >= 1
        # The authentication section should be most relevant
        assert any("Authentication" in r["document"] for r in results)


class TestBuildContextString:
    """Tests for the build_context_string function."""

    @requires_network
    def test_build_context_with_agents_md(self, tmp_path: Path):
        """Test building context with AGENTS.md."""
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text("# Global Rules\n\nFollow the style guide.")

        client = create_memory_store()
        collection = get_or_create_collection(client, "test_context")

        context = build_context_string(
            collection,
            "test query",
            agents_md_path=agents_path,
        )

        assert "Global Rules" in context
        assert "AGENTS.md" in context
