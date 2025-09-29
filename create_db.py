import sqlite3

# Path to database file
db_path = 'cafe.db'

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Query for tests
user_id = 1  
cursor.execute("""
    SELECT o.id AS order_id, o.total_price, o.date, i.name AS item_name, oi.quantity, oi.price
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN menu_items i ON oi.menu_item_id = i.id
    WHERE o.user_id = ?
    ORDER BY o.date DESC
""", (user_id,))
results = cursor.fetchall()

# Print the results
for row in results:
    print(f"Order ID: {row[0]}, Total Price: {row[1]}, Date: {row[2]}")
    print(f"  Item: {row[3]}, Quantity: {row[4]}, Price: {row[5]}")

# Close the connection
conn.close()
