from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import logging
import psycopg2
from psycopg2.extras import DictCursor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="inventory_db",
        user="postgres",
        password="postgres"
    )

# Login required decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Role required decorator
def role_required(roles):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.')
                return redirect(url_for('login'))
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=DictCursor)
            cur.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if not user:
                session.pop('user_id', None)
                flash('Your session has expired. Please log in again.')
                return redirect(url_for('login'))
            if user['role'] not in roles:
                flash('You do not have permission to access this page.')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

@app.route('/')
def index():
    if 'user_id' in session:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user['role'] == 'customer':
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=DictCursor)
            cur.execute('SELECT * FROM products WHERE is_featured = TRUE')
            featured_products = cur.fetchall()
            cur.execute('SELECT DISTINCT category FROM products')
            categories = cur.fetchall()
            cur.close()
            conn.close()
            return render_template('index.html', 
                                featured_products=featured_products,
                                categories=categories,
                                user=user)
        elif user['role'] == 'vendor':
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=DictCursor)
            cur.execute('SELECT * FROM products WHERE vendor_id = %s', (session['user_id'],))
            products = cur.fetchall()
            cur.close()
            conn.close()
            return render_template('index.html', products=products, user=user)
        else:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=DictCursor)
            cur.execute('SELECT * FROM products')
            products = cur.fetchall()
            cur.close()
            conn.close()
            return render_template('index.html', products=products, user=user)
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute('SELECT * FROM products WHERE is_featured = TRUE')
    featured_products = cur.fetchall()
    cur.execute('SELECT DISTINCT category FROM products')
    categories = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', 
                         featured_products=featured_products,
                         categories=categories,
                         user=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'customer')

        logger.debug(f"Attempting to register user: {username}")

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Check if username or email already exists
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        if cur.fetchone():
            logger.debug(f"Username {username} already exists")
            flash('Username already exists. Please choose another.')
            cur.close()
            conn.close()
            return redirect(url_for('register'))
            
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        if cur.fetchone():
            logger.debug(f"Email {email} already exists")
            flash('Email already exists. Please use another email.')
            cur.close()
            conn.close()
            return redirect(url_for('register'))

        try:
            # Create new user
            cur.execute('''
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (username, email, generate_password_hash(password), role))
            user_id = cur.fetchone()['id']
            conn.commit()
            logger.debug(f"Successfully registered user: {username}")

            flash('Registration successful! Please log in.')
            cur.close()
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during registration: {str(e)}")
            flash(f'Error during registration: {str(e)}')
            cur.close()
            conn.close()
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=DictCursor)
            cur.execute('''
                UPDATE users 
                SET last_login = %s 
                WHERE id = %s
            ''', (datetime.utcnow(), user['id']))
            conn.commit()
            cur.close()
            conn.close()
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'vendor':
                return redirect(url_for('vendor_dashboard'))
            elif user['role'] == 'customer':
                return redirect(url_for('customer_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/my_orders')
@login_required
@role_required(['customer'])
def my_orders():
    try:
        user_id = session.get('user_id')
        print(f"User ID from session: {user_id}")  # Debug log
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Get user info
        cur.execute('''
            SELECT id, username, email, role 
            FROM users 
            WHERE id = %s
        ''', (user_id,))
        user = cur.fetchone()
        
        # Get orders with their items
        cur.execute('''
            SELECT o.id, o.created_at, o.status, o.total_amount, o.shipping_address, o.payment_method,
                   oi.quantity, oi.price,
                   p.name as product_name, p.description as product_description
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE o.user_id = %s
            ORDER BY o.created_at DESC
        ''', (user_id,))
        order_rows = cur.fetchall()
        
        # Structure the orders data
        orders = {}
        for row in order_rows:
            order_id = row['id']
            if order_id not in orders:
                orders[order_id] = {
                    'id': order_id,
                    'created_at': row['created_at'],
                    'status': row['status'],
                    'total_amount': float(row['total_amount']) if row['total_amount'] else 0.0,
                    'shipping_address': row['shipping_address'],
                    'payment_method': row['payment_method'],
                    'order_items': []  # Changed from 'items' to 'order_items'
                }
            
            if row['product_name']:  # If there are items in the order
                orders[order_id]['order_items'].append({
                    'product_name': row['product_name'],
                    'product_description': row['product_description'],
                    'quantity': row['quantity'],
                    'price': float(row['price']) if row['price'] else 0.0
                })
        
        # Convert orders dict to list
        orders_list = list(orders.values())
        
        cur.close()
        conn.close()
        
        return render_template('customer/orders.html', orders=orders_list, user=user)
    except Exception as e:
        print(f"Error in my_orders route: {str(e)}")  # Debug log
        import traceback
        traceback.print_exc()  # Print full traceback
        flash('An error occurred while loading your orders.', 'error')
        return redirect(url_for('customer_dashboard'))

@app.route('/account_details')
@login_required
@role_required(['customer'])
def account_details():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute('''
            SELECT id, username, email, role, created_at, last_login
            FROM users 
            WHERE id = %s
        ''', (session['user_id'],))
        user = cur.fetchone()
        
        print(f"User found for account details: {user['username'] if user else None}")  # Debug log
        
        cur.close()
        conn.close()
        
        return render_template('customer/account.html', user=user)
    except Exception as e:
        print(f"Error in account_details route: {str(e)}")  # Debug log
        flash('An error occurred while loading your account details.', 'error')
        return redirect(url_for('customer_dashboard'))

@app.route('/admin/dashboard')
@login_required
@role_required(['admin'])
def admin_dashboard():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    # Get statistics
    cur.execute('SELECT COUNT(*) FROM users')
    total_users = cur.fetchone()['count']
    
    cur.execute('SELECT COUNT(*) FROM products')
    total_products = cur.fetchone()['count']
    
    cur.execute('SELECT COUNT(*) FROM orders')
    total_orders = cur.fetchone()['count']
    
    cur.execute('SELECT COALESCE(SUM(total_amount), 0) FROM orders')
    total_revenue = cur.fetchone()['coalesce']
    
    cur.close()
    conn.close()
    
    return render_template('admin/dashboard.html', 
                         user=user,
                         total_users=total_users,
                         total_products=total_products,
                         total_orders=total_orders,
                         total_revenue=total_revenue)

@app.route('/vendor/dashboard')
@login_required
def vendor_dashboard():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    if user['role'] != 'vendor':
        flash('Access denied. Vendor access required.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    
    # Get vendor's products
    cur.execute('SELECT * FROM products WHERE vendor_id = %s', (user['id'],))
    products = cur.fetchall()
    
    # Get pending orders with customer username
    cur.execute('''
        SELECT o.*, u.username as customer_username
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        JOIN users u ON o.user_id = u.id
        WHERE p.vendor_id = %s AND o.status = 'pending'
        GROUP BY o.id, u.username
    ''', (user['id'],))
    pending_orders = cur.fetchall()
    
    # Get recent orders with customer username
    cur.execute('''
        SELECT o.*, u.username as customer_username
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        JOIN users u ON o.user_id = u.id
        WHERE p.vendor_id = %s
        GROUP BY o.id, u.username
        ORDER BY o.created_at DESC
        LIMIT 5
    ''', (user['id'],))
    recent_orders = cur.fetchall()
    
    # Calculate total sales
    cur.execute('''
        SELECT COALESCE(SUM(oi.quantity * oi.price), 0)
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE p.vendor_id = %s
    ''', (user['id'],))
    total_sales = cur.fetchone()['coalesce']
    
    # Get low stock items
    cur.execute('''
        SELECT * FROM products 
        WHERE vendor_id = %s AND quantity <= 10
    ''', (user['id'],))
    low_stock_items = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('vendor/dashboard.html',
                         user=user,
                         products=products,
                         pending_orders=pending_orders,
                         recent_orders=recent_orders,
                         total_sales=total_sales,
                         low_stock_items=low_stock_items)

@app.route('/customer/dashboard')
@login_required
@role_required(['customer'])
def customer_dashboard():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    cur.execute('SELECT * FROM products WHERE is_featured = TRUE')
    featured_products = cur.fetchall()
    
    # Get distinct categories and clean them up
    cur.execute('SELECT DISTINCT category FROM products')
    categories_raw = cur.fetchall()
    categories = [cat['category'].strip("[]'") for cat in categories_raw]
    
    cur.close()
    conn.close()
    
    return render_template('customer/dashboard.html', 
                         user=user, 
                         featured_products=featured_products,
                         categories=categories)

@app.route('/manager/dashboard')
@login_required
@role_required(['manager'])
def manager_dashboard():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    # Get statistics
    cur.execute('SELECT COUNT(*) FROM users WHERE role = %s', ('customer',))
    total_customers = cur.fetchone()['count']
    
    cur.execute('SELECT COUNT(*) FROM users WHERE role = %s', ('vendor',))
    total_vendors = cur.fetchone()['count']
    
    cur.execute('SELECT COUNT(*) FROM orders')
    total_orders = cur.fetchone()['count']
    
    cur.execute('SELECT COALESCE(SUM(total_amount), 0) FROM orders')
    total_revenue = cur.fetchone()['coalesce']
    
    # Get recent orders
    cur.execute('''
        SELECT o.*, u.username as customer_username
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
        LIMIT 5
    ''')
    recent_orders = cur.fetchall()
    
    # Get low stock items
    cur.execute('''
        SELECT p.*, u.username as vendor_username
        FROM products p
        JOIN users u ON p.vendor_id = u.id
        WHERE p.quantity <= 10
    ''')
    low_stock_items = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('manager/dashboard.html',
                         user=user,
                         total_customers=total_customers,
                         total_vendors=total_vendors,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders,
                         low_stock_items=low_stock_items)

@app.route('/staff/dashboard')
@login_required
@role_required(['staff'])
def staff_dashboard():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    # Get pending orders
    cur.execute('''
        SELECT o.*, u.username as customer_username
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.status = 'pending'
        ORDER BY o.created_at DESC
    ''')
    pending_orders = cur.fetchall()
    
    # Get recent orders
    cur.execute('''
        SELECT o.*, u.username as customer_username
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
        LIMIT 5
    ''')
    recent_orders = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('staff/dashboard.html',
                         user=user,
                         pending_orders=pending_orders,
                         recent_orders=recent_orders)

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash('Please log in to view your cart.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Get or create cart
        cur.execute('''
            SELECT id FROM carts 
            WHERE user_id = %s
        ''', (session['user_id'],))
        cart = cur.fetchone()
        
        if not cart:
            cur.execute('''
                INSERT INTO carts (user_id) 
                VALUES (%s) 
                RETURNING id
            ''', (session['user_id'],))
            cart = cur.fetchone()
            conn.commit()
        
        # Get cart items with product details
        cur.execute('''
            SELECT 
                ci.id,
                ci.quantity,
                p.price,
                p.name as product_name,
                p.id as product_id
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            WHERE ci.cart_id = %s
        ''', (cart['id'],))
        cart_items = [dict(item) for item in cur.fetchall()]  # Convert to list of dictionaries
        
        # Calculate total
        total_amount = sum(float(item['price']) * item['quantity'] for item in cart_items)
        
        cart_data = {
            'id': cart['id'],
            'cart_items': cart_items,
            'total_amount': total_amount
        }
        
        print("Cart items:", cart_items)  # Debug print
        print("Cart data:", cart_data)    # Debug print
        
        return render_template('customer/cart.html', cart=cart_data)
        
    except Exception as e:
        print("Error in view_cart:", str(e))  # Debug print
        conn.rollback()
        flash('An error occurred while viewing your cart.', 'danger')
        return redirect(url_for('index'))
    
    finally:
        cur.close()
        conn.close()

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please log in to checkout.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Get user info
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        
        # Get cart and items
        cur.execute('''
            SELECT 
                ci.id,
                ci.quantity,
                p.price,
                p.name as product_name,
                p.id as product_id
            FROM carts c
            JOIN cart_items ci ON c.id = ci.cart_id
            JOIN products p ON ci.product_id = p.id
            WHERE c.user_id = %s
        ''', (session['user_id'],))
        cart_items = cur.fetchall()
        
        if not cart_items:
            flash('Your cart is empty!', 'warning')
            return redirect(url_for('view_cart'))
        
        # Calculate total
        total_amount = sum(float(item['price']) * item['quantity'] for item in cart_items)
        
        if request.method == 'POST':
            shipping_address = request.form.get('shipping_address')
            payment_method = request.form.get('payment_method')
            
            if not shipping_address or not payment_method:
                flash('Please provide shipping address and payment method.', 'warning')
                return render_template('customer/checkout.html',
                                    cart_items=cart_items,
                                    total_amount=total_amount,
                                    user=user)
            
            # Create order
            cur.execute('''
                INSERT INTO orders (user_id, total_amount, status, shipping_address, payment_method)
                VALUES (%s, %s, 'pending', %s, %s)
                RETURNING id
            ''', (session['user_id'], total_amount, shipping_address, payment_method))
            order_id = cur.fetchone()['id']
            
            # Add order items
            for item in cart_items:
                cur.execute('''
                    INSERT INTO order_items (order_id, product_id, quantity, price)
                    VALUES (%s, %s, %s, %s)
                ''', (order_id, item['product_id'], item['quantity'], item['price']))
                
                # Update product quantity
                cur.execute('''
                    UPDATE products
                    SET quantity = quantity - %s
                    WHERE id = %s
                ''', (item['quantity'], item['product_id']))
            
            # Clear cart
            cur.execute('''
                DELETE FROM cart_items
                WHERE cart_id IN (SELECT id FROM carts WHERE user_id = %s)
            ''', (session['user_id'],))
            
            conn.commit()
            flash('Order placed successfully!', 'success')
            return redirect(url_for('my_orders'))
        
        return render_template('customer/checkout.html',
                            cart_items=cart_items,
                            total_amount=total_amount,
                            user=user)
        
    except Exception as e:
        print("Error in checkout:", str(e))  # Debug print
        conn.rollback()
        flash('An error occurred while processing your order.', 'danger')
        return redirect(url_for('view_cart'))
    
    finally:
        cur.close()
        conn.close()

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please log in to add items to cart.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Get product details
        cur.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        product = cur.fetchone()
        
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('index'))
        
        # Check if quantity is available
        quantity = int(request.form.get('quantity', 1))
        if quantity > product['quantity']:
            flash('Not enough stock available.', 'warning')
            return redirect(url_for('index'))
        
        # Get or create cart
        cur.execute('''
            SELECT id FROM carts 
            WHERE user_id = %s
        ''', (session['user_id'],))
        cart = cur.fetchone()
        
        if not cart:
            cur.execute('''
                INSERT INTO carts (user_id) 
                VALUES (%s) 
                RETURNING id
            ''', (session['user_id'],))
            cart = cur.fetchone()
            conn.commit()
        
        # Check if item already in cart
        cur.execute('''
            SELECT id, quantity 
            FROM cart_items 
            WHERE cart_id = %s AND product_id = %s
        ''', (cart['id'], product_id))
        cart_item = cur.fetchone()
        
        if cart_item:
            # Update quantity
            new_quantity = cart_item['quantity'] + quantity
            cur.execute('''
                UPDATE cart_items 
                SET quantity = %s 
                WHERE id = %s
            ''', (new_quantity, cart_item['id']))
        else:
            # Add new item
            cur.execute('''
                INSERT INTO cart_items (cart_id, product_id, quantity) 
                VALUES (%s, %s, %s)
            ''', (cart['id'], product_id, quantity))
        
        conn.commit()
        flash('Item added to cart successfully.', 'success')
        return redirect(url_for('view_cart'))
        
    except Exception as e:
        print("Error in add_to_cart:", str(e))  # Debug print
        conn.rollback()
        flash('An error occurred while adding item to cart.', 'danger')
        return redirect(url_for('index'))
    
    finally:
        cur.close()
        conn.close()

@app.route('/update_cart/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    if 'user_id' not in session:
        flash('Please log in to update your cart.', 'danger')
        return redirect(url_for('login'))
    
    quantity = int(request.form.get('quantity', 0))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        if quantity > 0:
            # Update quantity
            cur.execute('''
                UPDATE cart_items 
                SET quantity = %s 
                WHERE id = %s AND cart_id IN (
                    SELECT id FROM carts WHERE user_id = %s
                )
            ''', (quantity, item_id, session['user_id']))
        else:
            # Remove item
            cur.execute('''
                DELETE FROM cart_items 
                WHERE id = %s AND cart_id IN (
                    SELECT id FROM carts WHERE user_id = %s
                )
            ''', (item_id, session['user_id']))
        
        conn.commit()
        flash('Cart updated successfully.', 'success')
        
    except Exception as e:
        print("Error in update_cart:", str(e))  # Debug print
        conn.rollback()
        flash('An error occurred while updating your cart.', 'danger')
    
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('view_cart'))

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if 'user_id' not in session:
        flash('Please log in to remove items from cart.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cur.execute('''
            DELETE FROM cart_items 
            WHERE id = %s AND cart_id IN (
                SELECT id FROM carts WHERE user_id = %s
            )
        ''', (item_id, session['user_id']))
        
        conn.commit()
        flash('Item removed from cart successfully.', 'success')
        
    except Exception as e:
        print("Error in remove_from_cart:", str(e))  # Debug print
        conn.rollback()
        flash('An error occurred while removing item from cart.', 'danger')
    
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('view_cart'))

@app.route('/category/<path:category>')
@login_required
@role_required(['customer'])
def category_products(category):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        
        # Clean up the category string and perform case-insensitive search
        clean_category = category.strip("[]'")
        print(f"Searching for category: {clean_category}")  # Debug log
        
        # Get products for the category (case-insensitive search)
        cur.execute('''
            SELECT * FROM products 
            WHERE LOWER(TRIM(category)) = LOWER(TRIM(%s))
        ''', (clean_category,))
        products = cur.fetchall()
        
        print(f"Found {len(products)} products for category: {clean_category}")  # Debug log
        
        # Get all categories for the navigation
        cur.execute('SELECT DISTINCT category FROM products')
        categories_raw = cur.fetchall()
        categories = [cat['category'].strip("[]'") for cat in categories_raw]
        
        cur.close()
        conn.close()
        
        return render_template('customer/category_products.html',
                             user=user,
                             category=clean_category,
                             products=products,
                             categories=categories)
    except Exception as e:
        print(f"Error in category_products route: {str(e)}")  # Debug log
        import traceback
        traceback.print_exc()  # Print full traceback
        flash('An error occurred while loading the category.', 'error')
        return redirect(url_for('customer_dashboard'))

@app.route('/vendor/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    if user['role'] != 'vendor':
        flash('Access denied. Vendor access required.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        quantity = int(request.form.get('quantity'))
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        
        try:
            cur.execute('''
                INSERT INTO products (name, description, price, quantity, category, subcategory, vendor_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (name, description, price, quantity, category, subcategory, user['id']))
            
            conn.commit()
            flash('Product added successfully!', 'success')
            cur.close()
            conn.close()
            return redirect(url_for('vendor_dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
            cur.close()
            conn.close()
            return redirect(url_for('add_product'))
    
    cur.close()
    conn.close()
    return render_template('vendor/add_product.html', user=user)

@app.route('/vendor/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    if user['role'] != 'vendor':
        flash('Access denied. Vendor access required.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    
    cur.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cur.fetchone()
    
    if not product or product['vendor_id'] != user['id']:
        flash('Access denied. You can only edit your own products.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('vendor_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        quantity = int(request.form.get('quantity'))
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        
        try:
            cur.execute('''
                UPDATE products 
                SET name = %s, description = %s, price = %s, quantity = %s, 
                    category = %s, subcategory = %s
                WHERE id = %s
            ''', (name, description, price, quantity, category, subcategory, product_id))
            
            conn.commit()
            flash('Product updated successfully!', 'success')
            cur.close()
            conn.close()
            return redirect(url_for('vendor_dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
            cur.close()
            conn.close()
            return redirect(url_for('edit_product', product_id=product_id))
    
    cur.close()
    conn.close()
    return render_template('vendor/edit_product.html', user=user, product=product)

@app.route('/vendor/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    if user['role'] != 'vendor':
        flash('Access denied. Vendor access required.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    
    cur.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cur.fetchone()
    
    if not product or product['vendor_id'] != user['id']:
        flash('Access denied. You can only delete your own products.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('vendor_dashboard'))
    
    try:
        cur.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('vendor_dashboard'))

@app.route('/vendor/orders')
@login_required
def vendor_orders():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    if user['role'] != 'vendor':
        flash('Access denied. Vendor access required.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    
    cur.execute('''
        SELECT DISTINCT o.*, u.username as customer_username
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        JOIN users u ON o.user_id = u.id
        WHERE p.vendor_id = %s
        ORDER BY o.created_at DESC
    ''', (user['id'],))
    orders = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('vendor/orders.html', user=user, orders=orders)

@app.route('/vendor/sales')
@login_required
def vendor_sales():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    if user['role'] != 'vendor':
        flash('Access denied. Vendor access required.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    
    # Get sales statistics
    cur.execute('''
        SELECT COALESCE(SUM(oi.quantity * oi.price), 0)
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE p.vendor_id = %s
    ''', (user['id'],))
    total_sales = cur.fetchone()['coalesce']
    
    # Get sales by category
    cur.execute('''
        SELECT p.category, COALESCE(SUM(oi.quantity * oi.price), 0) as total
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE p.vendor_id = %s
        GROUP BY p.category
    ''', (user['id'],))
    sales_by_category = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('vendor/sales.html',
                         user=user,
                         total_sales=total_sales,
                         sales_by_category=sales_by_category)

@app.route('/vendor/inventory')
@login_required
def vendor_inventory():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    if user['role'] != 'vendor':
        flash('Access denied. Vendor access required.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    
    cur.execute('SELECT * FROM products WHERE vendor_id = %s', (user['id'],))
    products = cur.fetchall()
    
    cur.execute('''
        SELECT * FROM products 
        WHERE vendor_id = %s AND quantity <= 10
    ''', (user['id'],))
    low_stock_items = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('vendor/inventory.html',
                         user=user,
                         products=products,
                         low_stock_items=low_stock_items)

@app.route('/search')
@login_required
@role_required(['customer'])
def search_products():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('customer_dashboard'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    # Search in product name, description, category, and subcategory
    cur.execute('''
        SELECT * FROM products 
        WHERE LOWER(name) LIKE LOWER(%s)
           OR LOWER(description) LIKE LOWER(%s)
           OR LOWER(category) LIKE LOWER(%s)
           OR LOWER(subcategory) LIKE LOWER(%s)
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
    products = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('customer/search_results.html',
                         user=user,
                         products=products,
                         query=query)

@app.route('/vendor/order/<int:order_id>')
@login_required
@role_required(['vendor'])
def view_order(order_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    cur.execute('SELECT * FROM orders WHERE id = %s', (order_id,))
    order = cur.fetchone()
    
    # Verify that the order contains products from this vendor
    cur.execute('''
        SELECT oi.*, p.name as product_name
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s AND p.vendor_id = %s
    ''', (order_id, user['id']))
    order_items = cur.fetchall()
    
    if not order_items:
        flash('Order not found or you do not have permission to view this order.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('vendor_dashboard'))
    
    cur.close()
    conn.close()
    
    return render_template('vendor/order_details.html',
                         user=user,
                         order=order,
                         order_items=order_items)

@app.route('/vendor/order/<int:order_id>/update', methods=['POST'])
@login_required
@role_required(['vendor'])
def update_order_status(order_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    cur.execute('SELECT * FROM orders WHERE id = %s', (order_id,))
    order = cur.fetchone()
    
    # Verify that the order contains products from this vendor
    cur.execute('''
        SELECT oi.*
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s AND p.vendor_id = %s
    ''', (order_id, user['id']))
    order_items = cur.fetchall()
    
    if not order_items:
        flash('Order not found or you do not have permission to update this order.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('vendor_dashboard'))
    
    try:
        cur.execute('''
            UPDATE orders 
            SET status = 'completed'
            WHERE id = %s
        ''', (order_id,))
        conn.commit()
        flash('Order status updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error updating order status.', 'danger')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('view_order', order_id=order_id))

@app.route('/vendor/order/<int:order_id>/process', methods=['POST'])
@login_required
@role_required(['vendor'])
def process_order(order_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    
    cur.execute('SELECT * FROM orders WHERE id = %s', (order_id,))
    order = cur.fetchone()
    
    # Verify that the order contains products from this vendor
    cur.execute('''
        SELECT oi.*
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s AND p.vendor_id = %s
    ''', (order_id, user['id']))
    order_items = cur.fetchall()
    
    if not order_items:
        flash('Order not found or you do not have permission to process this order.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('vendor_orders'))
    
    try:
        cur.execute('''
            UPDATE orders 
            SET status = 'processing'
            WHERE id = %s
        ''', (order_id,))
        conn.commit()
        flash('Order is now being processed!', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error processing order.', 'danger')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('vendor_orders'))

if __name__ == '__main__':
    app.run(debug=True, port=5001) 
    app.run(debug=True, port=5001) 
