import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.environ["DB_HOST"],
    port=os.environ.get("DB_PORT", "5432"),
    dbname=os.environ.get("DB_NAME", "postgres"),
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    connect_timeout=10,
)

with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM predictions;")
    print("Row count:", cur.fetchone()[0])

    cur.execute("SELECT * FROM predictions ORDER BY created_at DESC LIMIT 5;")
    for row in cur.fetchall():
        print(row)

conn.close()