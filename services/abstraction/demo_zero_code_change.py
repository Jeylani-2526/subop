from __future__ import annotations

import os
from typing import Any

# Import the shared abstraction layer.
# This layer provides the same public interface for all supported databases.
from services.abstraction.abstraction_layer import AbstractionLayer

# Import the MSSQL connector and rename its ConnectionConfig
# to avoid naming conflicts with the other database configs.
from services.connectors.mssql_connector import (
    ConnectionConfig as MSSQLConnectionConfig,
)
from services.connectors.mssql_connector import MSSQLConnector

# Import the MySQL connector and its database-specific configuration class.
from services.connectors.mysql_connector import (
    ConnectionConfig as MySQLConnectionConfig,
)
from services.connectors.mysql_connector import MySQLConnector

# Import the PostgreSQL connector and its database-specific configuration class.
from services.connectors.postgres_connector import (
    ConnectionConfig as PostgresConnectionConfig,
)
from services.connectors.postgres_connector import PostgresConnector

# Use one shared table name for the zero-code-change demonstration.
# The exact same table name is used in PostgreSQL, MySQL, and MSSQL.
TABLE_NAME = "demo_zero_code_change"


def run_demo(layer: AbstractionLayer) -> list[dict[str, Any]]:
    """
    Execute the exact same read/write logic against any configured database.

    This function contains no database-specific branching.
    The same SQL operations are passed through the AbstractionLayer
    regardless of whether the underlying database is PostgreSQL,
    MySQL, or MSSQL.
    """

    # Remove a previous demo table so the script can be executed repeatedly.
    layer.execute_write(f"DROP TABLE IF EXISTS {TABLE_NAME}")

    # Create the same simple demo table on every supported database.
    layer.execute_write(f"""
        CREATE TABLE {TABLE_NAME} (
            id INT PRIMARY KEY,
            name VARCHAR(100)
        )
        """)

    # Insert the same demo record using the shared abstraction interface.
    # No database-specific parameter placeholder is required here.
    layer.execute_write(f"""
        INSERT INTO {TABLE_NAME} (id, name)
        VALUES (1, 'SubOP')
        """)

    # Read the inserted record back using exactly the same query logic.
    rows = layer.execute_query(f"""
        SELECT id, name
        FROM {TABLE_NAME}
        WHERE id = 1
        """)

    # Return the database-independent List[Dict[str, Any]] result.
    return rows


def create_postgres_connector() -> PostgresConnector:
    """
    Create a PostgreSQL connector using environment variables
    with local development defaults.
    """

    # Build the PostgreSQL-specific connection configuration.
    config = PostgresConnectionConfig(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "subop"),
        username=os.getenv("POSTGRES_USER", "subop"),
        password=os.getenv("POSTGRES_PASSWORD", "subop_dev"),
    )

    # Return the connector without opening the connection yet.
    return PostgresConnector(config)


def create_mysql_connector() -> MySQLConnector:
    """
    Create a MySQL connector using environment variables
    with local development defaults.
    """

    # Build the MySQL-specific connection configuration.
    config = MySQLConnectionConfig(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "subop"),
        username=os.getenv("MYSQL_USER", "subop_app"),
        password=os.getenv("MYSQL_PASSWORD", "mysql_dev"),
    )

    # Return the connector without opening the connection yet.
    return MySQLConnector(config)


def create_mssql_connector() -> MSSQLConnector:
    """
    Create an MSSQL connector using environment variables
    with local development defaults.
    """

    # Build the MSSQL-specific connection configuration.
    config = MSSQLConnectionConfig(
        host=os.getenv("MSSQL_HOST", "localhost"),
        port=int(os.getenv("MSSQL_PORT", "1433")),
        database=os.getenv("MSSQL_DATABASE", "master"),
        username=os.getenv("MSSQL_USERNAME", "sa"),
        password=os.getenv(
            "MSSQL_PASSWORD",
            "YourStrong!Passw0rd",
        ),
    )

    # Return the connector without opening the connection yet.
    return MSSQLConnector(config)


def execute_database_demo(
    database: str,
    connector: Any,
) -> None:
    """
    Run the zero-code-change demo for one database connector.

    The connector handles the database-specific connection logic,
    while AbstractionLayer exposes the shared query/write interface.
    """

    # Print the database currently being tested.
    print(f"\n--- {database.upper()} ---")

    # Open the database-specific connection.
    connector.connect()

    try:
        # Wrap the connector with the common abstraction interface.
        layer = AbstractionLayer(
            connector=connector,
            database=database,
        )

        # Verify that the active database connection is healthy
        # before executing the demonstration.
        if not layer.health_check():
            raise RuntimeError(f"{database} health check failed")

        # Execute the exact same read/write logic for this database.
        rows = run_demo(layer)

        # Display the normalized database-independent result.
        print(f"Result: {rows}")

        # Confirm that this database completed the shared demo successfully.
        print("Zero-code-change demo passed.")

    finally:
        # Always close the database connection,
        # even if the demo raises an exception.
        connector.disconnect()


def main() -> None:
    """
    Create all supported database connectors and run
    the same demonstration against each one.
    """

    # Store the database identifier together with its connector.
    # Only connector/configuration setup differs between databases.
    databases = [
        ("postgresql", create_postgres_connector()),
        ("mysql", create_mysql_connector()),
        ("mssql", create_mssql_connector()),
    ]

    # Pass every database through the same execution workflow.
    for database, connector in databases:
        execute_database_demo(database, connector)


# Run the demonstration only when this file is executed directly.
# Importing this module from another file will not automatically run the demo.
if __name__ == "__main__":
    main()
