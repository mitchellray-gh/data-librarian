"""Databricks Unity Catalog REST API client."""

import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class DatabricksConfig:
    """Configuration for Databricks connection."""

    host: str
    token: str


class DatabricksClient:
    """Client for interacting with Databricks Unity Catalog REST API."""

    def __init__(self, config: DatabricksConfig):
        """Initialize the Databricks client.

        Args:
            config: Databricks configuration with host and token
        """
        self.config = config
        self.base_url = config.host.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        }

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to the Databricks API.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            requests.HTTPError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def list_catalogs(self) -> List[Dict[str, Any]]:
        """List all catalogs in the Unity Catalog.

        Returns:
            List of catalog dictionaries
        """
        response = self._make_request("/api/2.1/unity-catalog/catalogs")
        return response.get("catalogs", [])

    def list_schemas(self, catalog_name: str) -> List[Dict[str, Any]]:
        """List all schemas in a catalog.

        Args:
            catalog_name: Name of the catalog

        Returns:
            List of schema dictionaries
        """
        response = self._make_request(
            "/api/2.1/unity-catalog/schemas", params={"catalog_name": catalog_name}
        )
        return response.get("schemas", [])

    def list_tables(self, catalog_name: str, schema_name: str) -> List[Dict[str, Any]]:
        """List all tables in a schema.

        Args:
            catalog_name: Name of the catalog
            schema_name: Name of the schema

        Returns:
            List of table dictionaries
        """
        response = self._make_request(
            "/api/2.1/unity-catalog/tables",
            params={"catalog_name": catalog_name, "schema_name": schema_name},
        )
        return response.get("tables", [])

    def get_table(self, full_name: str) -> Dict[str, Any]:
        """Get detailed information about a table.

        Args:
            full_name: Full table name (catalog.schema.table)

        Returns:
            Table details dictionary including columns
        """
        response = self._make_request(f"/api/2.1/unity-catalog/tables/{full_name}")
        return response

    def get_catalog_structure(self) -> Dict[str, Any]:
        """Get the complete catalog structure.

        Returns:
            Dictionary with catalogs, schemas, tables, and columns
        """
        structure = {"catalogs": []}

        catalogs = self.list_catalogs()
        for catalog in catalogs:
            catalog_name = catalog["name"]
            catalog_data = {
                "name": catalog_name,
                "comment": catalog.get("comment", ""),
                "schemas": [],
            }

            schemas = self.list_schemas(catalog_name)
            for schema in schemas:
                schema_name = schema["name"]
                schema_data = {
                    "name": schema_name,
                    "comment": schema.get("comment", ""),
                    "tables": [],
                }

                tables = self.list_tables(catalog_name, schema_name)
                for table in tables:
                    table_full_name = table["full_name"]
                    table_details = self.get_table(table_full_name)

                    table_data = {
                        "name": table["name"],
                        "full_name": table_full_name,
                        "table_type": table.get("table_type", ""),
                        "comment": table.get("comment", ""),
                        "columns": table_details.get("columns", []),
                    }
                    schema_data["tables"].append(table_data)

                catalog_data["schemas"].append(schema_data)
            structure["catalogs"].append(catalog_data)

        return structure
