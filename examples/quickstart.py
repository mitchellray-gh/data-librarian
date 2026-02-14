"""Quickstart example for Data Librarian."""

from data_librarian.config.settings import settings
from data_librarian.indexing.index_builder import IndexBuilder
from data_librarian.engine.librarian import Librarian

# Ensure environment variables are set
# DATABRICKS_HOST and DATABRICKS_TOKEN must be configured

def main():
    """Run a quick example of Data Librarian."""
    
    print("📚 Data Librarian Quickstart\n")
    
    # Step 1: Ingest and index the catalog
    print("Step 1: Ingesting catalog data...")
    try:
        settings.validate()
        builder = IndexBuilder()
        stats = builder.ingest_and_index(force_refresh=True)
        print(f"✓ Indexed {stats['searchable_items']} items")
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set the following environment variables:")
        print("  - DATABRICKS_HOST")
        print("  - DATABRICKS_TOKEN")
        return
    
    # Step 2: Create librarian and ask questions
    print("\nStep 2: Asking questions...")
    librarian = Librarian()
    
    # Example questions
    questions = [
        "Where can I find customer data?",
        "What tables contain sales information?",
        "Show me tables related to user profiles",
    ]
    
    for question in questions:
        print(f"\nQ: {question}")
        result = librarian.ask(question)
        print(f"A: {result['answer'][:200]}...")  # Show first 200 chars
        print(f"   (based on {result['num_results']} catalog entries)")
    
    # Step 3: Explore catalog structure
    print("\nStep 3: Exploring catalog...")
    structure = librarian.explore()
    
    for catalog_name in structure.keys():
        print(f"\n📁 {catalog_name}")
        for schema_name, schema_data in structure[catalog_name].items():
            table_count = len(schema_data.get('tables', []))
            print(f"  └─ {schema_name} ({table_count} tables)")
    
    print("\n✓ Quickstart complete!")


if __name__ == "__main__":
    main()
