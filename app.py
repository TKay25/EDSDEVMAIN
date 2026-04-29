
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import pandas as pd

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DATABASES = {
    'connectlink': "postgresql://connectlinkdata_user:RsYLVxq6lzCBXV7m3e2drdiNMebYBFIC@dpg-d4m0bqggjchc73avg3eg-a.oregon-postgres.render.com/connectlinkdata",
    'zeduweb': "postgresql://zeduweb_user:qdEe6bfJmlIHAknO2TVbum3SSm2kFvFV@dpg-d7cklfa8qa3s73e9podg-a.oregon-postgres.render.com/zeduweb",
    'lmsdatabase': "postgresql://lmsdatabase_8ag3_user:6WD9lOnHkiU7utlUUjT88m4XgEYQMTLb@dpg-ctp9h0aj1k6c739h9di0-a.oregon-postgres.render.com/lmsdatabase_8ag3"
}

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASES['connectlink']
db = SQLAlchemy(app)

# User model for authentication
class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), default='admin')

# Decorator for login required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Bypass all checks and allow any login
        username = request.form.get('username', 'demo')
        session['user_id'] = 1
        session['username'] = username
        session['role'] = 'admin'
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('admin_index.html', dbs=DATABASES.keys())

@app.route('/db/<db_key>')
@login_required
def db_overview(db_key):
    if db_key not in DATABASES:
        flash('Database not found!', 'danger')
        return redirect(url_for('index'))
    # Table browsing placeholder
    return render_template('db_overview.html', db_key=db_key)

@app.route('/quotation', methods=['GET', 'POST'])
@login_required
def quotation():
    if request.method == 'POST':
        client = request.form['client']
        items = request.form.getlist('item')
        prices = request.form.getlist('price')
        # Convert prices to float and calculate totals
        prices_float = [float(p) for p in prices]
        subtotal = sum(prices_float)
        vat = subtotal * 0.15
        total = subtotal + vat

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        # Draw EDS logo (top left)
        logo_path = os.path.join(app.root_path, 'static', 'images', 'eds logo blue.png')
        if os.path.exists(logo_path):
            p.drawImage(logo_path, 40, 720, width=100, height=50, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 16)
        p.drawString(160, 750, f"Quotation for: {client}")
        p.setFont("Helvetica", 12)
        y = 700
        for item, price in zip(items, prices_float):
            p.drawString(100, y, f"{item}: ${price:.2f}")
            y -= 25
        y -= 10
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y, f"Subtotal: ${subtotal:.2f}")
        y -= 20
        p.drawString(100, y, f"VAT (15%): ${vat:.2f}")
        y -= 20
        p.drawString(100, y, f"Total: ${total:.2f}")
        p.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='quotation.pdf', mimetype='application/pdf')
    return render_template('quotation.html')

@app.route('/quotation/excel', methods=['POST'])
@login_required
def quotation_excel():
    client = request.form['client']
    items = request.form.getlist('item')
    prices = request.form.getlist('price')
    df = pd.DataFrame({'Item': items, 'Price': prices})
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Quotation')
        worksheet = writer.sheets['Quotation']
        worksheet.write(0, 3, f'Client: {client}')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='quotation.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# User management (admin only)
@app.route('/users')
@login_required
def users():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    all_users = AdminUser.query.all()
    return render_template('users.html', users=all_users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        if AdminUser.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
        else:
            user = AdminUser(username=username, password_hash=generate_password_hash(password), role=role)
            db.session.add(user)
            db.session.commit()
            flash('User added', 'success')
            return redirect(url_for('users'))
    return render_template('add_user.html')

# Activity log placeholder
@app.route('/logs')
@login_required
def logs():
    # Placeholder for audit trail
    return render_template('logs.html')

# Dashboard placeholder
@app.route('/dashboard')
@login_required
def dashboard():
    # Placeholder for stats
    return render_template('dashboard.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
