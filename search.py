import sqlite3
from datetime import datetime
from config import DB_PATH

def search(search_term):
    """
    Search for books by ISBN, title, or author(s) with case-insensitive substring matching.
    
    Args:
        search_term (str): Search query (case-insensitive, substring matching)
    
    Returns:
        list: List of dictionaries with keys: ISBN, Title, Authors, Status
              Status is "IN" if available, "OUT" if checked out
    """
    # Handle empty or whitespace-only search terms
    if not search_term or not search_term.strip():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Normalize search term for case-insensitive matching
    search_pattern = f"%{search_term.strip().lower()}%"
    
    # Find all ISBNs that match by ISBN, Title, or Author name
    # Then get all authors for those books
    query = """
    SELECT 
        b.Isbn,
        b.Title,
        COALESCE(GROUP_CONCAT(a.Name, ', '), 'Unknown') as Authors
    FROM BOOK b
    LEFT JOIN BOOK_AUTHORS ba ON b.Isbn = ba.Isbn
    LEFT JOIN AUTHORS a ON ba.Author_id = a.Author_id
    WHERE b.Isbn IN (
        SELECT DISTINCT Isbn 
        FROM BOOK 
        WHERE LOWER(Isbn) LIKE ? OR LOWER(Title) LIKE ?
        UNION
        SELECT DISTINCT ba2.Isbn
        FROM BOOK_AUTHORS ba2
        JOIN AUTHORS a2 ON ba2.Author_id = a2.Author_id
        WHERE LOWER(a2.Name) LIKE ?
    )
    GROUP BY b.Isbn, b.Title
    ORDER BY b.Isbn
    """
    
    cur.execute(query, (search_pattern, search_pattern, search_pattern))
    results = cur.fetchall()
    
    # Check availability for each book
    search_results = []
    for row in results:
        isbn = row['Isbn']
        title = row['Title']
        authors = row['Authors']  # Already handled by COALESCE in query
        
        # Check if book is currently checked out (Date_in is NULL)
        availability_query = """
        SELECT Card_id
        FROM BOOK_LOANS
        WHERE Isbn = ? AND Date_in IS NULL
        """
        cur.execute(availability_query, (isbn,))
        loan_info = cur.fetchone()
        
        if loan_info:
            status = "OUT"
            borrower_id = loan_info['Card_id']
        else:
            status = "IN"
            borrower_id = "NULL"
        
        search_results.append({
            'ISBN': isbn,
            'Title': title,
            'Authors': authors,
            'Status': status,
            'Borrower_id': borrower_id
        })
    
    conn.close()
    return search_results


def display_search_results(results):
    """
    Display search results in a formatted table.
    
    Args:
        results (list): List of search result dictionaries
    """
    if not results:
        print("No results found.")
        return
    
    # Print header
    print(f"\n{'NO':<4} {'ISBN':<15} {'TITLE':<50} {'AUTHORS':<40} {'STATUS':<6}")
    print("-" * 120)
    
    # Print results
    for idx, result in enumerate(results, 1):
        isbn = result['ISBN'][:14]  # Truncate if too long
        title = result['Title'][:49]  # Truncate if too long
        authors = result['Authors'][:39]  # Truncate if too long
        status = result['Status']
        
        print(f"{idx:<4} {isbn:<15} {title:<50} {authors:<40} {status:<6}")
    
    print()


if __name__ == "__main__":
    # Test the search function
    results = search("will")
    display_search_results(results)

