"""
Jupyter Notebook Execution Order Validator

This module validates that code cells in Jupyter Notebook files (.ipynb) have been
executed in consecutive order. It checks the execution_count field of each code cell
to ensure they form a continuous sequence (e.g., 1, 2, 3, 4...).

Usage:
    As a command-line tool:
        python -m nb_order_validator.main notebook1.ipynb notebook2.ipynb
        nb-order-validator notebook1.ipynb notebook2.ipynb

    As a pre-commit hook (add to .pre-commit-config.yaml):
        - repo: https://github.com/yourusername/nb-order-validator
          rev: v1.0.0
          hooks:
            - id: nb-order-validator

Exit Codes:
    0: All notebooks have consecutive execution counts
    1: One or more notebooks have non-consecutive execution counts

Examples:
    Validate a single notebook:
        $ nb-order-validator analysis.ipynb

    Validate multiple notebooks:
        $ nb-order-validator notebook1.ipynb notebook2.ipynb notebook3.ipynb
        ❌ Incorrect execution order: notebook2.ipynb
"""

import sys
import argparse
import ijson
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor


def get_execution_counts(filepath: Path) -> list[int | None]:
    """
    Extracts the execution counts from code cells in a Jupyter Notebook.

    Parameters
    ----------
    filepath : Path
        The path to the target .ipynb file.

    Returns
    -------
    list[int | None]
        A list of execution counts.
    """
    counts: list[int | None] = []
    try:
        with filepath.open("rb") as f:
            cell_stream = ijson.items(f, "cells.item")

            for cell in cell_stream:
                if cell.get("cell_type") == "code":
                    counts.append(cell.get("execution_count"))

    except (ijson.common.JSONError, FileNotFoundError, OSError):
        return []

    if counts and counts[-1] is None:
        counts.pop()

    return counts


def is_consecutive(counts: list[int | None]) -> bool:
    """
    Validates whether execution counts form a consecutive sequence.

    This function checks if the execution counts are consecutive integers without
    gaps or duplicates. The sequence must start from any integer and increment by
    exactly 1 for each subsequent element (e.g., [3, 4, 5, 6] is valid, but
    [1, 3, 4] or [1, 2, 2, 3] are not).

    Parameters
    ----------
    counts : list[int | None]
        A list of execution counts extracted from notebook code cells.
        May contain None values for cells that have not been executed.

    Returns
    -------
    bool
        True if the counts form a consecutive sequence or the list is empty.
        False if any count is None or if the sequence is not consecutive.

    Examples
    --------
    >>> is_consecutive([1, 2, 3, 4])
    True
    >>> is_consecutive([5, 6, 7])
    True
    >>> is_consecutive([1, 3, 4])  # Missing 2
    False
    >>> is_consecutive([1, 2, None, 4])  # Contains None
    False
    >>> is_consecutive([])  # Empty list is valid
    True
    """
    if not counts:
        return True

    if any(c is None for c in counts):
        return False

    int_counts = [int(c) for c in counts if c is not None]

    first = int_counts[0]
    last = int_counts[-1]
    expected = list(range(first, last + 1))

    return int_counts == expected


def process_file(filepath: Path) -> tuple[Path, bool]:
    """
    Worker function to validate a single notebook file.

    Parameters
    ----------
    filepath : Path
        The path object to validate.

    Returns
    -------
    tuple[Path, bool]
        The path object and the validation result.
    """
    if filepath.suffix != ".ipynb":
        return filepath, True

    counts = get_execution_counts(filepath)
    result = is_consecutive(counts)
    return filepath, result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify that Jupyter Notebook execution counts are consecutive."
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        type=Path,
        help="Paths to the Jupyter Notebook files (.ipynb) to check.",
    )
    args = parser.parse_args()

    if not args.filenames:
        sys.exit(0)

    failed = False

    with ProcessPoolExecutor() as executor:
        results = executor.map(process_file, args.filenames)

        for filepath, is_valid in results:
            if not is_valid:
                print(f"❌ Incorrect execution order: {filepath}")
                failed = True

    if failed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
