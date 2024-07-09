from flask import Flask,flash, render_template, request, redirect, url_for, session
import mysql.connector
import re
from datetime import datetime, timedelta
import pandas as pd
import secrets
import string

def generate_secret_key(length=24):
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

app = Flask(__name__)
app.secret_key = generate_secret_key()

# MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="library_management"
)

# Function to calculate due date excluding weekends
def calculate_due_date(start_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = start_date + pd.offsets.CustomBusinessDay(n=30)
    return end_date.strftime('%Y-%m-%d')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Validate password format
        if not re.match(r'^[A-Za-z0-9@#$%^&+=]{4,8}$', password):
            return "Invalid password format. It should be 4-8 characters."
        
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            session['username'] = username
            return redirect(url_for('book_management'))
        else:
            return "Login failed. Invalid username or password."
    
    return render_template('login.html')

@app.route('/book_management', methods=['GET', 'POST'])
def book_management():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    cursor.close()

    if request.method == 'POST':
        selected_books = request.form.getlist('book_id')
        
        for book_id in selected_books:
            # Check if book already in cart
            cursor = db.cursor()
            cursor.execute("SELECT * FROM cart WHERE username=%s AND book_id=%s", (session['username'], book_id))
            existing_book = cursor.fetchone()
            if existing_book:
                continue
                
            
            # Calculate due date
            start_date = datetime.now().strftime('%Y-%m-%d')
            due_date = calculate_due_date(start_date)
            
            # Add book to cart
            cursor.execute("INSERT INTO cart (username, book_id, start_date, due_date) VALUES (%s, %s, %s, %s)",
                           (session['username'], book_id, start_date, due_date))
            db.commit()
            cursor.close()
            
        return redirect(url_for('view_cart'))

    return render_template('book_management.html', books=books)

# Route to view cart contents
@app.route('/cart')
def view_cart():
    username = session.get('username')  # Assuming you store username in session after login

    cursor = db.cursor(dictionary=True)
    try:
        # Fetch cart items for the user
        cursor.execute("SELECT b.title, b.category, c.start_date, c.due_date FROM cart c INNER JOIN books b ON c.book_id = b.id WHERE c.username = %s", (username,))
        cart_items = cursor.fetchall()

        return render_template('cart.html', cart_items=cart_items)

    except Exception as e:
        print(f"Error fetching cart items: {e}")

    finally:
        cursor.close()

    return "Error fetching cart items"

if __name__ == '__main__':
    app.run(debug=True)
