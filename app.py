from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from forms.expense_form import ExpenseForm
from models.models import db, Expense
from datetime import date

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klic'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    expenses = Expense.query.order_by(Expense.date.desc()).limit(5).all()
    total = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    return render_template('dashboard.html', expenses=expenses, total_expenses=total)

@app.route('/new', methods=['GET', 'POST'])
def new_expense():
    form = ExpenseForm()
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

if __name__ == '__main__':
    app.run(debug=True)