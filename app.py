from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from forms.expense_form import ExpenseForm
from models.models import db, Expense, Category, User
from flask_login import (
    LoginManager,
    login_required,
    login_user,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # povolit HTTP pro OAuth při vývoji
from datetime import date
from io import StringIO
from flask import make_response
from io import BytesIO
from flask import send_file
from flask import render_template 
from collections import defaultdict
import csv
import pandas as pd
import json
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klic'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'expenses.db')}"
db.init_app(app)

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'index'

# OAuth setup
google_bp = make_google_blueprint(
    client_id=os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
    scope=[
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid"
    ],
    redirect_url="/login"
)
app.register_blueprint(google_bp, url_prefix='/login')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login')
def login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    resp = google.get('/oauth2/v2/userinfo')
    if resp.ok:
        info = resp.json()
        user = User.query.filter_by(email=info['email']).first()
        if not user:
            user = User(email=info['email'], name=info.get('name'))
            db.session.add(user)
            db.session.commit()
        login_user(user)
    return redirect(url_for('dashboard'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_screen'))


# Nová route pro přihlašovací obrazovku
@app.route('/login-screen')
def login_screen():
    return render_template('login_screen.html')

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin').first():
        admin = User(email='admin', name='Admin')
        admin.password_hash = generate_password_hash('admin')
        db.session.add(admin)
        db.session.commit()


@app.route('/new', methods=['GET', 'POST'])
@login_required
def new_expense():
    form = ExpenseForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    if form.validate_on_submit():
        new = Expense(
            name=form.name.data,
            amount=float(form.amount.data),
            category=form.category.data,
            date=form.date.data
        )
        db.session.add(new)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('new_expense.html', form=form)


@app.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('dashboard'))

# Nová route pro editaci výdaje
@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    form = ExpenseForm(obj=expense)
    form.category.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

    if form.validate_on_submit():
        expense.name = form.name.data
        expense.amount = float(form.amount.data)
        expense.category = form.category.data
        expense.date = form.date.data
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('edit_expense.html', form=form)

@app.route('/settings', methods=['GET'])
@login_required
def settings():
    sekce = request.args.get('sekce', 'kategorie')
    categories = Category.query.order_by(Category.name).all()
    return render_template('settings.html', categories=categories, sekce=sekce)

@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if name:
        existing = Category.query.filter_by(name=name).first()
        if not existing:
            new_cat = Category(name=name)
            db.session.add(new_cat)
            db.session.commit()
    return redirect(url_for('settings'))

@app.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    cat = Category.query.get_or_404(category_id)
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for('settings'))

@app.route('/export/csv')
@login_required
def export_csv():
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Název', 'Částka', 'Kategorie', 'Datum'])

    for e in Expense.query.all():
        cw.writerow([e.name, e.amount, e.category_obj.name, e.date.strftime('%Y-%m-%d')])

    response = make_response('\ufeff' + si.getvalue())  # BOM prefix
    response.headers["Content-Disposition"] = "attachment; filename=vydaje.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response

@app.route('/export/excel')
@login_required
def export_excel():
    data = [{
        'Název': e.name,
        'Částka': e.amount,
        'Kategorie': e.category_obj.name,
        'Datum': e.date.strftime('%Y-%m-%d')
    } for e in Expense.query.all()]

    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True,
                     download_name="vydaje.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# Route for classic login (admin/admin)
@app.route('/login-user', methods=['POST'])
def login_user_local():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('index'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login_screen.html')

@app.route('/dashboard')
@login_required
def dashboard():
    name_filter = request.args.get('name')
    amount_filter = request.args.get('amount')
    selected_categories = request.args.getlist('categories')
    date_filter = request.args.get('date')
    query = Expense.query

    if name_filter:
        query = query.filter(Expense.name.ilike(f"%{name_filter}%"))
    if amount_filter:
        try:
            query = query.filter(Expense.amount == float(amount_filter))
        except ValueError:
            pass  # ignoruj neplatné číslo
    if selected_categories:
        query = query.join(Category).filter(Category.name.in_(selected_categories))
    if date_filter:
        query = query.filter(Expense.date.like(f"%{date_filter}%"))

    expenses = query.order_by(Expense.date.desc()).limit(50).all()
    total = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    categories = Category.query.order_by(Category.name).all()

    # 💡 Výpočty pro koláčový graf
    summary = defaultdict(float)
    for e in expenses:
        summary[e.category_obj.name] += e.amount

    chart_labels = list(summary.keys())
    chart_values = list(summary.values())

    return render_template(
        'dashboard.html',
        expenses=expenses,
        total_expenses=total,
        categories=categories,
        chart_labels=json.dumps(chart_labels, ensure_ascii=False),
        chart_values=json.dumps(chart_values)
    )

@app.route('/update_password', methods=['POST'])
@login_required
def update_password():
    current = request.form.get('current_password')
    new = request.form.get('new_password')
    confirm = request.form.get('confirm_password')

    if not check_password_hash(current_user.password_hash, current):
        return "Aktuální heslo je nesprávné", 400
    if new != confirm:
        return "Hesla se neshodují", 400

    current_user.password_hash = generate_password_hash(new)
    db.session.commit()
    return redirect(url_for('settings', sekce='uzivatel'))

if __name__ == '__main__':
    app.run(debug=True)