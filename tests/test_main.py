import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from _pytest.capture import CaptureFixture

# Import modules from src
# Note: Ensure PYTHONPATH includes 'src' when running pytest
from nb_order_validator.main import (
    get_execution_counts,
    is_consecutive,
    main,
)


# ==========================================
# Helper Functions
# ==========================================
def create_notebook(path: Path, counts: list[int | None]) -> None:
    """
    Creates a dummy Jupyter Notebook (JSON) with the specified execution counts.

    Parameters
    ----------
    path : Path
        The path where the notebook file will be created.
    counts : list[int | None]
        A list of execution counts. Use `None` to represent an unexecuted cell (null).
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

    # Insert a Markdown cell to verify it is ignored by the logic
    cells.insert(1, {"cell_type": "markdown", "source": ["# Title"]})

    content = {
        "cells": cells,
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    # Open with utf-8 encoding to ensure compatibility across OS
    with path.open("w", encoding="utf-8") as f:
        json.dump(content, f)


# ==========================================
# 1. Logic Tests (is_consecutive)
# ==========================================
@pytest.mark.parametrize(
    "counts, expected",
    [
        ([1, 2, 3], True),  # Valid: Starts from 1
        ([10, 11, 12], True),  # Valid: Starts from arbitrary number
        ([1], True),  # Valid: Single cell
        ([], True),  # Valid: Empty
        ([1, 3, 2], False),  # Invalid: Order reversed
        ([1, 3], False),  # Invalid: Missing number
        ([1, 1, 2], False),  # Invalid: Duplicate numbers
        ([1, None, 3], False),  # Invalid: Unexecuted cell in the middle
        (
            [None],
            False,
        ),  # Invalid: Only unexecuted cell (treated as non-consecutive)
    ],
)
def test_is_consecutive(counts: list[int | None], expected: bool) -> None:
    """
    Tests the logic for validating whether a sequence of execution counts is consecutive.
    """
    assert is_consecutive(counts) == expected


# ==========================================
# 2. File Parsing Tests (get_execution_counts + ijson)
# ==========================================
def test_get_execution_counts_valid(tmp_path: Path) -> None:
    """
    Verifies that execution counts are correctly extracted from a valid Notebook.
    """
    f = tmp_path / "test.ipynb"
    create_notebook(f, [1, 2, 3])

    counts = get_execution_counts(f)
    assert counts == [1, 2, 3]


def test_get_execution_counts_ignore_trailing_null(tmp_path: Path) -> None:
    """
    Verifies that a trailing unexecuted cell (null) is ignored.
    """
    f = tmp_path / "test.ipynb"
    create_notebook(f, [1, 2, None])

    counts = get_execution_counts(f)
    # Expect [1, 2] because the trailing None should be removed
    assert counts == [1, 2]


def test_get_execution_counts_broken_json(tmp_path: Path) -> None:
    """
    Verifies behavior when the input file contains invalid JSON.
    Expected to return an empty list without raising an exception.
    """
    f = tmp_path / "broken.ipynb"
    f.write_text("{ broken json ", encoding="utf-8")

    counts = get_execution_counts(f)
    assert counts == []


def test_get_execution_counts_file_not_found() -> None:
    """
    Verifies behavior when the specified file does not exist.
    Expected to return an empty list.
    """
    counts = get_execution_counts(Path("ghost_file.ipynb"))
    assert counts == []


# ==========================================
# 3. CLI Integration Tests (main)
# ==========================================
def test_main_success(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    """
    Verifies that the CLI returns exit code 0 for a valid notebook.
    """
    f = tmp_path / "valid.ipynb"
    create_notebook(f, [1, 2, 3])

    test_args = ["check-nb-order", str(f)]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as e:
            main()

    assert e.value.code == 0

    # Ensure no error symbols are present in stdout
    captured = capsys.readouterr()
    assert "❌" not in captured.out


def test_main_failure(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    """
    Verifies that the CLI returns exit code 1 for an invalid notebook
    and prints the error message.
    """
    f = tmp_path / "invalid.ipynb"
    create_notebook(f, [1, 3])  # Missing number

    test_args = ["check-nb-order", str(f)]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as e:
            main()

    assert e.value.code == 1

    # Verify error message output
    captured = capsys.readouterr()
    assert "❌ Incorrect execution order" in captured.out
    assert "invalid.ipynb" in captured.out


def test_main_multiple_files(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """
    Verifies parallel processing of multiple files.
    The exit code should be 1 if at least one file is invalid.
    """
    f1 = tmp_path / "good.ipynb"
    create_notebook(f1, [1, 2])

    f2 = tmp_path / "bad.ipynb"
    create_notebook(f2, [1, 3])

    test_args = ["check-nb-order", str(f1), str(f2)]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as e:
            main()

    assert e.value.code == 1

    captured = capsys.readouterr()
    # Ensure only the bad file is reported
    assert "bad.ipynb" in captured.out
    assert "good.ipynb" not in captured.out
