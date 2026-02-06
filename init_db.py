import sqlite3
import csv
from pathlib import Path
from config import DB_PATH

def create_tables(conn):
    cur = conn.cursor()

    # Enable foreign keys
    cur.execute("PRAGMA foreign_keys = ON;")

    # BOOK
    cur.execute("""
    CREATE TABLE IF NOT EXISTS BOOK (
        Isbn TEXT PRIMARY KEY,
        Title TEXT NOT NULL
    );
    """)

    # AUTHORS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS AUTHORS (
        Author_id INTEGER PRIMARY KEY,
        Name TEXT NOT NULL
    );
    """)

    # BOOK_AUTHORS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS BOOK_AUTHORS (
        Isbn TEXT NOT NULL,
        Author_id INTEGER NOT NULL,
        PRIMARY KEY (Isbn, Author_id),
        FOREIGN KEY (Isbn) REFERENCES BOOK(Isbn),
        FOREIGN KEY (Author_id) REFERENCES AUTHORS(Author_id)
    );
    """)

    # BORROWER
    cur.execute("""
    CREATE TABLE IF NOT EXISTS BORROWER (
        Card_id TEXT PRIMARY KEY,
        Bname TEXT NOT NULL,
        Address TEXT NOT NULL,
        Phone TEXT NOT NULL,
        Ssn TEXT NOT NULL UNIQUE
    );
    """)

    # BOOK_LOANS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS BOOK_LOANS (
        Loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Isbn TEXT NOT NULL,
        Card_id TEXT NOT NULL,
        Date_out DATE NOT NULL,
        Due_date DATE NOT NULL,
        Date_in DATE,
        FOREIGN KEY (Isbn) REFERENCES BOOK(Isbn),
        FOREIGN KEY (Card_id) REFERENCES BORROWER(Card_id)
    );
    """)

    # FINES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS FINES (
        Loan_id INTEGER PRIMARY KEY,
        Fine_amt DECIMAL(10,2) NOT NULL,
        Paid INTEGER NOT NULL CHECK (Paid IN (0,1)),
        FOREIGN KEY (Loan_id) REFERENCES BOOK_LOANS(Loan_id)
    );
    """)

    conn.commit()


def load_csv(conn, csv_file, table, col_map):
    cur = conn.cursor()
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_cols = list(col_map.keys())
            table_cols = list(col_map.values())
            
            values = [row[col] for col in csv_cols]
            placeholders = ",".join(["?"] * len(table_cols))
            
            sql = f"INSERT INTO {table} ({','.join(table_cols)}) VALUES ({placeholders})"
            cur.execute(sql, values)
    conn.commit()


def main():
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()

    conn = sqlite3.connect(DB_PATH)

    create_tables(conn)

    load_csv(conn, "book.csv", "BOOK", {"ISBN13": "Isbn", "Title": "Title"})
    load_csv(conn, "authors.csv", "AUTHORS", {"Author_id": "Author_id", "Author": "Name"})
    load_csv(conn, "book_authors.csv", "BOOK_AUTHORS", {"ISBN13": "Isbn", "Author_id": "Author_id"})
    load_csv(conn, "borrower.csv", "BORROWER", {
        "Card_id": "Card_id", 
        "Bname": "Bname", 
        "Address": "Address", 
        "Phone": "Phone", 
        "Ssn": "Ssn"
    })

    conn.close()


if __name__ == "__main__":
    main()
