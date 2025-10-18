from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///crm.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customers = db.relationship('Customer', backref='user', lazy=True)
    tasks = db.relationship('Task', backref='user', lazy=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(100))
    status = db.Column(db.String(20))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_contact = db.Column(db.DateTime)
    tasks = db.relationship('Task', backref='customer', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')
    priority = db.Column(db.String(20), default='medium')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    customers = Customer.query.filter_by(user_id=session['user_id']).all()
    tasks = Task.query.filter_by(user_id=session['user_id']).order_by(Task.due_date).limit(5).all()
    
    # Dashboard statistics
    total_customers = len(customers)
    total_tasks = len(tasks)
    pending_tasks = Task.query.filter_by(user_id=session['user_id'], status='pending').count()
    
    return render_template('dashboard.html', 
                         user=user,
                         customers=customers,
                         tasks=tasks,
                         total_customers=total_customers,
                         total_tasks=total_tasks,
                         pending_tasks=pending_tasks)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if user already exists
        if User.query.filter_by(email=request.form['email']).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(request.form['password'])
        new_user = User(
            full_name=request.form['full_name'],
            email=request.form['email'],
            password=hashed_password,
            role='user'
        )
        
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            flash('Welcome back!', 'success')
            return redirect(url_for('home'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')
    

def seed_database():
    if not User.query.filter_by(email="admin@example.com").first():
        from werkzeug.security import generate_password_hash
        from datetime import datetime

        # Create admin user
        admin = User(
            full_name="Admin User",
            email="admin@example.com",
            password=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()

        # Sample customers
        customer1 = Customer(
            name="John Doe",
            email="john.doe@example.com",
            phone="1234567890",
            company="Example Corp",
            status="Active",
            user_id=admin.id
        )

        customer2 = Customer(
            name="Jane Smith",
            email="jane.smith@example.com",
            phone="0987654321",
            company="Tech Solutions",
            status="Prospect",
            user_id=admin.id
        )

        db.session.add_all([customer1, customer2])
        db.session.commit()

        # Sample tasks with proper datetime
        task1 = Task(
            title="Follow-up with John Doe",
            description="Discuss project updates",
            due_date=datetime(2025, 1, 20),
            status="pending",
            priority="high",
            user_id=admin.id,
            customer_id=customer1.id
        )

        task2 = Task(
            title="Send proposal to Jane Smith",
            description="Proposal for new CRM system",
            due_date=datetime(2025, 1, 25),
            status="pending",
            priority="medium",
            user_id=admin.id,
            customer_id=customer2.id
        )

        db.session.add_all([task1, task2])
        db.session.commit()
        print("Database seeded successfully!")


# Call the seed function during app startup
with app.app_context():
    db.create_all()
    seed_database()


@app.route('/customer/add', methods=['POST'])
def add_customer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_customer = Customer(
        name=request.form['name'],
        email=request.form['email'],
        phone=request.form['phone'],
        company=request.form['company'],
        status=request.form['status'],
        notes=request.form['notes'],
        user_id=session['user_id'],
        last_contact=datetime.utcnow()
    )
    
    db.session.add(new_customer)
    db.session.commit()
    flash('Customer added successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/task/add', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_task = Task(
        title=request.form['title'],
        description=request.form['description'],
        due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d'),
        priority=request.form['priority'],
        user_id=session['user_id'],
        customer_id=request.form.get('customer_id')
    )
    
    db.session.add(new_task)
    db.session.commit()
    flash('Task added successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))


@app.route('/healthz')
def health_check():
    return "OK", 200

