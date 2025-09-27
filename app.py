from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import jdatetime
import os
import sys
import json
from decimal import Decimal

# Unit conversion helper functions
def convert_to_grams(amount, unit):
    """Convert amount from given unit to grams"""
    conversion_factors = {
        'gram': 1,
        'kg': 1000,
        'liter': 1000,  # Assuming 1 liter = 1000 grams (for liquids like milk)
        'ml': 1,        # Assuming 1 ml = 1 gram (for liquids)
        'piece': 1,     # For countable items, treat as 1 gram each
        'pack': 100     # Assuming 1 pack = 100 grams
    }
    return amount * conversion_factors.get(unit, 1)

def convert_from_grams(amount_grams, unit):
    """Convert amount from grams to given unit"""
    conversion_factors = {
        'gram': 1,
        'kg': 1000,
        'liter': 1000,
        'ml': 1,
        'piece': 1,
        'pack': 100
    }
    return amount_grams / conversion_factors.get(unit, 1)

def get_unit_cost_in_grams(unit_cost, unit):
    """Convert unit cost to cost per gram"""
    conversion_factors = {
        'gram': 1,
        'kg': 1000,
        'liter': 1000,
        'ml': 1,
        'piece': 1,
        'pack': 100
    }
    return unit_cost / conversion_factors.get(unit, 1)

def generate_invoice_number():
    """Generate a unique invoice number"""
    today = datetime.now()
    date_prefix = today.strftime('%Y%m%d')
    
    # Get the count of orders for today
    today_orders = Order.query.filter(
        db.func.date(Order.created_at) == today.date()
    ).count()
    
    # Format: YYYYMMDD-XXX (e.g., 20241201-001)
    return f"{date_prefix}-{(today_orders + 1):03d}"

def get_status_display_name(status):
    """Get Persian display name for order status"""
    status_names = {
        'preparing': 'در حال آماده‌سازی',
        'delivered': 'تحویل داده شد',
        'cancelled': 'لغو شده'
    }
    return status_names.get(status, status)

def get_payment_method_display_name(method):
    method_names = {
        'cash': 'نقدی',
        'card': 'کارتی'
    }
    return method_names.get(method, method)

def _get_base_path():
    return getattr(sys, '_MEIPASS', os.path.abspath('.'))

def _get_templates_path():
    return os.path.join(_get_base_path(), 'templates')

def _get_static_path():
    return os.path.join(_get_base_path(), 'static')

def _get_user_data_dir():
    if sys.platform.startswith('win'):
        root = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
        path = os.path.join(root, 'CafeAppData')
    else:
        path = os.path.join(os.path.expanduser('~'), '.cafe_app')
    os.makedirs(path, exist_ok=True)
    return path

def _get_database_path():
    data_dir = _get_user_data_dir()
    db_path = os.path.join(data_dir, 'cafe.db')
    return db_path

app = Flask(__name__, template_folder=_get_templates_path(), static_folder=_get_static_path())
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + _get_database_path()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add custom Jinja2 filters
@app.template_filter('abs')
def abs_filter(value):
    """Custom filter for absolute value"""
    return abs(value)

@app.template_filter('convert_to_grams')
def convert_to_grams_filter(amount, unit):
    """Custom filter for converting amount to grams"""
    return convert_to_grams(amount, unit)

@app.template_filter('convert_from_grams')
def convert_from_grams_filter(amount_grams, unit):
    """Custom filter for converting amount from grams to display unit"""
    return convert_from_grams(amount_grams, unit)

# Jalali (Shamsi) date formatting filters
@app.template_filter('jalali_date')
def jalali_date_filter(value):
    if not value:
        return ''
    try:
        jdt = jdatetime.datetime.fromgregorian(datetime=value)
        return jdt.strftime('%Y/%m/%d')
    except Exception:
        return ''

@app.template_filter('jalali_datetime')
def jalali_datetime_filter(value):
    if not value:
        return ''
    try:
        jdt = jdatetime.datetime.fromgregorian(datetime=value)
        return jdt.strftime('%Y/%m/%d %H:%M')
    except Exception:
        return ''

@app.template_filter('format_time')
def format_time_filter(value):
    if not value:
        return ''
    try:
        return value.strftime('%H:%M')
    except Exception:
        return ''

@app.template_filter('jalali_month')
def jalali_month_filter(value):
    if not value:
        return ''
    try:
        jdt = jdatetime.datetime.fromgregorian(datetime=value)
        return jdt.strftime('%Y-%m')
    except Exception:
        return ''

db = SQLAlchemy(app)

# Helpers to parse Jalali input and convert to Gregorian datetime
def parse_jalali_date_or_gregorian(date_str: str) -> datetime:
    """Parse a date string that may be in Jalali (YYYY-MM-DD) or Gregorian (YYYY-MM-DD) and return Gregorian datetime."""
    if not date_str:
        return datetime.now()
    # Try Jalali first
    try:
        jdt = jdatetime.datetime.strptime(date_str, '%Y-%m-%d')
        return jdt.togregorian()
    except Exception:
        pass
    # Fallback to Gregorian
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except Exception:
        return datetime.now()

def parse_jalali_month_or_gregorian(month_str: str) -> str:
    """Parse a month string that may be in Jalali (YYYY-MM) or Gregorian (YYYY-MM) and return Gregorian month string YYYY-%m suitable for SQL filtering."""
    if not month_str:
        return datetime.now().strftime('%Y-%m')
    # Try Jalali month first
    try:
        # Force day=1 to avoid invalid day rollbacks
        j_year, j_month = map(int, month_str.split('-'))
        jdt = jdatetime.date(j_year, j_month, 1)
        gdt = jdt.togregorian()
        return gdt.strftime('%Y-%m')
    except Exception:
        pass
    # Fallback to Gregorian
    try:
        g_year, g_month = map(int, month_str.split('-'))
        gdt = datetime(g_year, g_month, 1)
        return gdt.strftime('%Y-%m')
    except Exception:
        return datetime.now().strftime('%Y-%m')

# Database Models
class RawMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    current_stock = db.Column(db.Float, nullable=False)  # stored in grams
    unit_cost = db.Column(db.Float, nullable=False)  # cost per gram
    display_unit = db.Column(db.String(20), default='gram')  # unit for display
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    @property
    def display_stock(self):
        """Return stock in display unit"""
        return convert_from_grams(self.current_stock, self.display_unit)
    
    @property
    def display_unit_cost(self):
        """Return unit cost in display unit"""
        return self.unit_cost * convert_to_grams(1, self.display_unit)
    
    @property
    def total_value(self):
        """Return total value of current stock"""
        return self.current_stock * self.unit_cost

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    recipe = db.Column(db.Text, nullable=False)  # JSON string of ingredients
    deleted = db.Column(db.Boolean, default=False)  # Soft delete flag
    created_at = db.Column(db.DateTime, default=datetime.now)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)
    product = db.relationship('Product', backref=db.backref('sales', lazy=True))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(20), default='preparing')  # preparing, delivered, cancelled
    notes = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(20), default='card')  # cash, card
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship to order items
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # Relationship to product
    product = db.relationship('Product', backref=db.backref('order_items', lazy=True))

class OverheadCost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(20), default='monthly')  # monthly, daily
    created_at = db.Column(db.DateTime, default=datetime.now)

class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # positive for addition, negative for consumption
    movement_type = db.Column(db.String(20), nullable=False)  # 'purchase', 'consumption'
    date = db.Column(db.DateTime, default=datetime.now)
    material = db.relationship('RawMaterial', backref=db.backref('movements', lazy=True))

# Routes
@app.route('/')
def dashboard():
    # Get summary statistics
    total_orders_today = Order.query.filter(
        db.func.date(Order.created_at) == datetime.now().date()
    ).count()
    
    total_sales_today = db.session.query(db.func.sum(Order.total_amount)).filter(
        db.func.date(Order.created_at) == datetime.now().date()
    ).scalar() or 0
    
    total_orders_month = Order.query.filter(
        db.func.strftime('%Y-%m', Order.created_at) == datetime.now().strftime('%Y-%m')
    ).count()
    
    total_sales_month = db.session.query(db.func.sum(Order.total_amount)).filter(
        db.func.strftime('%Y-%m', Order.created_at) == datetime.now().strftime('%Y-%m')
    ).scalar() or 0
    
    total_products = Product.query.count()
    
    # Get all materials and filter by display unit thresholds
    all_materials = RawMaterial.query.all()
    low_stock_materials = []
    
    for material in all_materials:
        display_stock = material.display_stock
        # Define thresholds based on display unit
        if material.display_unit == 'kg':
            threshold = 1  # 1 kg
        elif material.display_unit == 'liter':
            threshold = 1  # 1 liter
        elif material.display_unit == 'ml':
            threshold = 1000  # 1000 ml
        elif material.display_unit == 'piece':
            threshold = 100  # 100 pieces
        elif material.display_unit == 'pack':
            threshold = 10  # 10 packs
        else:  # gram or default
            threshold = 1000  # 1000 grams
        
        if display_stock < threshold:
            low_stock_materials.append(material)
    
    # Calculate break-even analysis
    monthly_overhead = db.session.query(db.func.sum(OverheadCost.amount)).filter(
        OverheadCost.period == 'monthly'
    ).scalar() or 0
    
    # Get actual order data for the current month
    current_month = datetime.now().strftime('%Y-%m')
    monthly_orders = Order.query.filter(
        db.func.strftime('%Y-%m', Order.created_at) == current_month
    ).all()
    
    if monthly_orders and total_orders_month > 0:
        # Calculate average profit margin from actual orders
        total_material_costs = 0
        for order in monthly_orders:
            for item in order.items:
                # Calculate material cost for this item
                recipe = json.loads(item.product.recipe)
                item_material_cost = 0
                for material_id, amount in recipe.items():
                    material = RawMaterial.query.get(int(material_id))
                    if material:
                        item_material_cost += amount * material.unit_cost * item.quantity
                total_material_costs += item_material_cost
        
        total_profit = total_sales_month - total_material_costs
        avg_profit_per_order = total_profit / total_orders_month
        
        # Calculate break-even
        break_even_orders = monthly_overhead / avg_profit_per_order if avg_profit_per_order > 0 else 0
    else:
        # Fallback to product-based calculation if no orders exist
        products = Product.query.all()
        total_margin = 0
        
        for product in products:
            recipe = json.loads(product.recipe)
            material_cost = 0
            for material_id, amount in recipe.items():
                material = RawMaterial.query.get(int(material_id))
                if material:
                    material_cost += amount * material.unit_cost
            
            margin = product.price - material_cost
            total_margin += margin
        
        avg_margin = total_margin / len(products) if products else 0
        break_even_orders = monthly_overhead / avg_margin if avg_margin > 0 else 0
    
    return render_template('dashboard.html',
                         total_orders_today=total_orders_today,
                         total_sales_today=total_sales_today,
                         total_orders_month=total_orders_month,
                         total_sales_month=total_sales_month,
                         total_products=total_products,
                         low_stock_materials=low_stock_materials,
                         monthly_overhead=monthly_overhead,
                         break_even_orders=break_even_orders)

@app.route('/materials')
def materials():
    materials = RawMaterial.query.all()
    # Calculate total inventory value correctly using the new property
    total_inventory_value = sum(material.total_value for material in materials)
    return render_template('materials.html', materials=materials, total_inventory_value=total_inventory_value)

@app.route('/materials/add', methods=['GET', 'POST'])
def add_material():
    if request.method == 'POST':
        name = request.form['name']
        current_stock = float(request.form['current_stock'])
        unit_cost = float(request.form['unit_cost'])
        display_unit = request.form['unit']
        
        # Convert to grams for storage
        stock_in_grams = convert_to_grams(current_stock, display_unit)
        cost_per_gram = get_unit_cost_in_grams(unit_cost, display_unit)
        
        material = RawMaterial(name=name, current_stock=stock_in_grams, 
                             unit_cost=cost_per_gram, display_unit=display_unit)
        db.session.add(material)
        db.session.commit()
        
        flash('Material added successfully!', 'success')
        return redirect(url_for('materials'))
    
    return render_template('add_material.html')

@app.route('/materials/<int:id>/edit', methods=['GET', 'POST'])
def edit_material(id):
    material = RawMaterial.query.get_or_404(id)
    
    if request.method == 'POST':
        material.name = request.form['name']
        display_unit = request.form['unit']
        
        # Convert input values to grams for storage
        current_stock = float(request.form['current_stock'])
        unit_cost = float(request.form['unit_cost'])
        
        material.current_stock = convert_to_grams(current_stock, display_unit)
        material.unit_cost = get_unit_cost_in_grams(unit_cost, display_unit)
        material.display_unit = display_unit
        
        db.session.commit()
        flash('Material updated successfully!', 'success')
        return redirect(url_for('materials'))
    
    return render_template('edit_material.html', material=material)

@app.route('/products')
def products():
    # Only show non-deleted products in the main list
    products = Product.query.filter_by(deleted=False).all()
    return render_template('products.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        
        # Parse recipe from form with unit conversion
        recipe = {}
        materials = RawMaterial.query.all()
        for material in materials:
            amount = request.form.get(f'recipe_{material.id}')
            unit = request.form.get(f'unit_{material.id}', 'gram')  # Default to gram if not provided
            
            if amount and float(amount) > 0:
                # Convert amount to grams for storage
                amount_in_grams = convert_to_grams(float(amount), unit)
                recipe[material.id] = amount_in_grams
        
        product = Product(name=name, price=price, recipe=json.dumps(recipe))
        db.session.add(product)
        db.session.commit()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
    
    materials = RawMaterial.query.all()
    return render_template('add_product.html', materials=materials)

@app.route('/products/<int:id>/edit', methods=['GET', 'POST'])
def edit_product(id):
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])
        
        # Parse recipe from form with unit conversion
        recipe = {}
        materials = RawMaterial.query.all()
        for material in materials:
            amount = request.form.get(f'recipe_{material.id}')
            unit = request.form.get(f'unit_{material.id}', 'gram')
            
            if amount and float(amount) > 0:
                # Convert amount to grams for storage
                amount_in_grams = convert_to_grams(float(amount), unit)
                recipe[material.id] = amount_in_grams
        
        product.recipe = json.dumps(recipe)
        db.session.commit()
        
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products'))
    
    materials = RawMaterial.query.all()
    current_recipe = json.loads(product.recipe) if product.recipe else {}
    return render_template('edit_product.html', product=product, materials=materials, current_recipe=current_recipe)

@app.route('/products/<int:id>/delete', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    
    # Soft delete: Mark product as deleted but keep all data intact
    # This preserves historical data and reporting integrity
    
    # Check if product has any orders
    if product.order_items:
        order_count = len(product.order_items)
        flash(f'محصول "{product.name}" حذف شد. این محصول در {order_count} سفارش قبلی باقی می‌ماند تا گزارش‌گیری تحت تأثیر قرار نگیرد.', 'success')
    else:
        flash(f'محصول "{product.name}" با موفقیت حذف شد!', 'success')
    
    # Mark as deleted instead of removing from database
    product.deleted = True
    db.session.commit()
    
    return redirect(url_for('products'))

@app.route('/products/deleted')
def deleted_products():
    """View deleted products (for admin purposes)"""
    deleted_products = Product.query.filter_by(deleted=True).all()
    return render_template('deleted_products.html', products=deleted_products)

@app.route('/products/<int:id>/restore', methods=['POST'])
def restore_product(id):
    """Restore a deleted product"""
    product = Product.query.get_or_404(id)
    if product.deleted:
        product.deleted = False
        db.session.commit()
        flash(f'محصول "{product.name}" با موفقیت بازیابی شد!', 'success')
    else:
        flash('این محصول قبلاً بازیابی شده است.', 'info')
    
    return redirect(url_for('deleted_products'))

@app.route('/sales')
def sales():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/orders')
def orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/orders/add', methods=['GET', 'POST'])
def add_order():
    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        customer_phone = request.form.get('customer_phone', '').strip()
        payment_method = request.form.get('payment_method', 'card').strip() or 'card'
        
        # Make customer information optional with fallback values
        if not customer_name:
            customer_name = 'مشتری ناشناس'
        if not customer_phone:
            customer_phone = 'ثبت نشده'
        
        # Generate invoice number
        invoice_number = generate_invoice_number()
        
        # Create order
        order = Order(
            invoice_number=invoice_number,
            customer_name=customer_name,
            customer_phone=customer_phone,
            status='preparing',
            payment_method=payment_method
        )
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Process order items from dropdown form
        total_amount = 0
        product_counter = 0
        
        while f'product_{product_counter}' in request.form:
            product_id = request.form.get(f'product_{product_counter}')
            quantity = request.form.get(f'quantity_{product_counter}')
            
            if product_id and quantity and int(quantity) > 0:
                product = Product.query.get(int(product_id))
                if product and not product.deleted:  # Only allow non-deleted products
                    quantity = int(quantity)
                    unit_price = product.price
                    total_price = unit_price * quantity
                    total_amount += total_price
                    
                    # Create order item
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                    db.session.add(order_item)
                    
                    # Update inventory (consume materials)
                    recipe = json.loads(product.recipe)
                    for material_id, amount in recipe.items():
                        material = RawMaterial.query.get(int(material_id))
                        if material:
                            consumed_amount = amount * quantity
                            material.current_stock -= consumed_amount
                            
                            # Record stock movement
                            movement = StockMovement(
                                material_id=material.id,
                                quantity=-consumed_amount,
                                movement_type='consumption'
                            )
                            db.session.add(movement)
            
            product_counter += 1
        
        if total_amount == 0:
            flash('حداقل یک محصول باید انتخاب شود!', 'error')
            db.session.rollback()
            return redirect(url_for('add_order'))
        
        # Update order total
        order.total_amount = total_amount
        
        db.session.commit()
        flash(f'سفارش با شماره فاکتور {invoice_number} ثبت شد!', 'success')
        return redirect(url_for('view_invoice', order_id=order.id))
    
    # Get only non-deleted products for new orders
    products = Product.query.filter_by(deleted=False).all()
    return render_template('add_order.html', products=products)

@app.route('/orders/<int:order_id>')
def view_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('invoice.html', order=order)

@app.route('/orders/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status in ['preparing', 'delivered', 'cancelled']:
        order.status = new_status
        order.updated_at = datetime.now()
        db.session.commit()
        flash(f'وضعیت سفارش به "{get_status_display_name(new_status)}" تغییر یافت!', 'success')
    
    return redirect(url_for('view_invoice', order_id=order_id))

@app.route('/orders/<int:order_id>/print')
def print_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('print_invoice.html', order=order)

@app.route('/overhead')
def overhead():
    overhead_costs = OverheadCost.query.all()
    return render_template('overhead.html', overhead_costs=overhead_costs)

@app.route('/overhead/add', methods=['GET', 'POST'])
def add_overhead():
    if request.method == 'POST':
        name = request.form['name']
        amount = float(request.form['amount'])
        period = request.form['period']
        
        overhead = OverheadCost(name=name, amount=amount, period=period)
        db.session.add(overhead)
        db.session.commit()
        
        flash('Overhead cost added successfully!', 'success')
        return redirect(url_for('overhead'))
    
    return render_template('add_overhead.html')

@app.route('/overhead/<int:cost_id>')
def overhead_detail(cost_id):
    cost = OverheadCost.query.get_or_404(cost_id)
    return jsonify({
        'id': cost.id,
        'name': cost.name,
        'amount': cost.amount,
        'period': cost.period,
        'period_display': 'ماهانه' if cost.period == 'monthly' else 'روزانه',
        'created_at': jdatetime.datetime.fromgregorian(datetime=cost.created_at).strftime('%Y/%m/%d %H:%M') if cost.created_at else ''
    })

@app.route('/overhead/<int:cost_id>/edit', methods=['GET', 'POST'])
def edit_overhead(cost_id):
    cost = OverheadCost.query.get_or_404(cost_id)
    if request.method == 'POST':
        cost.name = request.form['name']
        cost.amount = float(request.form['amount'])
        cost.period = request.form['period']
        db.session.commit()
        flash('هزینه با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('overhead'))
    return render_template('edit_overhead.html', cost=cost)

@app.route('/overhead/<int:cost_id>/delete', methods=['POST'])
def delete_overhead(cost_id):
    cost = OverheadCost.query.get_or_404(cost_id)
    db.session.delete(cost)
    db.session.commit()
    flash('هزینه با موفقیت حذف شد.', 'success')
    return redirect(url_for('overhead'))

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/reports/daily')
def daily_report():
    date = request.args.get('date', None)
    if not date:
        # default to today in Gregorian, but show Jalali in template via filter
        selected_date = datetime.now()
    else:
        selected_date = parse_jalali_date_or_gregorian(date)
    
    # Get orders for the day with proper relationships loaded
    daily_orders = Order.query.filter(
        db.func.date(Order.created_at) == selected_date.date()
    ).options(
        db.joinedload(Order.items).joinedload(OrderItem.product)
    ).all()
    
    total_sales = sum(order.total_amount for order in daily_orders)
    
    # Get material consumption for the day with costs
    daily_consumption = db.session.query(
        RawMaterial.name,
        db.func.sum(StockMovement.quantity).label('consumed'),
        RawMaterial.unit_cost
    ).join(StockMovement).filter(
        db.func.date(StockMovement.date) == selected_date.date(),
        StockMovement.movement_type == 'consumption'
    ).group_by(RawMaterial.id).all()
    
    # Calculate material costs for the day
    material_costs = sum(abs(consumed) * cost for _, consumed, cost in daily_consumption)
    
    # Get daily overhead costs (using period filter)
    daily_overhead = db.session.query(db.func.sum(OverheadCost.amount)).filter(
        OverheadCost.period == 'daily'
    ).scalar() or 0
    
    # Calculate estimated profit
    total_costs = material_costs + daily_overhead
    estimated_profit = total_sales - total_costs
    
    # Debug information
    print(f"Daily report for {date}:")
    print(f"Orders found: {len(daily_orders)}")
    for order in daily_orders:
        print(f"Order {order.id}: {len(order.items)} items")
        for item in order.items:
            print(f"  Item {item.id}: Product={item.product.name if item.product else 'NO PRODUCT'}, Qty={item.quantity}")
    
    return render_template('daily_report.html',
                         date=selected_date,
                         daily_orders=daily_orders,
                         total_sales=total_sales,
                         daily_consumption=daily_consumption,
                         material_costs=material_costs,
                         overhead_costs=daily_overhead,
                         total_costs=total_costs,
                         estimated_profit=estimated_profit)

@app.route('/reports/monthly')
def monthly_report():
    # Prefer explicit Jalali year/month
    jy_raw = request.args.get('jy')
    jm_raw = request.args.get('jm')
    if jy_raw and jm_raw:
        try:
            jy_int = int(jy_raw)
            jm_int = int(jm_raw)
        except Exception:
            jy_int = jdatetime.datetime.now().year
            jm_int = jdatetime.datetime.now().month
    else:
        # Fallback: try single month string or current Jalali date
        month_param = request.args.get('month', None)
        if month_param:
            try:
                jdt_tmp = jdatetime.datetime.strptime(month_param, '%Y-%m')
                jy_int, jm_int = jdt_tmp.year, jdt_tmp.month
            except Exception:
                now_j = jdatetime.datetime.now()
                jy_int, jm_int = now_j.year, now_j.month
        else:
            now_j = jdatetime.datetime.now()
            jy_int, jm_int = now_j.year, now_j.month

    # Build month filter from Jalali year/month (force day=1)
    try:
        j_first = jdatetime.date(jy_int, jm_int, 1)
        g_first = j_first.togregorian()
        month_filter = g_first.strftime('%Y-%m')
        selected_month = datetime(g_first.year, g_first.month, 1)
    except Exception:
        selected_month = datetime.now().replace(day=1)
        month_filter = selected_month.strftime('%Y-%m')
    
    # Get orders for the month
    monthly_orders = Order.query.filter(
        db.func.strftime('%Y-%m', Order.created_at) == month_filter
    ).all()
    
    total_sales = sum(order.total_amount for order in monthly_orders)
    
    # Get material consumption for the month
    monthly_consumption = db.session.query(
        RawMaterial.name,
        db.func.sum(StockMovement.quantity).label('consumed'),
        RawMaterial.unit_cost
    ).join(StockMovement).filter(
        db.func.strftime('%Y-%m', StockMovement.date) == month_filter,
        StockMovement.movement_type == 'consumption'
    ).group_by(RawMaterial.id).all()
    
    # Fallback: if no stock movements recorded, derive consumption from orders' recipes
    if (not monthly_consumption) and monthly_orders:
        material_id_to_total_grams = {}
        for order in monthly_orders:
            for item in order.items:
                if not item.product:
                    continue
                try:
                    recipe = json.loads(item.product.recipe)
                except Exception:
                    recipe = {}
                for material_id_str, amount_grams in recipe.items():
                    try:
                        material_id = int(material_id_str)
                    except Exception:
                        continue
                    consumed_grams = (amount_grams or 0) * (item.quantity or 0)
                    material_id_to_total_grams[material_id] = material_id_to_total_grams.get(material_id, 0) + consumed_grams
        monthly_consumption = []
        for material_id, total_grams in material_id_to_total_grams.items():
            material = RawMaterial.query.get(material_id)
            if material:
                monthly_consumption.append((material.name, -abs(total_grams), material.unit_cost))
    
    # Calculate costs
    material_costs = sum(abs(consumed) * cost for _, consumed, cost in monthly_consumption)
    overhead_costs = db.session.query(db.func.sum(OverheadCost.amount)).filter(
        OverheadCost.period == 'monthly'
    ).scalar() or 0
    
    total_costs = material_costs + overhead_costs
    profit = total_sales - total_costs
    
    # Build aggregated product summary for the month
    product_summary = {}
    for order in monthly_orders:
        for item in order.items:
            if not item.product:
                continue
            name = item.product.name
            if name not in product_summary:
                product_summary[name] = {'quantity': 0, 'revenue': 0}
            product_summary[name]['quantity'] += item.quantity or 0
            product_summary[name]['revenue'] += item.total_price or 0

    # Prepare Jalali selector context (use submitted jy/jm directly)
    jalali_year = jy_int
    jalali_month = jm_int
    jalali_years = [jalali_year - 2, jalali_year - 1, jalali_year, jalali_year + 1]

    return render_template('monthly_report.html',
                         month=selected_month,
                         monthly_orders=monthly_orders,
                         product_summary=product_summary,
                         total_sales=total_sales,
                         monthly_consumption=monthly_consumption,
                         material_costs=material_costs,
                         overhead_costs=overhead_costs,
                         total_costs=total_costs,
                         profit=profit,
                         jalali_year=jalali_year,
                         jalali_month=jalali_month,
                         jalali_years=jalali_years)

@app.route('/api/calculate_cost/<int:product_id>')
def calculate_cost(product_id):
    product = Product.query.get_or_404(product_id)
    recipe = json.loads(product.recipe)
    
    total_cost = 0
    for material_id, amount in recipe.items():
        material = RawMaterial.query.get(int(material_id))
        if material:
            total_cost += amount * material.unit_cost
    
    return jsonify({
        'product_name': product.name,
        'selling_price': product.price,
        'material_cost': total_cost,
        'profit_margin': product.price - total_cost
    })

@app.route('/api/recipe_details/<int:product_id>')
def recipe_details(product_id):
    product = Product.query.get_or_404(product_id)
    recipe = json.loads(product.recipe)
    
    recipe_details = []
    for material_id, amount_grams in recipe.items():
        material = RawMaterial.query.get(int(material_id))
        if material:
            # Convert from grams to display unit for better readability
            amount_in_display_unit = convert_from_grams(amount_grams, material.display_unit)
            recipe_details.append({
                'material_name': material.name,
                'amount': amount_in_display_unit,
                'unit': material.display_unit,
                'unit_cost': material.display_unit_cost,
                'total_cost': amount_grams * material.unit_cost
            })
    
    return jsonify({
        'product_name': product.name,
        'recipe': recipe_details
    })

@app.route('/api/weekly_sales_data')
def weekly_sales_data():
    """Get weekly sales data for the current month"""
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get orders for the current month
    monthly_orders = Order.query.filter(
        db.func.strftime('%Y-%m', Order.created_at) == current_month
    ).all()
    
    # Initialize weekly data (4 weeks)
    weekly_data = [0, 0, 0, 0]
    week_labels = ['هفته 1', 'هفته 2', 'هفته 3', 'هفته 4']
    
    for order in monthly_orders:
        # Calculate which week of the month this order belongs to
        day_of_month = order.created_at.day
        week_index = min((day_of_month - 1) // 7, 3)  # 0-3 for 4 weeks
        weekly_data[week_index] += order.total_amount
    
    # Convert to thousands for better display
    weekly_data_thousands = [amount / 1000 for amount in weekly_data]
    
    return jsonify({
        'labels': week_labels,
        'data': weekly_data_thousands
    })

@app.route('/api/cost_distribution_data')
def cost_distribution_data():
    """Get cost distribution data for the current month"""
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get orders for the current month
    monthly_orders = Order.query.filter(
        db.func.strftime('%Y-%m', Order.created_at) == current_month
    ).all()
    
    # Calculate total revenue
    total_revenue = sum(order.total_amount for order in monthly_orders)
    
    # Calculate material costs from actual consumption in orders
    total_material_costs = 0
    for order in monthly_orders:
        for item in order.items:
            recipe = json.loads(item.product.recipe)
            item_material_cost = 0
            for material_id, amount in recipe.items():
                material = RawMaterial.query.get(int(material_id))
                if material:
                    item_material_cost += amount * material.unit_cost * item.quantity
            total_material_costs += item_material_cost
    
    # Get overhead costs
    overhead_costs = db.session.query(db.func.sum(OverheadCost.amount)).filter(
        OverheadCost.period == 'monthly'
    ).scalar() or 0
    
    # Calculate profit
    total_costs = total_material_costs + overhead_costs
    profit = total_revenue - total_costs
    
    return jsonify({
        'labels': ['سود خالص', 'هزینه مواد اولیه', 'هزینه‌های عملیاتی'],
        'data': [profit, total_material_costs, overhead_costs]
    })

@app.route('/api/quick_stats')
def quick_stats():
    """Get quick statistics for the dashboard"""
    # Get today's data
    today = datetime.now().date()
    today_orders = Order.query.filter(
        db.func.date(Order.created_at) == today
    ).all()
    today_sales = sum(order.total_amount for order in today_orders)
    
    # Get current month's data
    current_month = datetime.now().strftime('%Y-%m')
    monthly_orders = Order.query.filter(
        db.func.strftime('%Y-%m', Order.created_at) == current_month
    ).all()
    month_sales = sum(order.total_amount for order in monthly_orders)
    
    # Calculate average daily sales for current month
    days_in_month = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1) - datetime.now().replace(day=1)
    days_passed = min(datetime.now().day, days_in_month.days)
    avg_daily_sales = month_sales / days_passed if days_passed > 0 else 0
    
    # Calculate profit margin from actual orders
    if monthly_orders:
        total_material_costs = 0
        for order in monthly_orders:
            for item in order.items:
                recipe = json.loads(item.product.recipe)
                item_material_cost = 0
                for material_id, amount in recipe.items():
                    material = RawMaterial.query.get(int(material_id))
                    if material:
                        item_material_cost += amount * material.unit_cost * item.quantity
                total_material_costs += item_material_cost
        
        total_profit = month_sales - total_material_costs
        profit_margin = (total_profit / month_sales * 100) if month_sales > 0 else 0
    else:
        profit_margin = 0
    
    return jsonify({
        'today_sales': today_sales,
        'month_sales': month_sales,
        'avg_daily_sales': avg_daily_sales,
        'profit_margin': profit_margin
    })

@app.route('/api/product_orders_info/<int:product_id>')
def product_orders_info(product_id):
    """Get information about whether a product has orders"""
    product = Product.query.get_or_404(product_id)
    
    has_orders = len(product.order_items) > 0
    order_count = len(product.order_items)
    
    return jsonify({
        'has_orders': has_orders,
        'order_count': order_count
    })

@app.route('/api/break_even_analysis')
def break_even_analysis():
    # Get all overhead costs
    monthly_overhead = db.session.query(db.func.sum(OverheadCost.amount)).filter(
        OverheadCost.period == 'monthly'
    ).scalar() or 0
    
    # Get actual order data for the current month
    current_month = datetime.now().strftime('%Y-%m')
    monthly_orders = Order.query.filter(
        db.func.strftime('%Y-%m', Order.created_at) == current_month
    ).all()
    
    if monthly_orders:
        total_revenue = sum(order.total_amount for order in monthly_orders)
        total_orders = len(monthly_orders)
        avg_order_value = total_revenue / total_orders
        
        # Calculate average profit margin from actual orders
        total_material_costs = 0
        for order in monthly_orders:
            for item in order.items:
                # Calculate material cost for this item
                recipe = json.loads(item.product.recipe)
                item_material_cost = 0
                for material_id, amount in recipe.items():
                    material = RawMaterial.query.get(int(material_id))
                    if material:
                        item_material_cost += amount * material.unit_cost * item.quantity
                total_material_costs += item_material_cost
        
        total_profit = total_revenue - total_material_costs
        avg_profit_per_order = total_profit / total_orders if total_orders > 0 else 0
        
        # Calculate break-even
        break_even_orders = monthly_overhead / avg_profit_per_order if avg_profit_per_order > 0 else 0
        break_even_revenue = break_even_orders * avg_order_value
    else:
        # Fallback to product-based calculation if no orders exist
        products = Product.query.all()
        total_margin = 0
        total_price = 0
        
        for product in products:
            recipe = json.loads(product.recipe)
            material_cost = 0
            for material_id, amount in recipe.items():
                material = RawMaterial.query.get(int(material_id))
                if material:
                    material_cost += amount * material.unit_cost
            
            margin = product.price - material_cost
            total_margin += margin
            total_price += product.price
        
        avg_margin = total_margin / len(products) if products else 0
        break_even_orders = monthly_overhead / avg_margin if avg_margin > 0 else 0
        break_even_revenue = break_even_orders * (total_price / len(products)) if products else 0
        avg_profit_per_order = avg_margin
    
    return jsonify({
        'monthly_overhead': monthly_overhead,
        'average_profit_per_order': avg_profit_per_order,
        'break_even_orders': break_even_orders,
        'break_even_revenue': break_even_revenue
    })

@app.route('/test/data')
def test_data():
    """Test route to check current data in the system"""
    orders = Order.query.all()
    products = Product.query.all()
    order_items = OrderItem.query.all()
    
    result = {
        'total_orders': len(orders),
        'total_products': len(products),
        'total_order_items': len(order_items),
        'orders': [],
        'products': []
    }
    
    for order in orders[:5]:  # Show first 5 orders
        order_data = {
            'id': order.id,
            'invoice': order.invoice_number,
            'customer': order.customer_name,
            'total': order.total_amount,
            'status': order.status,
            'created': jdatetime.datetime.fromgregorian(datetime=order.created_at).strftime('%Y/%m/%d %H:%M'),
            'items_count': len(order.items),
            'items': []
        }
        
        for item in order.items:
            item_data = {
                'id': item.id,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price,
                'product_id': item.product_id,
                'product_name': item.product.name if item.product else 'NO PRODUCT'
            }
            order_data['items'].append(item_data)
        
        result['orders'].append(order_data)
    
    for product in products[:5]:  # Show first 5 products
        product_data = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'deleted': product.deleted,
            'order_items_count': len(product.order_items)
        }
        result['products'].append(product_data)
    
    return jsonify(result)

if __name__ == '__main__':
    import threading, webbrowser
    with app.app_context():
        # Optional reset: set env CAFEMANAGER_RESET_DB=1 to start with a fresh database
        try:
            if os.environ.get('CAFEMANAGER_RESET_DB') == '1':
                db_path = _get_database_path()
                if os.path.exists(db_path):
                    os.remove(db_path)
        except Exception:
            pass
        db.create_all()
        # Runtime migration: ensure payment_method column exists on Order
        try:
            # Check if column exists by simple select
            db.session.execute(db.text('SELECT payment_method FROM "order" LIMIT 1'))
        except Exception:
            try:
                db.session.execute(db.text('ALTER TABLE "order" ADD COLUMN payment_method VARCHAR(20) DEFAULT "cash"'))
                db.session.commit()
            except Exception as e:
                print('Migration failed for payment_method:', e)
    try:
        threading.Timer(1.0, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    except Exception:
        pass
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
