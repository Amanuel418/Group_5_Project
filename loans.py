import sqlite3
from datetime import datetime, timedelta
import fines
from config import DB_PATH

def checkout(isbn, card_id, override=False):
    """
    Check out a book for a borrower.
    
    Args:
        isbn (str): ISBN of the book to checkout
        card_id (str): Borrower card ID
        override (bool): If True, bypass restrictions (fines, max loans, availability)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # Check if borrower exists
        cur.execute("SELECT * FROM BORROWER WHERE Card_id = ?", (card_id,))
        borrower = cur.fetchone()
        if not borrower:
            conn.close()
            return False, f"Error: Borrower with card ID '{card_id}' not found."
        
        # Check if book exists
        cur.execute("SELECT * FROM BOOK WHERE Isbn = ?", (isbn,))
        book = cur.fetchone()
        if not book:
            conn.close()
            return False, f"Error: Book with ISBN '{isbn}' not found."
        
        # Check if borrower has unpaid fines
        if not override and fines.has_unpaid_fines(card_id):
            conn.close()
            return False, "Error: Borrower has unpaid fines. Cannot checkout books until fines are paid."
        
        # Check if borrower already has 3 active loans
        cur.execute("""
            SELECT COUNT(*) as count
            FROM BOOK_LOANS
            WHERE Card_id = ? AND Date_in IS NULL
        """, (card_id,))
        active_loans = cur.fetchone()
        if not override and active_loans['count'] >= 3:
            conn.close()
            return False, f"Error: Borrower already has 3 active loans. Maximum limit reached."
        
        # Check if book is already checked out
        cur.execute("""
            SELECT COUNT(*) as count
            FROM BOOK_LOANS
            WHERE Isbn = ? AND Date_in IS NULL
        """, (isbn,))
        book_status = cur.fetchone()
        if book_status['count'] > 0:
            conn.close()
            return False, f"Error: Book with ISBN '{isbn}' is already checked out and not available."
        
        # Create new loan
        date_out = datetime.now().date()
        due_date = date_out + timedelta(days=14)
        
        cur.execute("""
            INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date)
            VALUES (?, ?, ?, ?)
        """, (isbn, card_id, date_out, due_date))
        
        conn.commit()
        conn.close()
        
        return True, f"Successfully checked out book '{book['Title']}' (ISBN: {isbn}). Due date: {due_date}."
    
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error: {str(e)}"


def find_loans_by_search(search_term):
    """
    Find loans by searching on ISBN, card_id, or borrower name (substring matching).
    
    Args:
        search_term (str): Search query (case-insensitive, substring matching)
    
    Returns:
        list: List of dictionaries with loan information
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    search_pattern = f"%{search_term.lower()}%"
    
    query = """
    SELECT 
        bl.Loan_id,
        bl.Isbn,
        b.Title,
        bl.Card_id,
        br.Bname,
        bl.Date_out,
        bl.Due_date,
        bl.Date_in
    FROM BOOK_LOANS bl
    JOIN BOOK b ON bl.Isbn = b.Isbn
    JOIN BORROWER br ON bl.Card_id = br.Card_id
    WHERE (LOWER(bl.Isbn) LIKE ? 
           OR LOWER(bl.Card_id) LIKE ?
           OR LOWER(br.Bname) LIKE ?)
      AND bl.Date_in IS NULL
    ORDER BY bl.Due_date
    """
    
    cur.execute(query, (search_pattern, search_pattern, search_pattern))
    results = cur.fetchall()
    
    loans = []
    for row in results:
        loans.append({
            'Loan_id': row['Loan_id'],
            'ISBN': row['Isbn'],
            'Title': row['Title'],
            'Card_id': row['Card_id'],
            'Borrower_name': row['Bname'],
            'Date_out': row['Date_out'],
            'Due_date': row['Due_date'],
            'Date_in': row['Date_in']
        })
    
    conn.close()
    return loans


def display_loans(loans):
    """
    Display loan search results in a formatted table.
    
    Args:
        loans (list): List of loan dictionaries
    """
    if not loans:
        print("No active loans found.")
        return
    
    print(f"\n{'NO':<4} {'LOAN_ID':<10} {'ISBN':<15} {'TITLE':<40} {'CARD_ID':<12} {'BORROWER':<30} {'DATE_OUT':<12} {'DUE_DATE':<12}")
    print("-" * 150)
    
    for idx, loan in enumerate(loans, 1):
        loan_id = str(loan['Loan_id'])
        isbn = loan['ISBN'][:14]
        title = loan['Title'][:39]
        card_id = loan['Card_id']
        borrower = loan['Borrower_name'][:29]
        date_out = loan['Date_out']
        due_date = loan['Due_date']
        
        print(f"{idx:<4} {loan_id:<10} {isbn:<15} {title:<40} {card_id:<12} {borrower:<30} {date_out:<12} {due_date:<12}")
    
    print()


def checkin(loan_ids):
    """
    Check in one or more books by loan IDs.
    
    Args:
        loan_ids (list): List of loan IDs to check in (1-3 loans)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not loan_ids:
        return False, "Error: No loan IDs provided."
    
    if len(loan_ids) > 3:
        return False, "Error: Cannot check in more than 3 books at once."
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        date_in = datetime.now().date()
        checked_in_count = 0
        errors = []
        
        for loan_id in loan_ids:
            # Verify loan exists and is still active
            cur.execute("""
                SELECT * FROM BOOK_LOANS
                WHERE Loan_id = ? AND Date_in IS NULL
            """, (loan_id,))
            loan = cur.fetchone()
            
            if not loan:
                errors.append(f"Loan ID {loan_id} not found or already checked in.")
                continue
            
            # Update loan with check-in date
            cur.execute("""
                UPDATE BOOK_LOANS
                SET Date_in = ?
                WHERE Loan_id = ?
            """, (date_in, loan_id))
            
            checked_in_count += 1
        
        conn.commit()
        conn.close()
        
        if errors:
            return False, f"Errors: {'; '.join(errors)}. Checked in {checked_in_count} book(s)."
        
        return True, f"Successfully checked in {checked_in_count} book(s)."
    
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error: {str(e)}"


if __name__ == "__main__":
    # Test checkout
    success, message = checkout("9780195153445", "ID000001")
    print(message)
    
    # Test finding loans
    loans = find_loans_by_search("ID000001")
    display_loans(loans)

