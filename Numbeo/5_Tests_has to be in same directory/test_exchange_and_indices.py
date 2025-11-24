import sqlite3
import pandas as pd

# Configuration: database path and number of rows to display
DB_PATH = "numbeo.db"
TOP_N = 10


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a connection to the SQLite database."""
    return sqlite3.connect(db_path)


def get_item_id_for_pattern(conn: sqlite3.Connection, pattern: str) -> int:
    """Find the item_id for an item whose name starts with the given pattern."""
    query = """
        SELECT item_id, item_name
        FROM items
        WHERE item_name LIKE ? 
        LIMIT 1;
    """
    df = pd.read_sql(query, conn, params=(pattern + "%",))
    if df.empty:
        raise RuntimeError(f"No item found for pattern '{pattern}'.")
    item_id = int(df.loc[0, "item_id"])
    print(f"Using item_id={item_id} for item_name='{df.loc[0, 'item_name']}'")
    return item_id


def query_cheapest_gasoline_in_eur(conn: sqlite3.Connection, item_id: int, top_n: int) -> pd.DataFrame:
    """Query the cheapest countries for a given gasoline item, converted to EUR using exchange_rates."""
    query = f"""
        SELECT
            c.country_name,
            c.currency,
            cp.average_price AS price_local,
            er.one_eur_to_currency,
            cp.average_price / er.one_eur_to_currency AS price_eur,
            ci.cpi_index AS cost_of_living_index,  -- cpi_index used as cost-of-living proxy
            ci.quality_of_life_index,
            ci.purchasing_power_incl_rent_index
        FROM country_prices cp
        JOIN countries c ON cp.country_id = c.country_id
        JOIN exchange_rates er ON c.currency = er.currency_code
        LEFT JOIN country_indices ci ON c.country_id = ci.country_id
        WHERE cp.item_id = {item_id}
          AND cp.average_price IS NOT NULL
          AND er.one_eur_to_currency IS NOT NULL
        ORDER BY price_eur ASC
        LIMIT {top_n};
    """
    df = pd.read_sql(query, conn)
    return df

if __name__ == "__main__":
    # Step 1: open the SQLite database
    conn = get_connection(DB_PATH)

    # Step 2: identify the gasoline item_id from the items table
    gasoline_id = get_item_id_for_pattern(conn, "Gasoline (1 Liter)")

    # Step 3: query the top cheapest countries for gasoline in EUR with indices
    result_df = query_cheapest_gasoline_in_eur(conn, gasoline_id, TOP_N)

    # Step 4: display the results nicely
    print(f"\nTop {TOP_N} cheapest countries for Gasoline (1 Liter) in EUR:")
    print(result_df.to_string(index=False))

    # Step 5: close connection
    conn.close()
