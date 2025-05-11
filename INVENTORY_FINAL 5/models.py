from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    orders = db.relationship('Order', back_populates='user', lazy=True)
    cart = db.relationship('Cart', backref='user', uselist=False, lazy=True)
    products = db.relationship('Product', backref='vendor')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    vendor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50))
    is_featured = db.Column(db.Boolean, default=False)
    discount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    cart_items = db.relationship('CartItem', backref='product')
    order_items = db.relationship('OrderItem', backref='product')

    @property
    def discounted_price(self):
        return self.price * (1 - self.discount / 100)

    @classmethod
    def search(cls, query, category=None, min_price=None, max_price=None):
        search_query = cls.query
        if query:
            search_query = search_query.filter(
                (cls.name.ilike(f'%{query}%')) | 
                (cls.description.ilike(f'%{query}%'))
            )
        if category:
            search_query = search_query.filter(cls.category == category)
        if min_price is not None:
            search_query = search_query.filter(cls.price >= min_price)
        if max_price is not None:
            search_query = search_query.filter(cls.price <= max_price)
        return search_query.all()

    @classmethod
    def get_categories(cls):
        return db.session.query(cls.category).distinct().all()

    @classmethod
    def get_featured_products(cls, limit=6):
        return cls.query.filter_by(is_featured=True).limit(limit).all()

class Cart(db.Model):
    __tablename__ = 'carts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')
    
    @property
    def total_amount(self):
        return sum(item.product.price * item.quantity for item in self.items)

    def __repr__(self):
        return f'<Cart {self.id}>'

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    shipping_address = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='orders')
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 