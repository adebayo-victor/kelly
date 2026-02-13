import os
from cs50 import SQL

# Create the file if it doesn't exist
if not os.path.exists("shop.db"):
    open("shop.db", "w").close()

db = SQL(os.environ.get("DATABASE_URL"))

def setup():
    # 1. Store Customer identity
    db.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            jid TEXT UNIQUE,
            username TEXT
        )
    """)

    # 2. Store Chat History as TEXT (instead of .txt files)
    db.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id SERIAL PRIMARY KEY ,
            jid TEXT UNIQUE,
            history TEXT DEFAULT ''
        )
    """)

    # 3. Store the Otaku Orders
    db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY ,
            customer_jid TEXT,
            item_type TEXT,
            art_choice TEXT,
            order_text TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("✅ shop.db initialized with CS50 SQL!")

if __name__ == "__main__":
    setup()


'''from cs50 import SQL
db = SQL("sqlite:///shop.db")
db.execute("DELETE  FROM chat_logs")
print("deleted chatlog history")'''