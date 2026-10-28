import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, seed_initial_data

if __name__ == '__main__':
    conn = get_db()
    seed_initial_data(conn)
    conn.close()
    print("Seed data successfully populated.")

