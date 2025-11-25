"""Tests for factory.bootstrap module."""

import json
from pathlib import Path

import pytest

from factory.bootstrap import load_seed, write_spec_artifact


class TestLoadSeed:
    """Tests for the load_seed function."""

    def test_load_valid_seed(self, tmp_path: Path):
        """Test loading a valid seed.json file."""
        seed_content = {
            "project_metadata": {
                "name": "test-project",
                "version": "0.1.0",
            },
            "intent": "Test intent",
        }

        seed_path = tmp_path / "seed.json"
        seed_path.write_text(json.dumps(seed_content))

        loaded = load_seed(seed_path)
        assert loaded["project_metadata"]["name"] == "test-project"
        assert loaded["intent"] == "Test intent"

    def test_load_missing_seed_raises(self, tmp_path: Path):
        """Test that loading a missing seed raises FileNotFoundError."""
        missing_path = tmp_path / "missing.json"
        with pytest.raises(FileNotFoundError):
            load_seed(missing_path)

    def test_load_invalid_json_raises(self, tmp_path: Path):
        """Test that loading invalid JSON raises JSONDecodeError."""
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("not valid json {{{")

        with pytest.raises(json.JSONDecodeError):
            load_seed(invalid_path)


class TestWriteSpecArtifact:
    """Tests for the write_spec_artifact function."""

    def test_write_artifact(self, tmp_path: Path):
        """Test writing a spec artifact to disk."""
        output_path = tmp_path / "spec.md"
        content = "# Test Specification\n\nContent here."

        write_spec_artifact(output_path, content)

        assert output_path.exists()
        assert output_path.read_text() == content

    def test_write_artifact_creates_parent_dirs(self, tmp_path: Path):
        """Test that write_spec_artifact creates parent directories."""
        output_path = tmp_path / "nested" / "path" / "spec.md"
        content = "# Nested Spec"

        write_spec_artifact(output_path, content)

        assert output_path.exists()
        assert output_path.read_text() == content
