# db.py
import psycopg2
import psycopg2.extras
import pandas as pd

def get_connection():
    """
    Create a PostgreSQL connection using psycopg2.
    Adjust host, dbname, user, password as needed.
    """
    return psycopg2.connect(
        host="172.17.26.6",   # or "localhost"
        dbname="client_holdings",
        user="postgres",
        password="admin",
        cursor_factory=psycopg2.extras.DictCursor
    )

def fetch_client_total_with_rm():
    query = """
        SELECT
            f.clientcode,
            SUM(f.amount) AS total_amount,
            c."rmName"
        FROM "floorsheet" f
        LEFT JOIN "client_rm_map" c
            ON f.clientcode= c."clientCode"
        GROUP BY
            f.clientcode,
            c."rmName"
        ORDER BY total_amount DESC;
    """

    with get_connection() as conn:
        return pd.read_sql(query, conn)


if __name__ == "__main__":
    result_df:pd.DataFrame = fetch_client_total_with_rm()
    # print(result_df.head())
    result_df.sort_values(by='rmName', inplace=True)
    result_df.to_excel("rm_performance.xlsx", index=False)