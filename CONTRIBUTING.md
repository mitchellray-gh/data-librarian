# Contributing to Data Librarian

Thank you for your interest in contributing to Data Librarian! We welcome contributions from the community.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/data-librarian.git
   cd data-librarian
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-azure-support` - New features
- `fix/vector-store-bug` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/improve-retrieval` - Code refactoring

### 2. Make Your Changes

- Write clean, readable code following PEP 8 guidelines
- Add docstrings to all functions and classes
- Include type hints where appropriate
- Keep changes focused and atomic

### 3. Add Tests

All new features and bug fixes should include tests:

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src/data_librarian --cov-report=html

# Run specific test file
pytest tests/test_ingestion/test_databricks_client.py
```

### 4. Format Your Code

We use `black` for code formatting:

```bash
# Format all code
black src/ tests/

# Check formatting without making changes
black --check src/ tests/
```

### 5. Lint Your Code

```bash
# Run flake8
flake8 src/ tests/

# Run mypy for type checking
mypy src/
```

### 6. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add support for Azure Databricks workspaces"
```

Good commit message format:
```
Add/Fix/Update: Brief description (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain what changed and why, not how.

- Bullet points are okay
- Typically a hyphen or asterisk is used for the bullet
```

### 7. Push and Create a Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Description of what changed and why
- Link to any related issues
- Screenshots for UI changes

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use meaningful variable and function names
- Add docstrings to all public functions/classes

### Docstring Format

```python
def example_function(param1: str, param2: int) -> bool:
    """Brief description of what the function does.

    More detailed explanation if needed. Can span multiple lines
    and include examples or important notes.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
    """
    pass
```

### Type Hints

Use type hints for function parameters and return values:

```python
from typing import List, Dict, Optional

def process_items(items: List[str], config: Optional[Dict] = None) -> int:
    """Process a list of items."""
    pass
```

## Testing Guidelines

### Writing Tests

- Use descriptive test names: `test_list_catalogs_returns_valid_data`
- One assertion per test when possible
- Use fixtures for common setup
- Mock external dependencies (API calls, file systems, etc.)

### Test Structure

```python
def test_feature_name():
    """Test description."""
    # Arrange - Set up test data and conditions
    client = DatabricksClient(config)
    
    # Act - Execute the code being tested
    result = client.list_catalogs()
    
    # Assert - Verify the results
    assert len(result) > 0
    assert result[0]["name"] == "expected_name"
```

### Using Fixtures

```python
@pytest.fixture
def sample_config():
    """Fixture for test configuration."""
    return DatabricksConfig(host="https://test.com", token="test")

def test_with_fixture(sample_config):
    """Test using the fixture."""
    client = DatabricksClient(sample_config)
    assert client.config == sample_config
```

## Areas for Contribution

We welcome contributions in these areas:

### Features

- Support for additional LLM providers (Anthropic, Cohere, etc.)
- Advanced query capabilities (filters, sorting, etc.)
- Caching and performance improvements
- Support for other data platforms (Snowflake, BigQuery, etc.)
- Web UI interface
- Integration with data catalogs (Alation, Collibra, etc.)

### Documentation

- Improve README with more examples
- Add tutorials and guides
- Create architecture diagrams
- Document common use cases
- Translate documentation

### Testing

- Increase test coverage
- Add integration tests
- Performance benchmarks
- End-to-end testing

### Bug Fixes

Check the [Issues](https://github.com/yourusername/data-librarian/issues) page for known bugs.

## Pull Request Process

1. **Update documentation** - Update README or other docs if needed
2. **Add tests** - Ensure your changes are tested
3. **Update changelog** - Add an entry to CHANGELOG.md (if exists)
4. **Ensure CI passes** - All tests and checks must pass
5. **Request review** - Tag maintainers for review
6. **Address feedback** - Make requested changes promptly
7. **Squash commits** - Maintainers may ask you to squash commits

## Code Review Process

### As a Contributor

- Be open to feedback
- Respond to comments promptly
- Ask questions if something is unclear
- Be patient - reviews take time

### As a Reviewer

- Be respectful and constructive
- Explain the "why" behind suggestions
- Acknowledge good work
- Use questions instead of commands when appropriate

## Community Guidelines

- **Be respectful** - Treat everyone with respect
- **Be inclusive** - Welcome newcomers
- **Be collaborative** - Work together to improve the project
- **Be patient** - Remember that everyone is volunteering their time

## Questions?

- Open an [Issue](https://github.com/yourusername/data-librarian/issues) for bug reports or feature requests
- Start a [Discussion](https://github.com/yourusername/data-librarian/discussions) for questions
- Check existing issues and discussions before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to Data Librarian! 🎉
