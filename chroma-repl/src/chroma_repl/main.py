"""Main CLI interface for the ChromaDB REPL tool.

This module provides an interactive command-line interface for querying
and inspecting Winston's ChromaDB intent databases. It supports both
direct database path specification and chapter context resolution.
"""

import json
import sys
from pathlib import Path

import click
import chromadb
from chromadb import Collection
from loguru import logger
from rich.console import Console
from rich.table import Table

from common.config import INTENT_COLLECTION_NAME, INTENT_DB_PERSIST_DIR
from common.intent_database import (
    get_full_item_by_id,
    initialize_intent_database,
    query_by_intent,
)
from common.paths import get_chapter_path


class ChromaREPLError(Exception):
    """Base exception for ChromaDB REPL operations."""

    pass


class DatabaseNotFoundError(ChromaREPLError):
    """Raised when specified database path cannot be found."""

    pass


class ChromaREPL:
    """Interactive REPL for ChromaDB operations.

    This class provides a command-driven interface for exploring
    and querying ChromaDB databases used by Winston's intent system.

    Attributes
    ----------
    console : Console
        Rich console instance for formatted output.
    collection : Collection | None
        Currently active ChromaDB collection.
    db_path : str | None
        Path to the current database directory.
    collection_name : str
        Name of the active collection.
    """

    def __init__(self) -> None:
        """Initialize the ChromaDB REPL interface."""
        self.console = Console()
        self.collection: Collection | None = None
        self.db_path: str | None = None
        self.collection_name: str = INTENT_COLLECTION_NAME

    @logger.catch
    def connect_database(
        self, db_path: str, collection_name: str = INTENT_COLLECTION_NAME
    ) -> None:
        """Connect to a ChromaDB database and collection.

        Parameters
        ----------
        db_path : str
            Path to the ChromaDB persistence directory.
        collection_name : str, optional
            Name of the collection to connect to.

        Raises
        ------
        DatabaseNotFoundError
            If the database path does not exist.
        ChromaREPLError
            If connection to the database fails.
        """
        db_path_obj = Path(db_path)
        if not db_path_obj.exists():
            raise DatabaseNotFoundError(f"Database path does not exist: {db_path}")

        try:
            self.collection = initialize_intent_database(
                persist_dir=str(db_path_obj), collection_name=collection_name
            )
            self.db_path = str(db_path_obj)
            self.collection_name = collection_name

            self.console.print(f"[green]✓[/green] Connected to database: {db_path}")
            self.console.print(f"[green]✓[/green] Active collection: {collection_name}")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise ChromaREPLError(f"Database connection failed: {e}") from e

    @logger.catch
    def show_info(self) -> None:
        """Display information about the current database and collection."""
        if not self.collection:
            self.console.print("[red]No database connected[/red]")
            return

        try:
            # Get basic collection information
            count = self.collection.count()

            # Create information table
            table = Table(title="Database Information")
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="white")

            table.add_row("Database Path", str(self.db_path))
            table.add_row("Collection Name", self.collection_name)
            table.add_row("Document Count", str(count))

            self.console.print(table)

        except Exception as e:
            logger.error(f"Failed to retrieve database info: {e}")
            self.console.print(f"[red]Error retrieving database info: {e}[/red]")

    @logger.catch
    def show_collections(self) -> None:
        """List all collections in the current database."""
        if not self.db_path:
            self.console.print("[red]No database connected[/red]")
            return

        try:
            client = chromadb.PersistentClient(path=self.db_path)
            collections = client.list_collections()

            if not collections:
                self.console.print("[yellow]No collections found[/yellow]")
                return

            table = Table(title="Available Collections")
            table.add_column("Name", style="cyan")
            table.add_column("ID", style="dim")

            for collection in collections:
                # Get count for each collection
                try:
                    coll = client.get_collection(collection.name)
                    count = coll.count()
                    name_with_count = f"{collection.name} ({count} docs)"
                except Exception:
                    name_with_count = collection.name

                table.add_row(name_with_count, str(collection.id))

            self.console.print(table)

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            self.console.print(f"[red]Error listing collections: {e}[/red]")

    @logger.catch
    def query_intent(self, intent: str, n_results: int = 5) -> None:
        """Query the database for items matching an intent.

        Parameters
        ----------
        intent : str
            The intent query string.
        n_results : int, optional
            Maximum number of results to return, by default 5.
        """
        if not self.collection:
            self.console.print("[red]No database connected[/red]")
            return

        try:
            results = query_by_intent(
                collection=self.collection, intent=intent, n_results=n_results
            )

            if not results:
                self.console.print(
                    f"[yellow]No results found for intent: '{intent}'[/yellow]"
                )
                return

            # Display results in a formatted table
            table = Table(title=f"Query Results for: '{intent}'")
            table.add_column("Rank", justify="right", style="cyan", width=4)
            table.add_column("Type", style="green", width=8)
            table.add_column("ID", style="blue", no_wrap=True)
            table.add_column("Similarity", justify="right", style="yellow", width=10)
            table.add_column("Document", style="white")

            for i, result in enumerate(results, 1):
                item_type = result.get("type", "unknown")
                doc_id = result.get("id", "unknown")
                similarity = f"{result.get('similarity', 0):.3f}"
                document = result.get("document", "")

                # Truncate long documents
                if len(document) > 80:
                    document = document[:77] + "..."

                table.add_row(str(i), item_type, doc_id, similarity, document)

            self.console.print(table)

        except Exception as e:
            logger.error(f"Failed to query intent: {e}")
            self.console.print(f"[red]Error querying intent: {e}[/red]")

    @logger.catch
    def show_count(self, item_type: str | None = None) -> None:
        """Show document count, optionally filtered by type.

        Parameters
        ----------
        item_type : str, optional
            Filter by item type (e.g., 'tool', 'intent').
        """
        if not self.collection:
            self.console.print("[red]No database connected[/red]")
            return

        try:
            if item_type:
                # Query with type filter to get count
                results = self.collection.get(
                    where={"type": item_type}, include=["metadatas"]
                )
                metadatas = results.get("metadatas")
                count = len(metadatas) if metadatas is not None else 0
                self.console.print(
                    f"[cyan]Documents of type '{item_type}': {count}[/cyan]"
                )
            else:
                count = self.collection.count()
                self.console.print(f"[cyan]Total documents: {count}[/cyan]")

        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            self.console.print(f"[red]Error getting count: {e}[/red]")

    @logger.catch
    def export_data(self, output_path: str, item_type: str | None = None) -> None:
        """Export collection data to JSON file.

        Parameters
        ----------
        output_path : str
            Path to output JSON file.
        item_type : str, optional
            Filter by item type for export.
        """
        if not self.collection:
            self.console.print("[red]No database connected[/red]")
            return

        try:
            # Build where clause - use None for no filter
            results = self.collection.get(
                where={"type": item_type} if item_type else None,
                include=["documents", "metadatas"],
            )

            # Structure data for export with null safety
            export_data = []
            ids = results.get("ids")
            docs = results.get("documents")
            metas = results.get("metadatas")

            # Ensure all lists are valid before processing
            if ids and docs and metas:
                for i, doc_id in enumerate(ids):
                    doc_text = docs[i] if i < len(docs) else ""
                    metadata = metas[i] if i < len(metas) else {}

                    item = {"id": doc_id, "document": doc_text, "metadata": metadata}
                    export_data.append(item)

            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with output_file.open("w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.console.print(
                f"[green]✓[/green] Exported {len(export_data)} items to: {output_path}"
            )

        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            self.console.print(f"[red]Error exporting data: {e}[/red]")

    @logger.catch
    def show_document(self, doc_id: str) -> None:
        """Display the full document entry for a given document ID.

        Parameters
        ----------
        doc_id : str
            The document ID to retrieve and display.
        """
        if not self.collection:
            self.console.print("[red]No database connected[/red]")
            return

        try:
            item = get_full_item_by_id(self.collection, doc_id)

            if item is None:
                self.console.print(f"[yellow]Document not found: '{doc_id}'[/yellow]")
                return

            # Display as formatted JSON
            formatted_json = json.dumps(item, indent=2, ensure_ascii=False)
            self.console.print(f"\n[bold cyan]Document: {doc_id}[/bold cyan]")
            self.console.print(formatted_json)

        except Exception as e:
            logger.error(f"Failed to retrieve document: {e}")
            self.console.print(f"[red]Error retrieving document: {e}[/red]")

    def show_help(self) -> None:
        """Display available commands and their usage."""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

[yellow]Database Operations:[/yellow]
  info                    - Show database and collection information
  collections            - List all collections in the database
  count [type]           - Show document count (optionally filtered by type)

[yellow]Query Operations:[/yellow]
  query <intent> [n]     - Query for items matching intent (default n=5)
  show <doc_id>          - Display full document entry as formatted JSON
  export <path> [type]   - Export data to JSON file (optionally filtered by type)

[yellow]Utility Commands:[/yellow]
  help                   - Show this help message
  exit                   - Exit the REPL

[yellow]Examples:[/yellow]
  query "file operations" 10
  show general-read_file
  count tool
  export ./data.json intent
  collections
"""
        self.console.print(help_text)

    def run_repl(self) -> None:
        """Run the interactive REPL loop."""
        self.console.print("\n[bold green]Winston ChromaDB REPL[/bold green]")
        self.console.print("Type 'help' for available commands or 'exit' to quit.\n")

        while True:
            try:
                # Get user input
                prompt = f"[{self.collection_name}]> " if self.collection else "> "
                user_input = self.console.input(f"[cyan]{prompt}[/cyan]").strip()

                if not user_input:
                    continue

                # Parse command and arguments
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:]

                # Execute commands
                if command == "exit":
                    self.console.print("[yellow]Goodbye![/yellow]")
                    break

                elif command == "help":
                    self.show_help()

                elif command == "info":
                    self.show_info()

                elif command == "collections":
                    self.show_collections()

                elif command == "count":
                    item_type = args[0] if args else None
                    self.show_count(item_type)

                elif command == "query":
                    if not args:
                        self.console.print(
                            "[red]Usage: query <intent> [n_results][/red]"
                        )
                        continue

                    intent = (
                        " ".join(args[:-1])
                        if len(args) > 1 and args[-1].isdigit()
                        else " ".join(args)
                    )
                    n_results = (
                        int(args[-1]) if len(args) > 1 and args[-1].isdigit() else 5
                    )

                    self.query_intent(intent, n_results)

                elif command == "show":
                    if not args:
                        self.console.print(
                            "[red]Usage: show <doc_id>[/red]"
                        )
                        continue

                    doc_id = args[0]
                    self.show_document(doc_id)

                elif command == "export":
                    if not args:
                        self.console.print(
                            "[red]Usage: export <output_path> [type][/red]"
                        )
                        continue

                    output_path = args[0]
                    item_type = args[1] if len(args) > 1 else None
                    self.export_data(output_path, item_type)

                else:
                    self.console.print(f"[red]Unknown command: {command}[/red]")
                    self.console.print("Type 'help' for available commands.")

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit.[/yellow]")
            except EOFError:
                self.console.print("\n[yellow]Goodbye![/yellow]")
                break
            except Exception as e:
                logger.error(f"REPL error: {e}")
                self.console.print(f"[red]Error: {e}[/red]")


@logger.catch
def resolve_database_path(
    db_path: str | None, collection_name: str | None, chapter_context: str | None
) -> tuple[str, str]:
    """Resolve database path and collection name from various inputs.

    Parameters
    ----------
    db_path : str, optional
        Direct path to database directory.
    collection_name : str, optional
        Name of the collection to use.
    chapter_context : str, optional
        Chapter context for automatic path resolution.

    Returns
    -------
    tuple[str, str]
        Resolved database path and collection name.

    Raises
    ------
    DatabaseNotFoundError
        If no valid database path can be resolved.
    """
    resolved_collection = collection_name or INTENT_COLLECTION_NAME

    # Direct path specified
    if db_path:
        path_obj = Path(db_path)
        if not path_obj.exists():
            raise DatabaseNotFoundError(f"Database path does not exist: {db_path}")
        return str(path_obj), resolved_collection

    # Chapter context specified
    if chapter_context:
        try:
            chapter_db_path = get_chapter_path(chapter_context, "chroma_db")
            if chapter_db_path.exists():
                return str(chapter_db_path), resolved_collection
            else:
                raise DatabaseNotFoundError(
                    f"Chapter database not found: {chapter_db_path}"
                )
        except Exception as e:
            raise DatabaseNotFoundError(
                f"Failed to resolve chapter context '{chapter_context}': {e}"
            ) from e

    # Default path
    default_path = Path(INTENT_DB_PERSIST_DIR)
    if default_path.exists():
        return str(default_path), resolved_collection

    raise DatabaseNotFoundError(
        "No database found. Specify --db-path, --chapter-context, or ensure "
        f"default database exists at: {INTENT_DB_PERSIST_DIR}"
    )


@click.command()
@click.option(
    "--db-path",
    "-d",
    type=click.Path(exists=False, path_type=Path),
    help="Direct path to ChromaDB persistence directory",
)
@click.option(
    "--collection-name",
    "-c",
    default=INTENT_COLLECTION_NAME,
    help=f"Collection name to use (default: {INTENT_COLLECTION_NAME})",
)
@click.option(
    "--chapter-context",
    "-ch",
    help="Chapter context for automatic database path resolution (e.g., 'chapter03')",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(
    db_path: Path | None,
    collection_name: str,
    chapter_context: str | None,
    verbose: bool,
) -> None:
    """Interactive REPL for Winston's ChromaDB intent databases.

    This tool provides a command-line interface for querying and inspecting
    ChromaDB databases used by Winston's intent discovery system.

    Examples:

        # Connect to specific database
        chroma-repl --db-path ./my_chromadb

        # Use chapter context
        chroma-repl --chapter-context chapter03

        # Specify collection name
        chroma-repl --collection-name custom_intents
    """
    if verbose:
        _ = logger.add(sys.stderr, level="DEBUG")
        logger.info("Verbose logging enabled")

    try:
        # Resolve database path and collection
        resolved_db_path, resolved_collection = resolve_database_path(
            db_path=str(db_path) if db_path else None,
            collection_name=collection_name,
            chapter_context=chapter_context,
        )

        # Initialize and run REPL
        repl = ChromaREPL()
        repl.connect_database(resolved_db_path, resolved_collection)
        repl.run_repl()

    except DatabaseNotFoundError as e:
        logger.error(f"Database error: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ChromaREPLError as e:
        logger.error(f"REPL error: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
