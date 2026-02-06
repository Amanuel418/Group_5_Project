import sqlite3
from datetime import datetime, date
from decimal import Decimal
from config import DB_PATH
FINE_RATE = Decimal('0.25')  # $0.25 per day

def has_unpaid_fines(card_id):
    """
    Check if a borrower has any unpaid fines.
    
    Args:
        card_id (str): Borrower card ID
    
    Returns:
        bool: True if borrower has unpaid fines, False otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = """
    SELECT COUNT(*) as count
    FROM FINES f
    JOIN BOOK_LOANS bl ON f.Loan_id = bl.Loan_id
    WHERE bl.Card_id = ? AND f.Paid = 0
    """
    
    cur.execute(query, (card_id,))
    result = cur.fetchone()
    conn.close()
    
    return result['count'] > 0


def calculate_fine_amount(due_date, date_in=None):
    """
    Calculate fine amount for a loan.
    
    Args:
        due_date: Due date (date object or string in YYYY-MM-DD format)
        date_in: Return date if book is returned, None if still out (date object or string)
    
    Returns:
        Decimal: Fine amount (0 if not overdue)
    """
    if isinstance(due_date, str):
        due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
    
    today = date.today()
    
    # Determine the end date for calculation
    if date_in:
        # Book has been returned - use date_in
        if isinstance(date_in, str):
            date_in = datetime.strptime(date_in, '%Y-%m-%d').date()
        end_date = date_in
    else:
        # Book still out - use today
        end_date = today
    
    # Calculate days overdue
    if end_date <= due_date:
        return Decimal('0.00')
    
    days_overdue = (end_date - due_date).days
    fine_amount = Decimal(days_overdue) * FINE_RATE
    
    # Round to 2 decimal places
    return fine_amount.quantize(Decimal('0.01'))


def update_fines():
    """
    Update/refresh entries in the FINES table.
    Handles both scenarios:
    1. Late books that have been returned: (date_in - due_date) * $0.25
    2. Late books still out: (TODAY - due_date) * $0.25
    
    Update logic:
    - If row exists and paid == FALSE (0), update fine_amt if different
    - If row exists and paid == TRUE (1), do nothing
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    today = date.today()
    
    # Find all overdue loans (both returned and still out)
    query = """
    SELECT Loan_id, Due_date, Date_in
    FROM BOOK_LOANS
    WHERE Due_date < ?
    """
    
    cur.execute(query, (today,))
    overdue_loans = cur.fetchall()
    
    for loan in overdue_loans:
        loan_id = loan['Loan_id']
        due_date = loan['Due_date']
        date_in = loan['Date_in']
        
        # Calculate fine amount
        fine_amount = calculate_fine_amount(due_date, date_in)
        
        if fine_amount > 0:
            # Check if fine already exists
            cur.execute("SELECT * FROM FINES WHERE Loan_id = ?", (loan_id,))
            existing_fine = cur.fetchone()
            
            if existing_fine:
                # If paid == TRUE (1), do nothing
                if existing_fine['Paid'] == 1:
                    continue
                
                # If paid == FALSE (0), update fine_amt if different
                existing_amount = Decimal(str(existing_fine['Fine_amt']))
                if existing_amount != fine_amount:
                    cur.execute("""
                        UPDATE FINES
                        SET Fine_amt = ?
                        WHERE Loan_id = ? AND Paid = 0
                    """, (str(fine_amount), loan_id))
            else:
                # Create new fine (always unpaid initially)
                cur.execute("""
                    INSERT INTO FINES (Loan_id, Fine_amt, Paid)
                    VALUES (?, ?, 0)
                """, (loan_id, str(fine_amount)))
    
    conn.commit()
    conn.close()


def get_fines_by_borrower(include_paid=False):
    """
    Get fines grouped by borrower (card_no), with total sum per borrower.
    
    Args:
        include_paid (bool): If True, include paid fines. If False, only unpaid fines.
    
    Returns:
        dict: Dictionary with card_id as key, containing borrower info and list of fines
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if include_paid:
        paid_filter = ""
    else:
        paid_filter = "AND f.Paid = 0"
    
    query = f"""
    SELECT 
        br.Card_id,
        br.Bname,
        f.Loan_id,
        f.Fine_amt,
        f.Paid,
        bl.Isbn,
        b.Title,
        bl.Due_date,
        bl.Date_in
    FROM FINES f
    JOIN BOOK_LOANS bl ON f.Loan_id = bl.Loan_id
    JOIN BORROWER br ON bl.Card_id = br.Card_id
    JOIN BOOK b ON bl.Isbn = b.Isbn
    WHERE 1=1 {paid_filter}
    ORDER BY br.Card_id, f.Paid, bl.Due_date
    """
    
    cur.execute(query)
    results = cur.fetchall()
    
    # Group by borrower
    borrowers = {}
    for row in results:
        card_id = row['Card_id']
        
        if card_id not in borrowers:
            borrowers[card_id] = {
                'Card_id': card_id,
                'Bname': row['Bname'],
                'fines': [],
                'total_fine': Decimal('0.00')
            }
        
        fine_amt = Decimal(str(row['Fine_amt']))
        borrowers[card_id]['fines'].append({
            'Loan_id': row['Loan_id'],
            'Fine_amt': fine_amt,
            'Paid': row['Paid'],
            'ISBN': row['Isbn'],
            'Title': row['Title'],
            'Due_date': row['Due_date'],
            'Date_in': row['Date_in']
        })
        
        # Only add to total if unpaid
        if row['Paid'] == 0:
            borrowers[card_id]['total_fine'] += fine_amt
    
    conn.close()
    return borrowers


def display_fines(include_paid=False):
    """
    Display fines grouped by borrower with totals.
    
    Args:
        include_paid (bool): If True, include paid fines. If False, only unpaid fines.
    """
    borrowers = get_fines_by_borrower(include_paid)
    
    if not borrowers:
        status = "unpaid" if not include_paid else "all"
        print(f"\nNo {status} fines found.")
        return
    
    status_text = "All Fines" if include_paid else "Unpaid Fines"
    print(f"\n{status_text} - Grouped by Borrower")
    print("=" * 120)
    
    for card_id, borrower_data in borrowers.items():
        print(f"\nCard ID: {borrower_data['Card_id']}")
        print(f"Borrower: {borrower_data['Bname']}")
        print(f"Total {'Unpaid ' if not include_paid else ''}Fine: ${borrower_data['total_fine']:.2f}")
        print("-" * 120)
        print(f"{'Loan_ID':<10} {'ISBN':<15} {'Title':<40} {'Due_Date':<12} {'Date_In':<12} {'Fine_Amt':<10} {'Paid':<6}")
        print("-" * 120)
        
        for fine in borrower_data['fines']:
            paid_status = "Yes" if fine['Paid'] == 1 else "No"
            date_in_str = fine['Date_in'] if fine['Date_in'] else "Still Out"
            title = fine['Title'][:39] if len(fine['Title']) > 39 else fine['Title']
            
            print(f"{fine['Loan_id']:<10} {fine['ISBN']:<15} {title:<40} {fine['Due_date']:<12} {date_in_str:<12} ${fine['Fine_amt']:<9.2f} {paid_status:<6}")
    
    print()


def pay_fines(card_id):
    """
    Pay all unpaid fines for a borrower.
    
    Requirements:
    - Cannot pay for books that are not yet returned
    - Cannot pay partial fines - must clear all fines
    - Updates all unpaid fines to paid = TRUE
    
    Args:
        card_id (str): Borrower card ID
    
    Returns:
        tuple: (success: bool, message: str, total_paid: Decimal or None)
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
            return False, f"Error: Borrower with card ID '{card_id}' not found.", None
        
        # Get all unpaid fines for this borrower
        query = """
        SELECT 
            f.Loan_id,
            f.Fine_amt,
            bl.Date_in
        FROM FINES f
        JOIN BOOK_LOANS bl ON f.Loan_id = bl.Loan_id
        WHERE bl.Card_id = ? AND f.Paid = 0
        """
        
        cur.execute(query, (card_id,))
        unpaid_fines = cur.fetchall()
        
        if not unpaid_fines:
            conn.close()
            return False, f"No unpaid fines found for borrower {card_id}.", None
        
        # Check if any fines are for books not yet returned
        unreturned_loans = [f for f in unpaid_fines if f['Date_in'] is None]
        if unreturned_loans:
            loan_ids = [str(f['Loan_id']) for f in unreturned_loans]
            conn.close()
            return False, f"Error: Cannot pay fines for books that are not yet returned. Loan IDs: {', '.join(loan_ids)}", None
        
        # Calculate total amount
        total_amount = Decimal('0.00')
        loan_ids_to_pay = []
        for fine in unpaid_fines:
            total_amount += Decimal(str(fine['Fine_amt']))
            loan_ids_to_pay.append(fine['Loan_id'])
        
        # Update all unpaid fines to paid
        placeholders = ','.join(['?'] * len(loan_ids_to_pay))
        cur.execute(f"""
            UPDATE FINES
            SET Paid = 1
            WHERE Loan_id IN ({placeholders}) AND Paid = 0
        """, loan_ids_to_pay)
        
        conn.commit()
        conn.close()
        
        return True, f"Successfully paid all fines for borrower {card_id}. Total amount: ${total_amount:.2f}", total_amount
    
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error: {str(e)}", None


def get_unpaid_fines(card_id):
    """
    Get all unpaid fines for a specific borrower.
    
    Args:
        card_id (str): Borrower card ID
    
    Returns:
        list: List of dictionaries with fine information
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = """
    SELECT 
        f.Loan_id,
        f.Fine_amt,
        bl.Isbn,
        b.Title,
        bl.Due_date,
        bl.Date_in
    FROM FINES f
    JOIN BOOK_LOANS bl ON f.Loan_id = bl.Loan_id
    JOIN BOOK b ON bl.Isbn = b.Isbn
    WHERE bl.Card_id = ? AND f.Paid = 0
    ORDER BY bl.Due_date
    """
    
    cur.execute(query, (card_id,))
    results = cur.fetchall()
    
    fines_list = []
    for row in results:
        fines_list.append({
            'Loan_id': row['Loan_id'],
            'Fine_amt': Decimal(str(row['Fine_amt'])),
            'ISBN': row['Isbn'],
            'Title': row['Title'],
            'Due_date': row['Due_date'],
            'Date_in': row['Date_in']
        })
    
    conn.close()
    return fines_list


if __name__ == "__main__":
    # Test update_fines
    print("Updating fines...")
    update_fines()
    print("Fines updated.")
    
    # Display unpaid fines
    display_fines(include_paid=False)
    
    # Test has_unpaid_fines
    result = has_unpaid_fines("ID000001")
    print(f"Borrower ID000001 has unpaid fines: {result}")
