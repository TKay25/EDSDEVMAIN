
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


@app.route('/invoice', methods=['GET', 'POST'])
@login_required
def invoice():
    if request.method == 'POST':
        from jinja2 import Environment, FileSystemLoader
        from weasyprint import HTML
        client = request.form['client']
        items = request.form.getlist('item')
        prices = request.form.getlist('price')
        prices_float = [float(p) for p in prices]
        subtotal = sum(prices_float)
        vat = subtotal * 0.15
        total = subtotal + vat

        from datetime import datetime
        import random
        invoice_items = list(zip(items, prices_float))
        logo_path = os.path.join('static', 'images', 'eds logo blue.png')

        # Get user-provided dates and format as '24 February 2026'
        invoice_date_raw = request.form.get('invoice_date')
        due_date_raw = request.form.get('due_date')
        invoice_date = datetime.strptime(invoice_date_raw, '%Y-%m-%d').strftime('%d %B %Y') if invoice_date_raw else datetime.now().strftime('%d %B %Y')
        due_date = datetime.strptime(due_date_raw, '%Y-%m-%d').strftime('%d %B %Y') if due_date_raw else (datetime.now() + timedelta(days=7)).strftime('%d %B %Y')
        invoice_number = f"INV{datetime.now().strftime('%Y%m%d')}{random.randint(100,999)}"

        env = Environment(loader=FileSystemLoader(os.path.join(app.root_path, 'templates')))
        template = env.get_template('invoice_pdf_template.html')
        html_out = template.render(
            client=client,
            items=invoice_items,
            subtotal=subtotal,
            vat=vat,
            total=total,
            logo_path=logo_path,
            invoice_date=invoice_date,
            due_date=due_date,
            invoice_number=invoice_number
        )

        pdf = HTML(string=html_out, base_url=app.root_path).write_pdf()
        return send_file(BytesIO(pdf), as_attachment=True, download_name='invoice.pdf', mimetype='application/pdf')
    return render_template('invoice.html')

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
