import logging
from database import execute
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

def run():
    execute("""
    CREATE TABLE IF NOT EXISTS catalog (
        id SERIAL PRIMARY KEY,
        item_type VARCHAR(20) NOT NULL,
        name VARCHAR(255) NOT NULL,
        price NUMERIC(10, 2) DEFAULT 0.00,
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
    );
    """)

    res = execute("SELECT COUNT(*) as c FROM catalog", fetch=True)
    if res and res[0]['c'] == 0:
        defaults = [
            ("PLAN", "PLC 397 - Plan 180GB MiFi TCL MW45AF", 100),
            ("PLAN", "PLC 376 - PLAN 30 GB NORMAL", 80),
            ("PLAN", "PLC345 - Plan 50GB", 120),
            ("EQUIPO", "iPhone 16e 128GB", 800),
            ("EQUIPO", "Samsung Galaxy A06 128GB", 150)
        ]
        for t, n, p in defaults:
            execute("INSERT INTO catalog (item_type, name, price) VALUES (%s, %s, %s)", (t, n, p))
        print("Catalog seeded!")
    else:
        print("Catalog already exists.")

if __name__ == '__main__':
    run()
