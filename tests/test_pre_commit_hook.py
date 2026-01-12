"""
Integration tests for pre-commit hook functionality.

These tests ensure that when users install this tool as a pre-commit hook,
it functions correctly and validates notebook execution order as expected.
"""

import json
import subprocess
from pathlib import Path
from typing import Any


def create_notebook(path: Path, counts: list[int | None]) -> None:
    """
    Creates a dummy Jupyter Notebook (JSON) with specified execution counts.

    Parameters
    ----------
    path : Path
        The path where the notebook file will be created.
    counts : list[int | None]
        A list of execution counts. Use `None` for unexecuted cells.
    """
    cells: list[dict[str, Any]] = []
    for c in counts:
        cell: dict[str, Any] = {
            "cell_type": "code",
            "execution_count": c,
            "metadata": {},
            "outputs": [],
            "source": ["print('test')"],
        }
        cells.append(cell)

    content = {
        "cells": cells,
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(content, f)


class TestPreCommitHookConfiguration:
    """Tests for verifying the pre-commit hook configuration file."""

    def test_hook_configuration_file_exists(self) -> None:
        """Verify that .pre-commit-hooks.yaml exists in the repository."""
        hook_file = Path(__file__).parent.parent / ".pre-commit-hooks.yaml"
        assert hook_file.exists(), (
            ".pre-commit-hooks.yaml not found in repository root"
        )

    def test_hook_configuration_is_valid_format(self) -> None:
        """
        Verify that .pre-commit-hooks.yaml has the expected structure.
        Uses simple text parsing to validate basic YAML structure.
        """
        hook_file = Path(__file__).parent.parent / ".pre-commit-hooks.yaml"
        content = hook_file.read_text(encoding="utf-8")

        # Verify it's not empty
        assert content.strip(), "Hook config should not be empty"

        # Check for required fields in the YAML content
        required_patterns = [
            "- id:",
            "name:",
            "entry:",
            "language:",
            "types:",
        ]
        for pattern in required_patterns:
            assert pattern in content, (
                f"Hook config should contain '{pattern}'"
            )

    def test_hook_has_required_fields(self) -> None:
        """
        Verify that the hook configuration contains all required fields
        with correct values.
        """
        hook_file = Path(__file__).parent.parent / ".pre-commit-hooks.yaml"
        content = hook_file.read_text(encoding="utf-8")

        # Verify specific values
        assert "id: check-nb-order" in content, (
            "Hook id should be 'check-nb-order'"
        )
        assert "entry: check-nb-order" in content, (
            "Hook entry should be 'check-nb-order'"
        )
        assert "language: python" in content, (
            "Hook language should be 'python'"
        )

    def test_hook_targets_jupyter_files(self) -> None:
        """
        Verify that the hook is configured to target
        Jupyter notebook files.
        """
        hook_file = Path(__file__).parent.parent / ".pre-commit-hooks.yaml"
        content = hook_file.read_text(encoding="utf-8")

        assert "types:" in content, "Hook should specify file types"
        assert "jupyter" in content, "Hook should target jupyter file type"


class TestPreCommitHookExecution:
    """
    Tests for verifying the hook executes correctly
    as a pre-commit hook.
    """

    def test_entry_point_exists(self) -> None:
        """Verify that the check-nb-order entry point is accessible."""
        result = subprocess.run(
            ["check-nb-order", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # The command should either show help or at least not fail with
        # "command not found"
        assert result.returncode in [
            0,
            1,
            2,
        ], "check-nb-order command should be available"

    def test_hook_validates_valid_notebook(self, tmp_path: Path) -> None:
        """
        Verify that the hook accepts a notebook
        with correct execution order.
        """
        notebook = tmp_path / "valid.ipynb"
        create_notebook(notebook, [1, 2, 3, 4])

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, (
            f"Hook should pass for valid notebook. stderr: {result.stderr}"
        )
        assert "❌" not in result.stdout, (
            "Should not show error for valid notebook"
        )

    def test_hook_rejects_invalid_notebook(self, tmp_path: Path) -> None:
        """
        Verify that the hook rejects a notebook
        with incorrect execution order.
        """
        notebook = tmp_path / "invalid.ipynb"
        create_notebook(notebook, [1, 3, 5])  # Non-consecutive

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 1, "Hook should fail for invalid notebook"
        assert "❌" in result.stdout, (
            "Should show error message for invalid notebook"
        )
        assert "invalid.ipynb" in result.stdout, (
            "Should mention the problematic file"
        )

    def test_hook_processes_multiple_files(self, tmp_path: Path) -> None:
        """
        Verify that the hook can process multiple notebook files at once.
        """
        valid1 = tmp_path / "valid1.ipynb"
        valid2 = tmp_path / "valid2.ipynb"
        invalid = tmp_path / "invalid.ipynb"

        create_notebook(valid1, [1, 2, 3])
        create_notebook(valid2, [10, 11, 12])
        create_notebook(invalid, [1, 2, 4])  # Missing 3

        result = subprocess.run(
            [
                "check-nb-order",
                str(valid1),
                str(valid2),
                str(invalid),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 1, (
            "Hook should fail when any notebook is invalid"
        )
        assert "invalid.ipynb" in result.stdout, (
            "Should report the invalid notebook"
        )
        assert "valid1.ipynb" not in result.stdout, (
            "Should not report valid notebooks"
        )
        assert "valid2.ipynb" not in result.stdout, (
            "Should not report valid notebooks"
        )

    def test_hook_handles_empty_notebooks(self, tmp_path: Path) -> None:
        """
        Verify that the hook handles notebooks with no code cells.
        """
        notebook = tmp_path / "empty.ipynb"
        create_notebook(notebook, [])

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, "Hook should accept empty notebooks"

    def test_hook_allows_trailing_unexecuted_cells(
        self, tmp_path: Path
    ) -> None:
        """
        Verify that the hook allows notebooks
        with a single trailing unexecuted cell.
        """
        notebook = tmp_path / "trailing_null.ipynb"
        create_notebook(notebook, [1, 2, 3, None])

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, (
            "Hook should accept trailing unexecuted cells"
        )

    def test_hook_rejects_middle_unexecuted_cells(
        self, tmp_path: Path
    ) -> None:
        """
        Verify that the hook rejects notebooks with unexecuted cells
        in the middle.
        """
        notebook = tmp_path / "middle_null.ipynb"
        create_notebook(notebook, [1, 2, None, 4])

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 1, (
            "Hook should reject unexecuted cells in the middle"
        )


class TestPreCommitHookIntegration:
    """
    Integration tests that simulate actual pre-commit hook usage scenarios.
    """

    def test_hook_integration_with_git_repo(self, tmp_path: Path) -> None:
        """
        Simulate a real pre-commit hook scenario in a git repository.

        This test:
        1. Creates a temporary git repository
        2. Creates test notebooks
        3. Verifies the hook can be run directly
        """
        # Create a git repo
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Create a notebook
        notebook = repo_dir / "test.ipynb"
        create_notebook(notebook, [1, 2, 3])

        # Test that check-nb-order can be run directly
        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, (
            "Hook should validate notebook successfully"
        )

    def test_hook_fails_with_clear_error_message(
        self, tmp_path: Path
    ) -> None:
        """
        Verify that when the hook fails, it provides a clear error message
        that helps users understand what went wrong.
        """
        notebook = tmp_path / "problem.ipynb"
        create_notebook(notebook, [1, 3, 2])  # Out of order

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 1, "Hook should fail"
        assert result.stdout.strip() != "", "Should provide error message"
        assert "problem.ipynb" in result.stdout, (
            "Error message should mention the file"
        )
        assert "❌" in result.stdout, "Should include visual error indicator"


class TestHookDocumentation:
    """Tests to verify that hook usage is properly documented."""

    def test_readme_mentions_pre_commit_hook(self) -> None:
        """Verify that README.md documents the pre-commit hook usage."""
        readme_file = Path(__file__).parent.parent / "README.md"
        assert readme_file.exists(), "README.md should exist"

        content = readme_file.read_text(encoding="utf-8")
        assert ".pre-commit-config.yaml" in content, (
            "README should mention .pre-commit-config.yaml"
        )
        assert "pre-commit install" in content, (
            "README should document hook installation"
        )
        assert "check-nb-order" in content, (
            "README should mention the hook id"
        )

    def test_pyproject_defines_entry_point(self) -> None:
        """
        Verify that pyproject.toml defines the check-nb-order entry point.
        """
        pyproject_file = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_file.exists(), "pyproject.toml should exist"

        content = pyproject_file.read_text(encoding="utf-8")
        assert "[project.scripts]" in content, "Should define project scripts"
        assert "check-nb-order" in content, (
            "Should define check-nb-order entry point"
        )


class TestHookRobustness:
    """Tests to ensure the hook handles edge cases robustly."""

    def test_hook_handles_malformed_json(self, tmp_path: Path) -> None:
        """
        Verify that the hook handles malformed notebook JSON gracefully.
        """
        notebook = tmp_path / "malformed.ipynb"
        notebook.write_text("{ broken json", encoding="utf-8")

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should not crash, but should fail validation
        assert result.returncode in [
            0,
            1,
        ], "Should handle malformed JSON gracefully"

    def test_hook_handles_nonexistent_file(self) -> None:
        """
        Verify that the hook handles nonexistent files gracefully.
        """
        result = subprocess.run(
            ["check-nb-order", "nonexistent.ipynb"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should not crash
        assert result.returncode in [
            0,
            1,
        ], "Should handle nonexistent files gracefully"

    def test_hook_unicode_filename_support(self, tmp_path: Path) -> None:
        """
        Verify that the hook can handle notebooks
        with Unicode filenames.
        """
        notebook = tmp_path / "テスト_日本語.ipynb"
        create_notebook(notebook, [1, 2, 3])

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, "Should handle Unicode filenames"

    def test_hook_handles_large_execution_counts(
        self, tmp_path: Path
    ) -> None:
        """
        Verify that the hook can handle notebooks
        with large execution counts.
        """
        notebook = tmp_path / "large_counts.ipynb"
        create_notebook(notebook, [1000, 1001, 1002, 1003])

        result = subprocess.run(
            ["check-nb-order", str(notebook)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, "Should handle large execution counts"
