"""Command-line interface for Data Librarian."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from ..config.settings import settings
from ..indexing.index_builder import IndexBuilder
from ..engine.librarian import Librarian

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """📚 Data Librarian - AI-powered Databricks catalog assistant."""
    pass


@cli.command()
@click.option("--force", is_flag=True, help="Force refresh even if data exists")
def ingest(force):
    """Ingest and index the Databricks Unity Catalog."""
    console.print("\n[bold blue]📚 Data Librarian - Catalog Ingestion[/bold blue]\n")

    try:
        # Validate settings
        settings.validate()

        # Create index builder
        index_builder = IndexBuilder()

        # Run ingestion
        with console.status("[bold green]Ingesting catalog..."):
            stats = index_builder.ingest_and_index(force_refresh=force)

        # Display results
        if stats["searchable_items"] > 0:
            table = Table(title="Ingestion Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="magenta")

            table.add_row("Catalogs", str(stats["catalogs"]))
            table.add_row("Schemas", str(stats["schemas"]))
            table.add_row("Tables", str(stats["tables"]))
            table.add_row("Columns", str(stats["columns"]))
            table.add_row("Indexed Items", str(stats["searchable_items"]))

            console.print(table)
            console.print("\n[bold green]✓[/bold green] Ingestion complete!")
        else:
            console.print("[yellow]No new data to ingest.[/yellow]")

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        console.print("\n[yellow]Please set required environment variables:[/yellow]")
        console.print("  - DATABRICKS_HOST")
        console.print("  - DATABRICKS_TOKEN")
        return 1
    except Exception as e:
        console.print(f"[bold red]Error during ingestion:[/bold red] {str(e)}")
        return 1


@cli.command()
@click.argument("question")
@click.option("--catalog", help="Filter by catalog name")
@click.option("--schema", help="Filter by schema name")
def ask(question, catalog, schema):
    """Ask a natural language question about the catalog."""
    console.print("\n[bold blue]📚 Data Librarian[/bold blue]\n")

    try:
        # Create librarian
        librarian = Librarian()

        # Check if indexed
        status = librarian.get_status()
        if status["status"] != "ready":
            console.print(
                "[bold red]Error:[/bold red] Catalog not indexed. Run 'data-librarian ingest' first."
            )
            return 1

        # Ask question
        with console.status("[bold green]Searching catalog..."):
            result = librarian.ask(question, catalog=catalog, schema=schema)

        # Display question
        console.print(Panel(f"[bold]{question}[/bold]", title="Question", border_style="blue"))

        # Display answer
        console.print("\n[bold green]Answer:[/bold green]\n")
        console.print(Markdown(result["answer"]))

        # Display context
        if result["context_items"]:
            console.print(f"\n[dim]Based on {result['num_results']} catalog entries[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@cli.command()
@click.argument("path", required=False)
def explore(path):
    """Browse catalog structure (e.g., 'catalog.schema')."""
    console.print("\n[bold blue]📚 Data Librarian - Catalog Explorer[/bold blue]\n")

    try:
        # Parse path
        catalog = None
        schema = None
        if path:
            parts = path.split(".")
            if len(parts) >= 1:
                catalog = parts[0]
            if len(parts) >= 2:
                schema = parts[1]

        # Create librarian
        librarian = Librarian()

        # Get structure
        structure = librarian.explore(catalog=catalog, schema=schema)

        # Display structure
        if not structure:
            console.print("[yellow]No catalog data found. Run 'data-librarian ingest' first.[/yellow]")
            return

        for cat_name, schemas in structure.items():
            console.print(f"\n[bold cyan]📁 {cat_name}[/bold cyan]")

            for schema_name, schema_data in schemas.items():
                console.print(f"  [bold]└─ {schema_name}[/bold]")

                # Show tables
                tables = schema_data.get("tables", [])
                if tables:
                    console.print(f"     [dim]Tables: {len(tables)}[/dim]")
                    for table in tables[:5]:  # Show first 5
                        console.print(f"       • {table}")
                    if len(tables) > 5:
                        console.print(f"       [dim]... and {len(tables) - 5} more[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@cli.command()
def status():
    """Show ingestion status and statistics."""
    console.print("\n[bold blue]📚 Data Librarian - Status[/bold blue]\n")

    try:
        # Create librarian
        librarian = Librarian()
        status_info = librarian.get_status()

        # Create status table
        table = Table(title="System Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Status", status_info["status"])
        table.add_row("Indexed Items", str(status_info["indexed_items"]))
        table.add_row("Last Updated", status_info["last_updated"] or "Never")
        table.add_row("Embedding Model", status_info["embedding_model"])
        table.add_row("LLM Provider", status_info["llm_provider"])
        table.add_row("Top-K Results", str(status_info["top_k"]))

        console.print(table)

        if status_info["status"] != "ready":
            console.print("\n[yellow]⚠ Catalog not indexed. Run 'data-librarian ingest' to get started.[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


if __name__ == "__main__":
    cli()
