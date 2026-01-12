# nb-order-validator

A pre-commit hook and CLI tool to verify that Jupyter Notebook code cells have been executed in consecutive order.

[![PyPI version](https://badge.fury.io/py/nb-order-validator.svg)](https://badge.fury.io/py/nb-order-validator)
[![Python Support](https://img.shields.io/pypi/pyversions/nb-order-validator.svg)](https://pypi.org/project/nb-order-validator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why nb-order-validator?

When working with Jupyter Notebooks in a collaborative environment or CI/CD pipeline, it's important to ensure that notebooks are executed in the correct order. This tool validates that all code cells have consecutive `execution_count` values (e.g., 1, 2, 3, 4...), helping you:

- Catch notebooks that were executed out of order
- Ensure reproducibility of notebook results
- Maintain code quality in team environments
- Integrate notebook validation into your CI/CD pipeline

## Features

- Fast validation using streaming JSON parser (handles large notebooks efficiently)
- Pre-commit hook integration for automatic validation
- Parallel processing support for multiple notebooks
- Zero dependencies (only requires `ijson`)
- Comprehensive error reporting

## Installation

### As a pre-commit hook (Recommended)

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/b-trout/nb-order-validator
    rev: v0.1.0  # Use the latest version
    hooks:
      - id: check-nb-order
```

Then install the hook:

```bash
pre-commit install
```

### As a standalone tool

```bash
pip install nb-order-validator
```

## Usage

### As a pre-commit hook

Once configured, the hook will automatically run when you commit `.ipynb` files:

```bash
git add notebook.ipynb
git commit -m "Add analysis notebook"
# The hook will validate execution order automatically
```

### As a CLI tool

Validate a single notebook:

```bash
check-nb-order notebook.ipynb
```

Validate multiple notebooks:

```bash
check-nb-order notebook1.ipynb notebook2.ipynb notebook3.ipynb
```

Use with shell globbing:

```bash
check-nb-order notebooks/**/*.ipynb
```

### Exit Codes

- `0`: All notebooks have consecutive execution counts
- `1`: One or more notebooks have non-consecutive execution counts

## Examples

### Valid Notebook

A notebook with cells executed in order (1, 2, 3, 4...):

```bash
$ check-nb-order analysis.ipynb
# No output, exit code 0
```

### Invalid Notebook

A notebook with cells executed out of order:

```bash
$ check-nb-order analysis.ipynb
❌ Incorrect execution order: analysis.ipynb
# Exit code 1
```

### Multiple Files

```bash
$ check-nb-order notebook1.ipynb notebook2.ipynb notebook3.ipynb
❌ Incorrect execution order: notebook2.ipynb
# Exit code 1
```

## How It Works

The tool checks the `execution_count` field in each code cell of your Jupyter Notebook:

1. Extracts all `execution_count` values from code cells
2. Ignores markdown and other non-code cells
3. Allows trailing `null` execution counts (unexecuted cells at the end)
4. Verifies that remaining counts form a consecutive sequence

### Valid Sequences

- `[1, 2, 3, 4]` - Standard consecutive order
- `[5, 6, 7, 8]` - Consecutive starting from any number
- `[1, 2, 3, null]` - Trailing unexecuted cell is allowed
- `[]` - Empty notebook is valid

### Invalid Sequences

- `[1, 3, 4]` - Missing execution count (2)
- `[1, 2, 2, 3]` - Duplicate execution count
- `[1, null, 3]` - Unexecuted cell in the middle
- `[3, 2, 1]` - Reversed order

## Requirements

- Python 3.10 or higher
- `ijson >= 3.4.0.post0`

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Repository

GitHub: [https://github.com/b-trout/nb-order-validator](https://github.com/b-trout/nb-order-validator)

## Author

b-trout (yuuta.masubuti@gmail.com)
