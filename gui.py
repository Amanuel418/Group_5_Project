import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import search
import loans
import borrowers
import fines
from config import DB_PATH
import sqlite3

class LoginDialog:
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Login")
        self.window.geometry("300x200")
        self.window.resizable(False, False)
        
        # Center the window
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_widgets()
        
        # Center on screen
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'+{x}+{y}')
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.wait_window()

        
    def create_widgets(self):
        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Username:").pack(anchor=tk.W, pady=(0, 5))
        self.username_entry = ttk.Entry(frame)
        self.username_entry.pack(fill=tk.X, pady=(0, 10))
        self.username_entry.focus_set()
        
        ttk.Label(frame, text="Password:").pack(anchor=tk.W, pady=(0, 5))
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.pack(fill=tk.X, pady=(0, 20))
        
        self.password_entry.bind('<Return>', lambda e: self.login())
        
        ttk.Button(frame, text="Login", command=self.login).pack(fill=tk.X)
        
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Warning", "Please enter username and password.")
            return
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT role FROM USERS WHERE username = ? AND password = ?", (username, password))
        user = cur.fetchone()
        conn.close()
        
        if user:
            self.result = user['role']
            self.window.destroy()
        else:
            messagebox.showerror("Error", "Invalid username or password.")
            
    def on_close(self):
        self.window.destroy()

class LibraryManagementGUI:
    def __init__(self, root, user_role):
        self.root = root
        self.user_role = user_role
        self.root.title(f"Library Management System - Logged in as: {user_role.upper()}")
        self.root.geometry("1000x700")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_search_tab()
        self.create_checkout_tab()
        self.create_checkin_tab()
        self.create_borrower_tab()
        self.create_fines_tab()

        #Create status bar for copies
        self.status_bar = ttk.Label(root, text="", relief = tk.SUNKEN, anchor = tk.W)
        self.status_bar.pack(side = tk.BOTTOM, fill = tk.X, padx=10, pady=(0,10))
        
        # Update fines on startup
        try:
            fines.update_fines()
        except:
            pass
    
    def create_search_tab(self):
        """Create book search tab"""
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Book Search")
        
        # Search input
        input_frame = ttk.Frame(search_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="Search (ISBN, Title, or Author):", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(input_frame, width=40, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', lambda e: self.perform_search())
        
        ttk.Button(input_frame, text="Search", command=self.perform_search).pack(side=tk.LEFT, padx=5)
        
        # Results display
        results_frame = ttk.Frame(search_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview for results
        columns = ("ISBN", "Title", "Authors", "Status", "Borrower ID")
        self.search_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.search_tree.heading(col, text=col)
            self.search_tree.column(col, width=200)
        
        self.search_tree.column("ISBN", width=120)
        self.search_tree.column("Title", width=250)
        self.search_tree.column("Authors", width=250)
        self.search_tree.column("Status", width=80)
        self.search_tree.column("Borrower ID", width=100)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=scrollbar.set)
        
        self.search_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.search_tree.bind('<Double-1>', self.copy_selected_isbn)

    def copy_selected_isbn(self,event):
        """Copies ISBN of selected row"""
        selected_items = self.search_tree.selection()

        if not selected_items:
            return
        
        item_id = selected_items[0]
        values = self.search_tree.item(item_id, 'values')

        #Copies value from row
        if values and len(values) > 0:
            isbn = values[0]

            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(isbn)
                self.show_status_message(f"ISBN '{isbn}' copied to clipboard.")

            except Exception as e:
                messagebox.showerror("Clipboard Error", f"Failed to copy ISBN: {e}")

    def show_status_message(self, message, duration_ms = 3000):
        """Dipslays a mesage in the status bar for a set duration"""
        self.status_bar.config(text=message)

        #Cancel any previous operation
        if hasattr(self, '_clear_status_job'):
            self.root.after_cancel(self._clear_status_job)

        self._clear_status_job = self.root.after(duration_ms, lambda: self.status_bar.config(text=""))

    def perform_search(self):
        """Perform book search"""
        search_term = self.search_entry.get().strip()
        if not search_term:
            messagebox.showwarning("Warning", "Please enter a search term.")
            return
        
        # Clear previous results
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        try:
            results = search.search(search_term)
            if not results:
                messagebox.showinfo("No Results", f"No books found matching '{search_term}'.")
                return
            
            for result in results:
                self.search_tree.insert("", tk.END, values=(
                    result['ISBN'],
                    result['Title'],
                    result['Authors'],
                    result['Status'],
                    result['Borrower_id']
                ))
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Search error: {error_details}")  # Print to console for debugging
            messagebox.showerror("Error", f"Search failed: {str(e)}\n\nPlease ensure the database file exists.")
    
    def create_checkout_tab(self):
        """Create book checkout tab"""
        checkout_frame = ttk.Frame(self.notebook)
        self.notebook.add(checkout_frame, text="Checkout Book")
        
        # Input fields
        form_frame = ttk.LabelFrame(checkout_frame, text="Checkout Information", padding=20)
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(form_frame, text="ISBN:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.checkout_isbn = ttk.Entry(form_frame, width=30, font=("Arial", 10))
        self.checkout_isbn.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(form_frame, text="Borrower Card ID:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.checkout_card_id = ttk.Entry(form_frame, width=30, font=("Arial", 10))
        self.checkout_card_id.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Button(form_frame, text="Checkout Book", command=self.perform_checkout).grid(row=3, column=0, columnspan=2, pady=10)
        
        # Super-User Override
        self.override_var = tk.BooleanVar()
        self.override_check = ttk.Checkbutton(form_frame, text="Super-User Override (Ignore Restrictions)", variable=self.override_var)
        self.override_check.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Hide override for non-librarians
        if self.user_role != 'librarian':
            self.override_check.grid_remove()
        
        # Status display
        status_frame = ttk.LabelFrame(checkout_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.checkout_status = scrolledtext.ScrolledText(status_frame, height=10, font=("Arial", 9))
        self.checkout_status.pack(fill=tk.BOTH, expand=True)
    
    def perform_checkout(self):
        """Perform book checkout"""
        isbn = self.checkout_isbn.get().strip()
        card_id = self.checkout_card_id.get().strip()
        
        if not isbn or not card_id:
            messagebox.showwarning("Warning", "Please enter both ISBN and Borrower Card ID.")
            return
        
        try:
            override = self.override_var.get()
            success, message = loans.checkout(isbn, card_id, override)
            self.checkout_status.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            self.checkout_status.see(tk.END)
            
            if success:
                messagebox.showinfo("Success", message)
                self.checkout_isbn.delete(0, tk.END)
                self.checkout_card_id.delete(0, tk.END)
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            error_msg = f"Checkout failed: {str(e)}"
            self.checkout_status.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n")
            messagebox.showerror("Error", error_msg)
    
    def create_checkin_tab(self):
        """Create book check-in tab"""
        checkin_frame = ttk.Frame(self.notebook)
        self.notebook.add(checkin_frame, text="Check-in Book")
        
        # Search for loans
        search_frame = ttk.LabelFrame(checkin_frame, text="Find Loans", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(search_frame, text="Search (ISBN, Card ID, or Borrower Name):", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.checkin_search_entry = ttk.Entry(search_frame, width=30, font=("Arial", 10))
        self.checkin_search_entry.pack(side=tk.LEFT, padx=5)
        self.checkin_search_entry.bind('<Return>', lambda e: self.search_loans())
        ttk.Button(search_frame, text="Search", command=self.search_loans).pack(side=tk.LEFT, padx=5)
        
        # Results display
        results_frame = ttk.Frame(checkin_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Loan ID", "ISBN", "Title", "Card ID", "Borrower", "Date Out", "Due Date")
        self.checkin_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.checkin_tree.heading(col, text=col)
        
        self.checkin_tree.column("Loan ID", width=80)
        self.checkin_tree.column("ISBN", width=150)
        self.checkin_tree.column("Title", width=250)
        self.checkin_tree.column("Card ID", width=100)
        self.checkin_tree.column("Borrower", width=150)
        self.checkin_tree.column("Date Out", width=100)
        self.checkin_tree.column("Due Date", width=100)
        
        # Selection
        self.checkin_tree.config(selectmode=tk.EXTENDED)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.checkin_tree.yview)
        self.checkin_tree.configure(yscrollcommand=scrollbar.set)
        
        self.checkin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Check-in button
        button_frame = ttk.Frame(checkin_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Check-in Selected Books (1-3)", command=self.perform_checkin).pack(side=tk.LEFT, padx=5)
        
        # Status display
        status_frame = ttk.LabelFrame(checkin_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.checkin_status = scrolledtext.ScrolledText(status_frame, height=5, font=("Arial", 9))
        self.checkin_status.pack(fill=tk.BOTH, expand=True)
    
    def search_loans(self):
        """Search for loans to check in"""
        search_term = self.checkin_search_entry.get().strip()
        if not search_term:
            messagebox.showwarning("Warning", "Please enter a search term.")
            return
        
        # Clear previous results
        for item in self.checkin_tree.get_children():
            self.checkin_tree.delete(item)
        
        try:
            loan_results = loans.find_loans_by_search(search_term)
            if not loan_results:
                messagebox.showinfo("No Results", f"No active loans found matching '{search_term}'.")
                return
            
            for loan in loan_results:
                self.checkin_tree.insert("", tk.END, values=(
                    loan['Loan_id'],
                    loan['ISBN'],
                    loan['Title'],
                    loan['Card_id'],
                    loan['Borrower_name'],
                    loan['Date_out'],
                    loan['Due_date']
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {str(e)}")
    
    def perform_checkin(self):
        """Perform book check-in"""
        selected_items = self.checkin_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select at least one loan to check in.")
            return
        
        if len(selected_items) > 3:
            messagebox.showwarning("Warning", "You can only check in 1-3 books at a time.")
            return
        
        loan_ids = []
        for item in selected_items:
            values = self.checkin_tree.item(item, 'values')
            loan_ids.append(int(values[0]))
        
        try:
            success, message = loans.checkin(loan_ids)
            self.checkin_status.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            self.checkin_status.see(tk.END)
            
            if success:
                messagebox.showinfo("Success", message)
                # Refresh the search
                self.search_loans()
                # Update fines after check-in
                fines.update_fines()
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            error_msg = f"Check-in failed: {str(e)}"
            self.checkin_status.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n")
            messagebox.showerror("Error", error_msg)
    
    def create_borrower_tab(self):
        """Create borrower management tab"""
        borrower_frame = ttk.Frame(self.notebook)
        self.notebook.add(borrower_frame, text="Borrower Management")
        
        # Form
        form_frame = ttk.LabelFrame(borrower_frame, text="Create New Borrower", padding=20)
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(form_frame, text="Name:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.borrower_name = ttk.Entry(form_frame, width=40, font=("Arial", 10))
        self.borrower_name.grid(row=0, column=1, pady=5, padx=10, sticky=tk.W+tk.E)
        
        ttk.Label(form_frame, text="Address:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.borrower_address = ttk.Entry(form_frame, width=40, font=("Arial", 10))
        self.borrower_address.grid(row=1, column=1, pady=5, padx=10, sticky=tk.W+tk.E)
        
        ttk.Label(form_frame, text="Phone:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.borrower_phone = ttk.Entry(form_frame, width=40, font=("Arial", 10))
        self.borrower_phone.grid(row=2, column=1, pady=5, padx=10, sticky=tk.W+tk.E)
        
        ttk.Label(form_frame, text="SSN:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.borrower_ssn = ttk.Entry(form_frame, width=40, font=("Arial", 10))
        self.borrower_ssn.grid(row=3, column=1, pady=5, padx=10, sticky=tk.W+tk.E)
        form_frame.columnconfigure(1, weight=1)
        
        ttk.Button(form_frame, text="Create Borrower", command=self.create_borrower).grid(row=4, column=0, columnspan=2, pady=20)
        
        # Status display
        status_frame = ttk.LabelFrame(borrower_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.borrower_status = scrolledtext.ScrolledText(status_frame, height=10, font=("Arial", 9))
        self.borrower_status.pack(fill=tk.BOTH, expand=True)
    
    def create_borrower(self):
        """Create a new borrower"""
        bname = self.borrower_name.get().strip()
        address = self.borrower_address.get().strip()
        phone = self.borrower_phone.get().strip()
        ssn = self.borrower_ssn.get().strip()
        
        if not all([bname, address, phone, ssn]):
            messagebox.showwarning("Warning", "All fields are required.")
            return
        
        try:
            success, message, card_id = borrowers.create_borrower(bname, address, phone, ssn)
            self.borrower_status.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            self.borrower_status.see(tk.END)
            
            if success:
                messagebox.showinfo("Success", f"{message}\nCard ID: {card_id}")
                # Clear form
                self.borrower_name.delete(0, tk.END)
                self.borrower_address.delete(0, tk.END)
                self.borrower_phone.delete(0, tk.END)
                self.borrower_ssn.delete(0, tk.END)
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            error_msg = f"Failed to create borrower: {str(e)}"
            self.borrower_status.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n")
            messagebox.showerror("Error", error_msg)
    
    def create_fines_tab(self):
        """Create fines management tab"""
        fines_frame = ttk.Frame(self.notebook)
        self.notebook.add(fines_frame, text="Fines Management")
        
        # Control buttons
        control_frame = ttk.Frame(fines_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="Update Fines", command=self.update_fines).pack(side=tk.LEFT, padx=5)
        
        # Search filter
        ttk.Label(control_frame, text="Search (Card ID/Name):", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.fines_search_entry = ttk.Entry(control_frame, width=20, font=("Arial", 10))
        self.fines_search_entry.pack(side=tk.LEFT, padx=5)
        self.fines_search_entry.bind('<Return>', lambda e: self.refresh_fines_display())
        ttk.Button(control_frame, text="Search", command=self.refresh_fines_display).pack(side=tk.LEFT, padx=5)
        
        # Filter option
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(side=tk.RIGHT, padx=5)
        ttk.Label(filter_frame, text="Show:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.fines_filter = tk.StringVar(value="unpaid")
        ttk.Radiobutton(filter_frame, text="Unpaid Only", variable=self.fines_filter, value="unpaid", 
                       command=self.refresh_fines_display).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="All Fines", variable=self.fines_filter, value="all",
                       command=self.refresh_fines_display).pack(side=tk.LEFT, padx=5)
        
        # Fines display
        display_frame = ttk.Frame(fines_frame)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview for fines
        columns = ("Card ID", "Borrower", "Total Fine")
        self.fines_tree = ttk.Treeview(display_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.fines_tree.heading(col, text=col)
        
        self.fines_tree.column("Card ID", width=120)
        self.fines_tree.column("Borrower", width=200)
        self.fines_tree.column("Total Fine", width=150)
        
        scrollbar = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.fines_tree.yview)
        self.fines_tree.configure(yscrollcommand=scrollbar.set)
        
        self.fines_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to show details
        self.fines_tree.bind('<Double-1>', self.show_fine_details)
        
        # Payment section
        payment_frame = ttk.LabelFrame(fines_frame, text="Pay Fines", padding=10)
        payment_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(payment_frame, text="Borrower Card ID:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.payment_card_id = ttk.Entry(payment_frame, width=20, font=("Arial", 10))
        self.payment_card_id.pack(side=tk.LEFT, padx=5)
        ttk.Button(payment_frame, text="Pay All Fines", command=self.pay_fines).pack(side=tk.LEFT, padx=10)
        
        # Status display
        status_frame = ttk.LabelFrame(fines_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fines_status = scrolledtext.ScrolledText(status_frame, height=5, font=("Arial", 9))
        self.fines_status.pack(fill=tk.BOTH, expand=True)
        
        # Initial display
        self.refresh_fines_display()
    
    def update_fines(self):
        """Update fines in the database"""
        try:
            fines.update_fines()
            messagebox.showinfo("Success", "Fines updated successfully.")
            self.refresh_fines_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update fines: {str(e)}")
    
    def refresh_fines_display(self):
        """Refresh the fines display"""
        # Clear previous results
        for item in self.fines_tree.get_children():
            self.fines_tree.delete(item)
        
        try:
            include_paid = (self.fines_filter.get() == "all")
            search_term = self.fines_search_entry.get().strip().lower()
            
            borrowers_data = fines.get_fines_by_borrower(include_paid)
            
            if not borrowers_data:
                return
            
            for card_id, borrower_data in borrowers_data.items():
                # Filter by search term
                if search_term:
                    if (search_term not in card_id.lower() and 
                        search_term not in borrower_data['Bname'].lower()):
                        continue
                
                total_fine = f"${borrower_data['total_fine']:.2f}"
                self.fines_tree.insert("", tk.END, values=(
                    borrower_data['Card_id'],
                    borrower_data['Bname'],
                    total_fine
                ), tags=(card_id,))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh fines display: {str(e)}")
    
    def show_fine_details(self, event):
        """Show detailed fine information for selected borrower"""
        selected_item = self.fines_tree.selection()
        if not selected_item:
            return
        
        item = self.fines_tree.item(selected_item[0])
        card_id = item['tags'][0] if item['tags'] else item['values'][0]
        
        # Create detail window
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Fine Details - {card_id}")
        detail_window.geometry("800x400")
        
        # Get borrower info
        borrower_info = borrowers.get_borrower(card_id)
        if borrower_info:
            info_text = f"Borrower: {borrower_info['Bname']}\nCard ID: {card_id}\n\n"
        else:
            info_text = f"Card ID: {card_id}\n\n"
        
        # Get fines
        include_paid = (self.fines_filter.get() == "all")
        borrowers_data = fines.get_fines_by_borrower(include_paid)
        
        if card_id in borrowers_data:
            borrower_data = borrowers_data[card_id]
            info_text += f"Total Fine: ${borrower_data['total_fine']:.2f}\n\n"
            info_text += "Individual Fines:\n"
            info_text += "-" * 80 + "\n"
            
            for fine in borrower_data['fines']:
                paid_status = "Paid" if fine['Paid'] == 1 else "Unpaid"
                date_in = fine['Date_in'] if fine['Date_in'] else "Still Out"
                info_text += f"Loan ID: {fine['Loan_id']} | ISBN: {fine['ISBN']}\n"
                info_text += f"Title: {fine['Title']}\n"
                info_text += f"Due Date: {fine['Due_date']} | Returned: {date_in}\n"
                info_text += f"Fine Amount: ${fine['Fine_amt']:.2f} | Status: {paid_status}\n"
                info_text += "-" * 80 + "\n"
        else:
            info_text += "No fines found."
        
        text_widget = scrolledtext.ScrolledText(detail_window, font=("Arial", 9))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, info_text)
        text_widget.config(state=tk.DISABLED)
    
    def pay_fines(self):
        """Pay fines for a borrower"""
        card_id = self.payment_card_id.get().strip()
        if not card_id:
            messagebox.showwarning("Warning", "Please enter a Borrower Card ID.")
            return
        
        # Confirm payment
        result = messagebox.askyesno("Confirm Payment", 
                                     f"Pay all unpaid fines for borrower {card_id}?\n\n"
                                     "Note: You cannot pay partial fines. This will clear all unpaid fines.")
        if not result:
            return
        
        try:
            success, message, total_paid = fines.pay_fines(card_id)
            self.fines_status.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            self.fines_status.see(tk.END)
            
            if success:
                messagebox.showinfo("Success", message)
                self.payment_card_id.delete(0, tk.END)
                self.refresh_fines_display()
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            error_msg = f"Payment failed: {str(e)}"
            self.fines_status.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}\n")
            messagebox.showerror("Error", error_msg)


def main():
    root = tk.Tk()
    #root.withdraw() # Hide the main window initially
    
    # Show login dialog
    login = LoginDialog(root)
    
    if login.result:
        root.deiconify() # Show main window if login successful
        app = LibraryManagementGUI(root, login.result)
        root.mainloop()
    else:
        root.destroy()


if __name__ == "__main__":
    main()

