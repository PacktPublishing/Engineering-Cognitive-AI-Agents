# ChromaDB REPL Tool

An interactive REPL-like CLI tool for querying and inspecting ChromaDB databases used in the Winston cognitive AI agents project.

## Features

- Interactive command-line interface for ChromaDB inspection
- Support for semantic queries with distance thresholds
- Database information and statistics display
- Collection management and browsing
- Chapter context resolution (e.g., `chapter03` → database path)
- Rich-formatted output with tables and syntax highlighting
- Export functionality for query results

## Installation

This tool is part of the Winston workspace and is installed automatically when you run:

```bash
uv sync
```

## Usage

### Basic Usage

```bash
# Launch REPL with default settings
chroma-repl

# Connect to specific database
chroma-repl --db-path ./path/to/chroma.db

# Use chapter context resolution
chroma-repl --chapter-context chapter03

# Specify collection name
chroma-repl --collection-name intent_index

# Enable verbose logging
chroma-repl --verbose
```

### Interactive Commands

Once in the REPL, you can use these commands:

- `query <text> [--limit N] [--threshold X.X]` - Semantic search
- `info` - Database and collection information
- `count` - Document count in collection
- `collections` - List all collections
- `export [--format json|csv] [--output file.ext]` - Export data
- `help` - Show command help
- `exit` - Exit the REPL

### Examples

```bash
# Query for intent-related documents
> query "create file" --limit 5 --threshold 0.8

# Get database statistics
> info

# Export all documents as JSON
> export --format json --output intent_data.json
```

## Integration with Winston

This tool is specifically designed to work with Winston's intent database system:

- Automatically resolves chapter-specific database paths
- Uses Winston's common configuration and utilities
- Supports the intent index collection used for tool discovery
- Compatible with Winston's ChromaDB schema and metadata

## Architecture

The tool follows Winston's principles:

- **Minimal Interface**: Simple, focused REPL for database inspection
- **Protocol Integration**: Uses Winston's common ChromaDB utilities
- **Extensible Design**: Easy to add new commands and features
- **Error Resilience**: Comprehensive error handling and logging

## Development

For development and testing:

```bash
# Run with package specification
uv run --package chroma-repl chroma-repl --help

# Type checking
uv run mypy chroma-repl/src/

# Code formatting
uv run ruff format chroma-repl/src/
```

## License

Part of the Winston cognitive AI agents project.
