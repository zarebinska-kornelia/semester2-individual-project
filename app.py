from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from datetime import datetime
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = 'vfytgf2yreiure32yugfyi5urgej3t672454' 

@app.route('/')
def index():
    return render_template("index.html", title="Our Café", year=datetime.now().year)

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        flash("Please log in to view your orders.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('cafe.db')
    cursor = conn.cursor()

    # Fetch orders and their items
    cursor.execute("""
        SELECT o.id AS order_id, o.date, o.total_price, i.name, oi.quantity, oi.price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN menu_items i ON oi.menu_item_id = i.id
        WHERE o.user_id = ?
        ORDER BY o.date DESC
    """, (user_id,))
    results = cursor.fetchall()

    # Group orders with their items
    orders_dict = {}
    for row in results:
        order_id = row[0]
        if order_id not in orders_dict:
            orders_dict[order_id] = {
                'id': order_id,
                'date': row[1],
                'total_price': row[2],
                'order_items': []
            }
        orders_dict[order_id]['order_items'].append({
            'name': row[3],
            'quantity': row[4],
            'price': row[5]
        })

    conn.close()
    return render_template('orders.html', orders=list(orders_dict.values()))

@app.route('/menu')
def menu():
    conn = sqlite3.connect('cafe.db')  
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, image_url FROM menu_items")  
    menu_items = cursor.fetchall()
    conn.close()
    return render_template('menu.html', menu_items=menu_items)


@app.route('/add_to_basket', methods=['POST'])
def add_to_basket():
    data = request.json
    item_id = data.get('item_id')
    #fetch info about cofee from db
    conn = sqlite3.connect('cafe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM menu_items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    conn.close()

    if item:
        basket = session.setdefault('basket', [])
        basket.append({
            'id': item_id,
            'name': item[0],
            'price': item[1]
        })

        session['basket'] = basket

        return jsonify({
            'success': True,
            'message': f"{item[0]} added to the basket.",
            'item_name': item[0],
            'item_price': item[1]
        })
    else:
        return jsonify({'success': False, 'message': 'Item not found.'}), 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect('cafe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check does two passwords are the same
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match.")
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # put to DB
        conn = sqlite3.connect('cafe.db')
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            # Check to username not repeat
            return render_template('register.html', error="Username already exists.")
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully!", "info")
    return redirect(url_for('index'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'You need to log in to checkout.'}), 403

    basket = session.get('basket', [])
    if not basket:
        return jsonify({'success': False, 'message': 'Your basket is empty.'}), 400

    user_id = session['user_id']
    total_price = sum(item['price'] for item in basket)
    conn = sqlite3.connect('cafe.db')
    cursor = conn.cursor()

    try:
        # Insert the order into the orders table
        cursor.execute("""
            INSERT INTO orders (user_id, date, total_price, status)
            VALUES (?, ?, ?, ?)
        """, (user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), total_price, "Pending"))
        order_id = cursor.lastrowid

        # Insert each item in the basket into the order_items table
        for item in basket:
            cursor.execute("""
                INSERT INTO order_items (order_id, menu_item_id, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (order_id, item['id'], 1, item['price']))


        conn.commit()
        session.pop('basket', None)  # Clear the basket after successful checkout
        return jsonify({'success': True})
    except Exception as e:
        print("Error during checkout:", e)
        return jsonify({'success': False, 'message': 'An error occurred during checkout.'}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)

