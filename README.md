# 📚 Data Librarian

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║       📚  D A T A   L I B R A R I A N  📚                    ║
║                                                               ║
║   AI-Powered Databricks Unity Catalog Discovery Assistant    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

An intelligent assistant that learns your Databricks Unity Catalog structure (catalogs, schemas, tables, columns, and metadata) and helps users discover the right data assets by asking natural language questions. Think of it as a "librarian" for your data lakehouse.

## ✨ Features

- 🔍 **Natural Language Search** - Ask questions in plain English to find data
- 🤖 **AI-Powered Responses** - Uses RAG (Retrieval-Augmented Generation) with LLMs
- 📊 **Complete Catalog Indexing** - Indexes catalogs, schemas, tables, and columns
- ⚡ **Fast Vector Search** - FAISS-powered similarity search for instant results
- 🔌 **Multiple LLM Providers** - Supports OpenAI, Databricks, or local-only mode
- 🖥️ **CLI & API Interfaces** - Use via command line or REST API
- 🐳 **Docker Ready** - Easy deployment with Docker Compose
- 🔒 **Secure** - Never logs tokens, uses environment variables

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [CLI](#cli-usage)
  - [API](#api-usage)
  - [Python](#python-usage)
- [How It Works](#how-it-works)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Data Librarian solves the common problem of data discovery in large data lakehouses. Instead of manually browsing through catalogs and schemas or writing complex metadata queries, you can simply ask:

- "Where can I find customer purchase history?"
- "What tables contain user profile information?"
- "Show me all tables with email addresses"

The system uses semantic search to find relevant tables and columns, then optionally uses an LLM to provide a natural language answer.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │   CLI (Click/Rich)   │    │   API (FastAPI)      │      │
│  └──────────────────────┘    └──────────────────────┘      │
└────────────────────┬──────────────────┬─────────────────────┘
                     │                  │
┌────────────────────┴──────────────────┴─────────────────────┐
│                   Librarian Engine                           │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐       │
│  │ Retriever  │  │Prompt Builder│  │  LLM Client   │       │
│  └────────────┘  └──────────────┘  └───────────────┘       │
└────────────────────┬──────────────────┬─────────────────────┘
                     │                  │
┌────────────────────┴──────────────────┴─────────────────────┐
│                  Indexing Pipeline                           │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐       │
│  │  Embedder  │  │Vector Store  │  │Index Builder  │       │
│  │ (S-BERT)   │  │   (FAISS)    │  │               │       │
│  └────────────┘  └──────────────┘  └───────────────┘       │
└────────────────────┬──────────────────┬─────────────────────┘
                     │                  │
┌────────────────────┴──────────────────┴─────────────────────┐
│                  Data Ingestion Layer                        │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐       │
│  │ Databricks │  │   Catalog    │  │   Metadata    │       │
│  │   Client   │  │   Parser     │  │    Store      │       │
│  └────────────┘  └──────────────┘  └───────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Data Ingestion** (`src/data_librarian/ingestion/`)
   - Connects to Databricks Unity Catalog REST API
   - Retrieves catalogs, schemas, tables, and columns
   - Stores metadata locally in SQLite

2. **Embedding & Indexing** (`src/data_librarian/indexing/`)
   - Generates embeddings using sentence-transformers
   - Builds FAISS vector index for similarity search
   - Enables fast semantic search over catalog metadata

3. **AI Query Engine** (`src/data_librarian/engine/`)
   - Retrieves relevant catalog entries via vector search
   - Builds context-aware prompts for LLMs
   - Supports multiple LLM providers (OpenAI, Databricks, local)

4. **User Interfaces** (`src/data_librarian/interface/`)
   - Rich CLI with interactive commands
   - REST API with FastAPI
   - Easy integration into existing workflows

## 🚀 Installation

### Option 1: Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/data-librarian.git
cd data-librarian

# Install dependencies
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Option 2: Using Docker

```bash
# Clone the repository
git clone https://github.com/yourusername/data-librarian.git
cd data-librarian

# Copy environment variables
cp .env.example .env
# Edit .env with your Databricks credentials

# Start with Docker Compose
docker-compose up
```

### Option 3: Install from PyPI (Coming Soon)

```bash
pip install data-librarian
```

## ⚙️ Configuration

Data Librarian uses environment variables for configuration. Create a `.env` file in your project root:

```bash
# Copy the example file
cp .env.example .env
```

### Required Settings

```bash
# Databricks Configuration
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your_databricks_personal_access_token
```

### Optional Settings

```bash
# LLM Provider (openai, databricks, or local)
LLM_PROVIDER=local

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=your_openai_api_key

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Search Configuration
TOP_K_RESULTS=5

# Data Storage
DATA_DIR=./data
```

### LLM Provider Options

- **`local`** - No LLM required; returns only search results (default, fastest)
- **`openai`** - Uses OpenAI API (requires `OPENAI_API_KEY`)
- **`databricks`** - Uses Databricks Foundation Model API (requires Databricks setup)

## 🎬 Quick Start

### 1. Set Up Environment

```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-token"
export LLM_PROVIDER="local"  # Start with local mode
```

### 2. Ingest Catalog

```bash
# Index your Databricks catalog
data-librarian ingest
```

This will:
- Connect to your Databricks workspace
- Retrieve all catalog metadata
- Generate embeddings
- Build the search index

### 3. Ask Questions

```bash
# Ask a natural language question
data-librarian ask "Where can I find customer data?"

# Filter by catalog
data-librarian ask "What sales tables exist?" --catalog production

# Filter by schema
data-librarian ask "Show me user tables" --catalog main --schema analytics
```

### 4. Explore Catalog

```bash
# Browse entire catalog
data-librarian explore

# Browse specific catalog
data-librarian explore production

# Browse specific schema
data-librarian explore production.sales
```

### 5. Check Status

```bash
data-librarian status
```

## 📖 Usage

### CLI Usage

#### Ingest Catalog

```bash
# First-time ingestion
data-librarian ingest

# Force refresh
data-librarian ingest --force
```

#### Ask Questions

```bash
# Basic question
data-librarian ask "Where is customer data?"

# With filters
data-librarian ask "Find user tables" --catalog main

# Schema-specific
data-librarian ask "What's in sales?" --schema sales
```

#### Explore Catalog

```bash
# Browse all
data-librarian explore

# Browse catalog
data-librarian explore production

# Browse schema
data-librarian explore production.sales
```

#### System Status

```bash
data-librarian status
```

### API Usage

Start the API server:

```bash
# Using uvicorn directly
uvicorn data_librarian.interface.api:app --host 0.0.0.0 --port 8000

# Or using Docker
docker-compose up
```

#### API Endpoints

**Ask a Question**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Where can I find customer data?",
    "top_k": 5
  }'
```

**Browse Catalog**
```bash
curl http://localhost:8000/catalog

# With filters
curl "http://localhost:8000/catalog?catalog=main&schema=sales"
```

**Trigger Ingestion**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true}'
```

**Get Status**
```bash
curl http://localhost:8000/status
```

**Health Check**
```bash
curl http://localhost:8000/health
```

### Python Usage

```python
from data_librarian.indexing.index_builder import IndexBuilder
from data_librarian.engine.librarian import Librarian

# Step 1: Ingest catalog (first time only)
builder = IndexBuilder()
stats = builder.ingest_and_index()

# Step 2: Create librarian
librarian = Librarian()

# Step 3: Ask questions
result = librarian.ask("Where can I find customer data?")
print(result['answer'])

# Step 4: Explore catalog
structure = librarian.explore(catalog="production")
print(structure)
```

## 🔍 How It Works

Data Librarian uses **Retrieval-Augmented Generation (RAG)** to answer questions:

1. **Ingestion Phase**
   - Fetches catalog metadata from Databricks Unity Catalog API
   - Parses and structures the data
   - Stores in local SQLite database

2. **Indexing Phase**
   - Generates text descriptions for tables and columns
   - Creates embeddings using sentence-transformers
   - Builds FAISS vector index for fast similarity search

3. **Query Phase**
   - User asks a natural language question
   - Question is embedded using the same model
   - FAISS finds top-K most similar catalog entries
   - Results are formatted as context

4. **Response Phase**
   - **Local mode**: Returns formatted search results
   - **LLM mode**: Sends context + question to LLM for natural language answer

### Why RAG?

- **Accurate**: Grounds answers in actual catalog metadata
- **Fast**: Vector search is extremely fast (milliseconds)
- **Offline-capable**: Works without LLM after indexing
- **Cost-effective**: Only sends relevant context to LLM
- **Scalable**: Handles large catalogs efficiently

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/data-librarian.git
cd data-librarian

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Code Style

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
data-librarian/
├── src/data_librarian/
│   ├── config/          # Configuration management
│   ├── ingestion/       # Databricks API client & parsers
│   ├── indexing/        # Embedding & vector search
│   ├── engine/          # RAG engine & LLM clients
│   └── interface/       # CLI & API
├── tests/               # Unit tests
├── examples/            # Example scripts
├── pyproject.toml       # Project configuration
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## 🧪 Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/data_librarian --cov-report=html

# Run specific test file
pytest tests/test_ingestion/test_databricks_client.py

# Run specific test
pytest tests/test_ingestion/test_databricks_client.py::test_list_catalogs
```

### Test Coverage

The test suite includes:
- Unit tests for all core components
- Mocked Databricks API responses
- Vector store operations
- Retrieval accuracy
- End-to-end workflow tests

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Add tests** for new functionality
5. **Ensure tests pass** (`pytest`)
6. **Format code** (`black src/ tests/`)
7. **Commit changes** (`git commit -m 'Add amazing feature'`)
8. **Push to branch** (`git push origin feature/amazing-feature`)
9. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Write clear docstrings for all functions/classes
- Add unit tests for new features
- Update documentation as needed
- Keep commits atomic and descriptive

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Databricks Unity Catalog](https://www.databricks.com/product/unity-catalog)
- Embeddings by [Sentence Transformers](https://www.sbert.net/)
- Vector search powered by [FAISS](https://github.com/facebookresearch/faiss)
- LLM support via [OpenAI](https://openai.com/) and Databricks
- CLI built with [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/)
- API powered by [FastAPI](https://fastapi.tiangolo.com/)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/data-librarian/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/data-librarian/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/data-librarian/wiki)

---

**Made with ❤️ for the data community**