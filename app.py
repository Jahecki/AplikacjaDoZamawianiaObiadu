import sqlite3
from datetime import datetime
import csv

conn = sqlite3.connect('orders.db')
c = conn.cursor()


c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        preferred_restaurant TEXT NOT NULL,
        alternate_restaurant TEXT NOT NULL,
        menu_item INTEGER NOT NULL,
        menu_item_price REAL NOT NULL,
        status TEXT DEFAULT 'new',
        group_order_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_order_id) REFERENCES group_orders(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS group_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant TEXT NOT NULL,
        order_date DATE DEFAULT CURRENT_DATE,
        status TEXT DEFAULT 'new'
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
    )
''')

conn.commit()


def initialize_database():
    restaurants_data = [
        ('Restauracja A',),
        ('Restauracja B',),
        ('Restauracja C',)
    ]
    c.executemany('INSERT INTO restaurants (name) VALUES (?)', restaurants_data)
    conn.commit()

    menu_items_data = [
        (1, 'Zurek', 10.99),
        (1, 'Schabowy', 12.50),
        (2, 'Rosol', 15.75),
        (2, 'Mielony', 18.00),
        (3, 'Pomidorowa', 9.99),
        (3, 'Bigos', 11.25)
    ]
    c.executemany('INSERT INTO menu_items (restaurant_id, name, price) VALUES (?, ?, ?)', menu_items_data)
    conn.commit()


def load_orders(file_path):
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            user_name, preferred_restaurant_name, alternate_restaurant_name, menu_item_name = row


            c.execute('SELECT id FROM users WHERE name = ?', (user_name,))
            user = c.fetchone()
            if not user:
                c.execute('INSERT INTO users (name) VALUES (?)', (user_name,))
                conn.commit()
                user_id = c.lastrowid
            else:
                user_id = user[0]


            c.execute('SELECT id FROM restaurants WHERE name = ?', (preferred_restaurant_name,))
            preferred_restaurant = c.fetchone()
            if not preferred_restaurant:
                print(f"Blad:  '{preferred_restaurant_name}' nie znaleziono tej restauracji.")
                continue
            preferred_restaurant_id = preferred_restaurant[0]


            c.execute('SELECT id, price FROM menu_items WHERE restaurant_id = ? AND name = ?', (preferred_restaurant_id, menu_item_name))
            menu_item = c.fetchone()
            if not menu_item:
                print(f"Blad:  '{menu_item_name}' nie znaleziono dania w restuaracji: '{preferred_restaurant_name}'.")
                continue
            menu_item_id, menu_item_price = menu_item


            c.execute('''
                INSERT INTO orders (user_id, preferred_restaurant, alternate_restaurant, menu_item, menu_item_price) 
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, preferred_restaurant_name, alternate_restaurant_name, menu_item_id, menu_item_price))
            conn.commit()

    print("Zamowienia przyjete z powodzeniem.")


def group_orders():
    today = datetime.utcnow().date()
    c.execute('SELECT DISTINCT preferred_restaurant FROM orders WHERE status = "new"')
    restaurants = c.fetchall()

    for restaurant in restaurants:
        restaurant = restaurant[0]
        c.execute('SELECT * FROM orders WHERE preferred_restaurant = ? AND status = "new"', (restaurant,))
        orders = c.fetchall()

        if orders:
            c.execute('INSERT INTO group_orders (restaurant, order_date) VALUES (?, ?)', (restaurant, today))
            conn.commit()
            group_order_id = c.lastrowid

            for order in orders:
                c.execute('UPDATE orders SET status = "grouped", group_order_id = ? WHERE id = ?', (group_order_id, order[0]))
                conn.commit()

    print("Zamowienia pogrupowane pomyslnie.")


def update_status(group_order_id, new_status):
    c.execute('UPDATE group_orders SET status = ? WHERE id = ?', (new_status, group_order_id))
    conn.commit()

    c.execute('UPDATE orders SET status = ? WHERE group_order_id = ?', (new_status, group_order_id))
    conn.commit()

    print("Zaktualizowano pomyslnie.")
def display_recent_group_orders():
    c.execute('SELECT id, restaurant, order_date, status FROM group_orders ORDER BY order_date DESC LIMIT 10')
    group_orders = c.fetchall()
    if group_orders:
        print("Ostatnie zamowienia grupowe:")
        for order in group_orders:
            group_order_id = order[0]
            c.execute('SELECT SUM(menu_item_price), COUNT(*) FROM orders WHERE group_order_id = ?', (group_order_id,))
            total_amount, total_items = c.fetchone()
            print(
                f"ID: {group_order_id}, {order[1]}, Data: {order[2]}, Status: {order[3]}, Cena: {total_amount:.2f}, Ilosc dan: {total_items}")
    else:
        print("Nie znaleziono pogrupowanych zamowien.")

    print("\nniepogrupowane zamowienia:")
    c.execute('''
            SELECT o.id, u.name, o.preferred_restaurant, o.alternate_restaurant, m.name, o.menu_item_price 
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN menu_items m ON o.menu_item = m.id
            WHERE o.status = "new"
            ORDER BY o.id
        ''')
    ungrouped_orders = c.fetchall()
    if ungrouped_orders:
        for order in ungrouped_orders:
            print(
                f"Order ID: {order[0]}, Uzytkownik: {order[1]}, preferowana {order[2]}, Alternatywna {order[3]}, pozycja: {order[4]}, cena: {order[5]:.2f}")
    else:
        print("Nie znaleziono niepogrupowanych zamowien.")


# Funkcja główna
def main():
    initialize_database()

    while True:
        print("1. Wprowadz zamowienie")
        print("2. pogrupuj zamowienia")
        print("3. zaktualizuj status")
        print("4. Wyjdz")
        print("5. Wyświetl ostatnie grupowe zamówienia")
        choice = input("Wybierz opcje: ")

        if choice == '1':
            file_path = input("Podaj sciezke do pliku z zamowieniami: ")
            load_orders(file_path)
        elif choice == '2':
            group_orders()
        elif choice == '3':
            group_order_id = int(input("Podaj identyfikator grupowego zamowienia: "))
            new_status = input("Podaj nowy status: ")
            update_status(group_order_id, new_status)
        elif choice == '4':
            break
        elif choice == '5':
            display_recent_group_orders()
        else:
            print("Nieprawidlowy wybór. Sprobuj ponownie.")

if __name__ == '__main__':
    main()