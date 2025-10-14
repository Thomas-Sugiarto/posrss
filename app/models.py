from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import json

def generate_uuid():
    return str(uuid.uuid4())

class Tenant(db.Model):
    __tablename__ = 'tenants'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)  # UUID length 36
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    subdomain = db.Column(db.String(50), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Hardware settings
    printer_type = db.Column(db.String(20), default='thermal')
    printer_settings = db.Column(db.Text, default='{"type": "network", "host": "localhost", "port": 9100, "width": 42}')  # Changed to Text
    barcode_scanner_type = db.Column(db.String(20), default='keyboard')
    
    # Relationships
    users = db.relationship('User', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    products = db.relationship('Product', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    sales = db.relationship('Sale', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    customers = db.relationship('Customer', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')

class MarketplaceItem(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    sku = db.Column(db.String(50), nullable=True, unique=True)
    image_url = db.Column(db.String(255), nullable=True) # URL gambar dari S3
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<MarketplaceItem {self.name}>'
    
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)  # UUID length 36
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))  # Increased length for hashed password
    role = db.Column(db.String(20), nullable=False, default='cashier')
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_superadmin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Foreign keys
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role in ['admin', 'manager']
    
    def is_cashier(self):
        return self.role in ['admin', 'manager', 'cashier']
    
    def get_id(self):
        return self.id

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy='dynamic')

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(100), unique=True)
    barcode = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float)
    stock_quantity = db.Column(db.Integer, default=0)
    stock_alert = db.Column(db.Integer, default=10)
    unit = db.Column(db.String(20), default='pcs')  # pcs, carton
    carton_quantity = db.Column(db.Integer, default=1)  # pieces per carton
    is_active = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    category_id = db.Column(db.String(36), db.ForeignKey('categories.id'))
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='product', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'stock_quantity': self.stock_quantity,
            'image_url': self.image_url,
            'sku': self.sku,
            'barcode': self.barcode
        }

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    
    # Relationships
    sales = db.relationship('Sale', backref='customer', lazy='dynamic')
    
    @property
    def last_sale_date(self):
        """Get the date of the last sale for this customer"""
        last_sale = self.sales.order_by(Sale.created_at.desc()).first()
        return last_sale.created_at if last_sale else None
    
    @property
    def total_spent(self):
        """Calculate total amount spent by customer"""
        return db.session.query(db.func.sum(Sale.total_amount))\
            .filter(Sale.customer_id == self.id)\
            .scalar() or 0
    
    @property 
    def sales_count(self):
        """Get total number of sales"""
        return self.sales.count()

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, card, transfer
    payment_status = db.Column(db.String(20), default='completed')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey('customers.id'))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    # Relationships
    user = db.relationship('User', backref='sales')
    items = db.relationship('SaleItem', backref='sale', lazy='dynamic', cascade='all, delete-orphan')
    
    def calculate_totals(self):
        """Calculate totals from sale items"""
        subtotal = sum(item.total_price for item in self.items)
        self.total_amount = subtotal + self.tax_amount - self.discount_amount

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # Foreign keys
    sale_id = db.Column(db.String(36), db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    
    @property
    def product_name(self):
        return self.product.name

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)