import sqlite3
import pandas as pd
import os

DB_NAME = "snacks.db"
CSV_FILE = "snacks_data.csv"

def init_db():
    print("Initializing Database from CSV...")
    
    # Check if CSV exists
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found.")
        return

    # Load CSV
    try:
        df = pd.read_csv(CSV_FILE)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Reset Tables
    cursor.execute("DROP TABLE IF EXISTS product_info")
    cursor.execute("""
        CREATE TABLE product_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            제품명 TEXT,
            제조사 TEXT,
            칼로리 INTEGER,
            원산지 TEXT,
            카테고리 TEXT,
            이모지 TEXT,
            원재료명 TEXT
        )
    """)
    
    # Insert Data
    for index, row in df.iterrows():
        cursor.execute("INSERT INTO product_info (제품명, 제조사, 칼로리, 원산지, 카테고리, 이모지, 원재료명) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (row['PRDLST_NM'], row['BSSH_NM'], row['CALORIE'], row['ORIGIN'], row['CATEGORY'], row['EMOJI'], row['RAWMTRL_NM']))
        
    conn.commit()
    conn.close()
    print(f"Database seeded with {len(df)} records.")

if __name__ == "__main__":
    init_db()
