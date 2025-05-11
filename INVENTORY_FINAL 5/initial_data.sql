-- Insert initial admin user (password: admin123)
INSERT INTO user (username, email, password_hash, role) VALUES 
('admin', 'admin@inventory.com', 'pbkdf2:sha256:600000$X7X7X7X7X7X7X7X7$X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7', 'admin');

-- Insert sample vendor
INSERT INTO user (username, email, password_hash, role) VALUES 
('vendor1', 'vendor1@inventory.com', 'pbkdf2:sha256:600000$X7X7X7X7X7X7X7$X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7', 'vendor');

-- Insert sample manager
INSERT INTO user (username, email, password_hash, role) VALUES 
('manager1', 'manager1@inventory.com', 'pbkdf2:sha256:600000$X7X7X7X7X7X7X7$X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7', 'manager');

-- Insert sample staff
INSERT INTO user (username, email, password_hash, role) VALUES 
('staff1', 'staff1@inventory.com', 'pbkdf2:sha256:600000$X7X7X7X7X7X7X7$X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7', 'staff');

-- Insert sample customer
INSERT INTO user (username, email, password_hash, role) VALUES 
('customer1', 'customer1@inventory.com', 'pbkdf2:sha256:600000$X7X7X7X7X7X7X7$X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7X7', 'customer');

-- Insert sample products
INSERT INTO product (name, description, price, quantity, vendor_id) VALUES
('Laptop', 'High-performance laptop with 16GB RAM', 999.99, 10, 2),
('Smartphone', 'Latest smartphone with 5G capability', 699.99, 20, 2),
('Headphones', 'Wireless noise-cancelling headphones', 199.99, 15, 2),
('Tablet', '10-inch tablet with stylus support', 499.99, 8, 2),
('Smartwatch', 'Fitness tracking smartwatch', 249.99, 12, 2); 