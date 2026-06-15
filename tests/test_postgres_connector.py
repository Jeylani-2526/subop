# Verify that the health check returns True
def test_health_check(test_db_connection):
    assert test_db_connection.health_check() is True


# Verify that a simple SELECT query works correctly
def test_select_query(test_db_connection):
    result = test_db_connection.execute_query("SELECT 1 AS test")
    assert result[0]["test"] == 1


# Test basic write operations: INSERT, UPDATE and DELETE
def test_insert_update_delete(test_db_connection):

    # Create a temporary test table if it does not exist
    test_db_connection.execute_write("""
        CREATE TABLE IF NOT EXISTS test_users (
            id SERIAL PRIMARY KEY,
            name TEXT
        )
    """)

    # Insert a test record
    inserted_rows = test_db_connection.execute_write(
        "INSERT INTO test_users (name) VALUES (%s)",
        ("Omer",)
    )
    assert inserted_rows == 1

    # Update the inserted record
    updated_rows = test_db_connection.execute_write(
        "UPDATE test_users SET name = %s WHERE name = %s",
        ("Omer Updated", "Omer")
    )
    assert updated_rows >= 1

    # Remove the test record
    deleted_rows = test_db_connection.execute_write(
        "DELETE FROM test_users WHERE name = %s",
        ("Omer Updated",)
    )
    assert deleted_rows >= 1