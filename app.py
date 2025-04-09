from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from collections import defaultdict
from calendar import month_abbr
import os
import sqlalchemy as sa


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    source = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)

class Saving(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, default=0.0)

# Check if at least one table exists, and create all if not
def initialize_tables():
    engine = sa.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    inspector = sa.inspect(engine)
    if not inspector.has_table("user"):  # You can check for any known table
        with app.app_context():
            db.create_all()
            print("✅ Tables created in the database.")

initialize_tables()

@app.route('/')
def index():
    user_id = session.get('user_id')
    today = date.today()
    current_month_str = request.args.get('month')
    current_month = datetime.strptime(current_month_str, '%Y-%m') if current_month_str else today.replace(day=1)

    start_date = current_month.replace(day=1)
    next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_date = next_month - timedelta(days=1)
    prev_month = (start_date - timedelta(days=1)).replace(day=1).strftime('%Y-%m')
    next_month_str = next_month.strftime('%Y-%m')

    incomes, expenses, savings, goals = [], [], [], []
    if user_id:
        incomes = Income.query.filter_by(user_id=user_id).filter(Income.date >= start_date, Income.date <= end_date).all()
        expenses = Expense.query.filter_by(user_id=user_id).filter(Expense.date >= start_date, Expense.date <= end_date).all()
        savings = Saving.query.filter_by(user_id=user_id).filter(Saving.date >= start_date, Saving.date <= end_date).all()
        goals = Goal.query.filter_by(user_id=user_id).all()

    goal_lookup = {(g.name, g.type): g.amount for g in goals}

    income_summary = []
    for source in set(i.source for i in incomes):
        actual = sum(i.amount for i in incomes if i.source == source)
        goal = goal_lookup.get((source, 'income'), 0)
        sample_income = next((i for i in incomes if i.source == source), None)
        income_summary.append({
            "id": sample_income.id if sample_income else None,
            "label": source,
            "icon": "bi-cash-stack",
            "goal": goal,
            "actual": actual,
            "diff": actual - goal
        })

    expense_summary = []
    for category in set(e.category for e in expenses):
        actual = sum(e.amount for e in expenses if e.category == category)
        goal = goal_lookup.get((category, 'expense'), 0)
        sample_expense = next((e for e in expenses if e.category == category), None)
        expense_summary.append({
            "id": sample_expense.id if sample_expense else None,
            "label": category,
            "icon": "bi-wallet",
            "goal": goal,
            "actual": actual,
            "diff": goal - actual
        })

    income_data = [i.amount for i in incomes]
    expense_data = [e.amount for e in expenses]

    total_income = sum(income_data)
    total_expenses = sum(expense_data)

    monthly_income, monthly_expenses = defaultdict(float), defaultdict(float)
    for i in Income.query.filter_by(user_id=user_id).all():
        monthly_income[i.date.strftime('%b')] += i.amount
    for e in Expense.query.filter_by(user_id=user_id).all():
        monthly_expenses[e.date.strftime('%b')] += e.amount

    months_order = list(month_abbr)[1:]
    monthly_income_list = [monthly_income[m] for m in months_order]
    monthly_expense_list = [monthly_expenses[m] for m in months_order]
    monthly_savings_list = [i - e for i, e in zip(monthly_income_list, monthly_expense_list)]

    monthly_labels = months_order
    monthly_actual_income = []
    monthly_goal_income = []
    for i in range(12):
        month_start = date(today.year, i + 1, 1)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        month_incomes = Income.query.filter_by(user_id=user_id).filter(Income.date >= month_start, Income.date <= month_end).all()
        actual = sum(i.amount for i in month_incomes)
        goal = sum(goal_lookup.get((i.source, "income"), 0) for i in month_incomes)
        monthly_actual_income.append(actual)
        monthly_goal_income.append(goal)

    return render_template("index.html",
        income_labels=[i.source for i in incomes],
        income_data=income_data,
        expense_labels=[e.category for e in expenses],
        expense_data=expense_data,
        savings_labels=months_order,
        savings_data=monthly_savings_list,
        monthly_income=monthly_income_list,
        monthly_expenses=monthly_expense_list,
        monthly_savings=monthly_savings_list,
        budget=total_income,
        total=total_expenses,
        remaining=total_income - total_expenses,
        planner_data=[],
        expenses=expenses,
        income_summary=income_summary,
        expense_summary=expense_summary,
        current_month=current_month,
        prev_month=prev_month,
        next_month=next_month_str,
        monthly_income_labels=monthly_labels,
        monthly_expense_labels=monthly_labels,
        monthly_actual_income=monthly_actual_income,
        monthly_goal_income=monthly_goal_income
    )

# Auth Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if not User.query.filter_by(username=request.form['username']).first():
            hashed_pw = generate_password_hash(request.form['password'])
            user = User(username=request.form['username'], password=hashed_pw)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

# Budget Routes
@app.route('/set_goal', methods=['POST'])
def set_goal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    goal = Goal.query.filter_by(user_id=session['user_id'], name=request.form['name'], type=request.form['type']).first()
    amount = float(request.form['amount'])
    if goal:
        goal.amount = amount
    else:
        goal = Goal(user_id=session['user_id'], name=request.form['name'], type=request.form['type'], amount=amount)
        db.session.add(goal)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_income', methods=['POST'])
def add_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db.session.add(Income(
        user_id=session['user_id'],
        source=request.form['source'],
        amount=float(request.form['amount']),
        date=datetime.strptime(request.form['date'], '%Y-%m-%d')
    ))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db.session.add(Expense(
        user_id=session['user_id'],
        category=request.form['category'],
        amount=float(request.form['amount']),
        date=datetime.strptime(request.form['date'], '%Y-%m-%d')
    ))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_income', methods=['POST'])
def edit_income():
    income = Income.query.filter_by(id=request.form['income_id'], user_id=session['user_id']).first()
    if income:
        income.amount = float(request.form['amount'])
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_expense', methods=['POST'])
def edit_expense():
    expense = Expense.query.filter_by(id=request.form['expense_id'], user_id=session['user_id']).first()
    if expense:
        expense.amount = float(request.form['amount'])
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_income/<int:income_id>', methods=['POST'])
def delete_income(income_id):
    income = Income.query.get_or_404(income_id)
    if income.user_id == session['user_id']:
        db.session.delete(income)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id == session['user_id']:
        db.session.delete(expense)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
