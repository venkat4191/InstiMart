-- Drop existing tables if they exist
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS cart_items CASCADE;
DROP TABLE IF EXISTS carts CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    vendor_id INTEGER REFERENCES users(id),
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50),
    image_url VARCHAR(255),
    is_featured BOOLEAN DEFAULT FALSE,
    discount INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create carts table
CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create cart_items table
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER REFERENCES carts(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create order_items table
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial admin user
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@inventory.com', 'scrypt:32768:8:1$nEZ6eiyhWSg4GQs1$ef44a70979f41ef2325a2055d3c43ad89c36414316483f0d7b9b31524f4d3260e40d8d0e8218c99fde7c4c6a82d25a603476132eed18130e206c984f45a83fc8', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Insert sample products
INSERT INTO products (name, description, price, quantity, vendor_id, category, subcategory, is_featured, discount)
VALUES
    -- Stationery Products
    ('Premium Fountain Pen', 'Smooth writing fountain pen with gold nib and elegant design', 49.99, 50, 1, 'Stationery', 'Writing Instruments', TRUE, 0),
    ('Leather Journal', 'Handcrafted leather journal with 200 pages of premium paper', 29.99, 30, 1, 'Stationery', 'Notebooks', TRUE, 10),
    ('Desk Organizer Set', 'Wooden desk organizer with compartments for pens, papers, and more', 39.99, 25, 1, 'Stationery', 'Desk Accessories', TRUE, 0),
    
    -- Merchandise Products
    ('Limited Edition T-Shirt', 'Premium cotton t-shirt with exclusive design', 24.99, 100, 1, 'Merchandise', 'Apparel', TRUE, 15),
    ('Logo Hoodie', 'Comfortable hoodie with embroidered logo', 49.99, 50, 1, 'Merchandise', 'Apparel', TRUE, 0),
    ('Branded Water Bottle', 'Stainless steel water bottle with company logo', 19.99, 75, 1, 'Merchandise', 'Accessories', TRUE, 5),
    
    -- Daily Essentials
    ('Organic Hand Soap', 'Natural hand soap with essential oils', 9.99, 200, 1, 'Daily Essentials', 'Personal Care', TRUE, 0),
    ('Bamboo Toothbrush Set', 'Eco-friendly bamboo toothbrushes (pack of 4)', 14.99, 150, 1, 'Daily Essentials', 'Personal Care', TRUE, 10),
    ('Reusable Shopping Bag', 'Durable foldable shopping bag with large capacity', 12.99, 100, 1, 'Daily Essentials', 'Household', TRUE, 0),
    
    -- Electronics
    ('Wireless Earbuds', 'True wireless earbuds with charging case', 79.99, 40, 1, 'Electronics', 'Audio', TRUE, 20),
    ('Portable Power Bank', '10000mAh power bank with fast charging', 29.99, 60, 1, 'Electronics', 'Accessories', TRUE, 0),
    ('Smart Watch', 'Fitness tracking smartwatch with heart rate monitor', 149.99, 30, 1, 'Electronics', 'Wearables', TRUE, 15); 