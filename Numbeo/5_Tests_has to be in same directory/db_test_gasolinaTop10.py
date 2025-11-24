import sqlite3
import pandas as pd

# Configuration: paths for the SQLite database and how many countries to show
DB_PATH = "numbeo.db"
TOP_N = 10


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a connection to the SQLite database."""
    return sqlite3.connect(db_path)


def get_gasoline_item_id(conn: sqlite3.Connection) -> int:
    """Find the item_id corresponding to 'Gasoline (1 Liter)' in the items table."""
    query = """
        SELECT item_id, item_name
        FROM items
        WHERE item_name LIKE 'Gasoline (1 Liter)%'
        LIMIT 1;
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        raise RuntimeError("Could not find an item matching 'Gasoline (1 Liter)' in items table.")
    item_id = int(df.loc[0, "item_id"])
    print(f"Using item_id={item_id} for item_name='{df.loc[0, 'item_name']}'")
    return item_id


def get_top_cheapest_countries_for_item(
    conn: sqlite3.Connection, item_id: int, top_n: int
) -> pd.DataFrame:
    """Return the TOP_N cheapest countries for a given item_id based on average_price."""
    query = f"""
        SELECT
            c.country_name,
            c.currency,
            cp.average_price,
            cp.data_points
        FROM country_prices cp
        JOIN countries c ON cp.country_id = c.country_id
        WHERE cp.item_id = {item_id}
          AND cp.average_price IS NOT NULL
        ORDER BY cp.average_price ASC
        LIMIT {top_n};
    """
    df = pd.read_sql(query, conn)
    return df


if __name__ == "__main__":
    # Step 1: open database connection
    conn = get_connection(DB_PATH)

    # Step 2: get the item_id for gasoline (1 Liter)
    gasoline_item_id = get_gasoline_item_id(conn)

    # Step 3: query the TOP_N cheapest countries for gasoline
    top_gasoline_df = get_top_cheapest_countries_for_item(conn, gasoline_item_id, TOP_N)

    # Step 4: print the result nicely
    print(f"\nTop {TOP_N} cheapest countries for Gasoline (1 Liter):")
    print(top_gasoline_df.to_string(index=False))

    # Step 5: close the connection
    conn.close()
