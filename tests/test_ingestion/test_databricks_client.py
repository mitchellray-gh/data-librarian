"""Tests for Databricks client."""

import pytest
from unittest.mock import Mock, patch
from data_librarian.ingestion.databricks_client import DatabricksClient, DatabricksConfig


@pytest.fixture
def databricks_config():
    """Fixture for Databricks configuration."""
    return DatabricksConfig(host="https://test.databricks.com", token="test-token")


@pytest.fixture
def mock_response():
    """Fixture for mock API response."""
    mock = Mock()
    mock.json.return_value = {"catalogs": []}
    mock.raise_for_status.return_value = None
    return mock


def test_databricks_client_initialization(databricks_config):
    """Test client initialization."""
    client = DatabricksClient(databricks_config)
    assert client.config == databricks_config
    assert client.base_url == "https://test.databricks.com"
    assert "Bearer test-token" in client.headers["Authorization"]


@patch("requests.get")
def test_list_catalogs(mock_get, databricks_config, mock_response):
    """Test listing catalogs."""
    mock_response.json.return_value = {
        "catalogs": [{"name": "test_catalog", "comment": "Test catalog"}]
    }
    mock_get.return_value = mock_response

    client = DatabricksClient(databricks_config)
    catalogs = client.list_catalogs()

    assert len(catalogs) == 1
    assert catalogs[0]["name"] == "test_catalog"
    mock_get.assert_called_once()


@patch("requests.get")
def test_list_schemas(mock_get, databricks_config, mock_response):
    """Test listing schemas."""
    mock_response.json.return_value = {
        "schemas": [{"name": "test_schema", "comment": "Test schema"}]
    }
    mock_get.return_value = mock_response

    client = DatabricksClient(databricks_config)
    schemas = client.list_schemas("test_catalog")

    assert len(schemas) == 1
    assert schemas[0]["name"] == "test_schema"


@patch("requests.get")
def test_list_tables(mock_get, databricks_config, mock_response):
    """Test listing tables."""
    mock_response.json.return_value = {
        "tables": [
            {
                "name": "test_table",
                "full_name": "test_catalog.test_schema.test_table",
                "comment": "Test table",
            }
        ]
    }
    mock_get.return_value = mock_response

    client = DatabricksClient(databricks_config)
    tables = client.list_tables("test_catalog", "test_schema")

    assert len(tables) == 1
    assert tables[0]["name"] == "test_table"


@patch("requests.get")
def test_get_table(mock_get, databricks_config, mock_response):
    """Test getting table details."""
    mock_response.json.return_value = {
        "name": "test_table",
        "full_name": "test_catalog.test_schema.test_table",
        "columns": [{"name": "id", "type_name": "INT"}],
    }
    mock_get.return_value = mock_response

    client = DatabricksClient(databricks_config)
    table = client.get_table("test_catalog.test_schema.test_table")

    assert table["name"] == "test_table"
    assert len(table["columns"]) == 1
