from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from forms.expense_form import ExpenseForm
from models.models import db, Expense, Category
from datetime import date

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klic'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    category_filter = request.args.get('category', type=int)
    month_filter = request.args.get('month', type=int)
    query = Expense.query

    if category_filter:
        query = query.filter(Expense.category == category_filter)
    if month_filter:
        query = query.filter(db.extract('month', Expense.date) == month_filter)

    expenses = query.order_by(Expense.date.desc()).limit(50).all()
    total = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    categories = Category.query.order_by(Category.name).all()
    return render_template('dashboard.html', expenses=expenses, total_expenses=total, categories=categories)

@app.route('/new', methods=['GET', 'POST'])
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
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET'])
def settings():
    categories = Category.query.order_by(Category.name).all()
    return render_template('settings.html', categories=categories)

@app.route('/add_category', methods=['POST'])
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
def delete_category(category_id):
    cat = Category.query.get_or_404(category_id)
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for('settings'))

if __name__ == '__main__':
    app.run(debug=True)