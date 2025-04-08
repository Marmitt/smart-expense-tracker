from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from collections import defaultdict
from calendar import month_abbr
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    today = date.today()
    current_month_str = request.args.get('month')
    current_month = datetime.strptime(current_month_str, '%Y-%m') if current_month_str else today.replace(day=1)
    
    start_date = current_month.replace(day=1)
    next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_date = next_month - timedelta(days=1)
    prev_month = (start_date - timedelta(days=1)).replace(day=1).strftime('%Y-%m')
    next_month_str = next_month.strftime('%Y-%m')

    incomes = Income.query.filter_by(user_id=user_id).filter(Income.date >= start_date, Income.date <= end_date).all()
    expenses = Expense.query.filter_by(user_id=user_id).filter(Expense.date >= start_date, Expense.date <= end_date).all()
    savings = Saving.query.filter_by(user_id=user_id).filter(Saving.date >= start_date, Saving.date <= end_date).all()
    goals = Goal.query.filter_by(user_id=user_id).all()

    goal_lookup = {(g.name, g.type): g.amount for g in goals}

    income_summary = []
    income_sources = set(i.source for i in incomes)
    for source in income_sources:
        actual = sum(i.amount for i in incomes if i.source == source)
        goal = goal_lookup.get((source, 'income'), 0)
        diff = actual - goal
        sample = next((i for i in incomes if i.source == source), None)
        income_summary.append({
            "id": sample.id if sample else None,
            "label": source,
            "icon": "bi-cash-stack",
            "goal": goal,
            "actual": actual,
            "diff": diff
        })

    expense_summary = []
    expense_categories = set(e.category for e in expenses)
    for category in expense_categories:
        actual = sum(e.amount for e in expenses if e.category == category)
        goal = goal_lookup.get((category, 'expense'), 0)
        diff = goal - actual
        sample = next((e for e in expenses if e.category == category), None)
        expense_summary.append({
            "id": sample.id if sample else None,
            "label": category,
            "icon": "bi-wallet",
            "goal": goal,
            "actual": actual,
            "diff": diff
        })

    income_labels = [i.source for i in incomes]
    income_data = [i.amount for i in incomes]
    expense_labels = [e.category for e in expenses]
    expense_data = [e.amount for e in expenses]
    savings_labels = [s.date.strftime('%b') for s in savings]
    savings_data = [s.amount for s in savings]

    total_income = sum(income_data)
    total_expenses = sum(expense_data)

    # Monthly summary for savings chart
    monthly_income = defaultdict(float)
    monthly_expenses = defaultdict(float)
    for i in Income.query.filter_by(user_id=user_id).all():
        monthly_income[i.date.strftime('%b')] += i.amount
    for e in Expense.query.filter_by(user_id=user_id).all():
        monthly_expenses[e.date.strftime('%b')] += e.amount

    months_order = list(month_abbr)[1:]  # Jan - Dec
    monthly_income_list = [monthly_income[m] for m in months_order]
    monthly_expense_list = [monthly_expenses[m] for m in months_order]
    monthly_savings_list = [monthly_income[m] - monthly_expenses[m] for m in months_order]

    monthly_actual_income = []
    monthly_goal_income = []
    for i in range(1, 13):
        m_start = date(today.year, i, 1)
        m_end = (m_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        m_incomes = Income.query.filter_by(user_id=user_id).filter(Income.date >= m_start, Income.date <= m_end).all()
        actual = sum(i.amount for i in m_incomes)
        goal = sum(goal_lookup.get((i.source, "income"), 0) for i in m_incomes)
        monthly_actual_income.append(actual)
        monthly_goal_income.append(goal)
    
    monthly_actual_expense = []
    monthly_goal_expense = []
    monthly_expense_labels = months_order

    for i in range(12):
        month_start = date(today.year, i + 1, 1)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

        # Get all expenses for the month
        month_expenses = Expense.query.filter_by(user_id=user_id).filter(Expense.date >= month_start, Expense.date <= month_end).all()
        actual = sum(e.amount for e in month_expenses)
        goal = sum(goal_lookup.get((e.category, "expense"), 0) for e in month_expenses)

        monthly_actual_expense.append(actual)
        monthly_goal_expense.append(goal)


    return render_template("index.html",
        income_labels=income_labels,
        income_data=income_data,
        income_summary=income_summary,
        incomeGoal=[item["goal"] for item in income_summary],
        incomeActual=[item["actual"] for item in income_summary],

        expense_labels=expense_labels,
        expense_data=expense_data,
        expense_summary=expense_summary,

        savings_labels=months_order,
        savings_data=savings_data,
        monthly_income=monthly_income_list,
        monthly_expenses=monthly_expense_list,
        monthly_savings=monthly_savings_list,
        monthly_goal_expense=monthly_goal_expense,
        monthly_actual_expense=monthly_actual_expense,
        monthly_expense_labels=monthly_expense_labels,


        monthly_income_labels=months_order,
        monthly_actual_income=monthly_actual_income,
        monthly_goal_income=monthly_goal_income,

        budget=total_income,
        total=total_expenses,
        remaining=total_income - total_expenses,
        planner_data=[],
        expenses=expenses,
        current_month=current_month,
        prev_month=prev_month,
        next_month=next_month_str
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'], password=request.form['password']).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if not User.query.filter_by(username=request.form['username']).first():
            user = User(username=request.form['username'], password=request.form['password'])
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/add_income', methods=['POST'])
def add_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    date_str = request.form['date']
    income_date = datetime.strptime(date_str, '%Y-%m-%d')
    new_income = Income(user_id=session['user_id'], source=request.form['source'], amount=float(request.form['amount']), date=income_date)
    db.session.add(new_income)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    new_expense = Expense(user_id=session['user_id'], category=request.form['category'], amount=float(request.form['amount']), date=date)
    db.session.add(new_expense)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_savings', methods=['POST'])
def add_savings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db.session.add(Saving(user_id=session['user_id'], amount=float(request.form['amount'])))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_income', methods=['POST'])
def edit_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    income = Income.query.filter_by(id=request.form['income_id'], user_id=session['user_id']).first()
    if income:
        income.amount = float(request.form['amount'])
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_expense', methods=['POST'])
def edit_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.filter_by(id=request.form['expense_id'], user_id=session['user_id']).first()
    if expense:
        expense.amount = float(request.form['amount'])
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/set_goal', methods=['POST'])
def set_goal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    name = request.form['name']
    goal_type = request.form['type']
    amount = float(request.form['amount'])
    goal = Goal.query.filter_by(user_id=user_id, name=name, type=goal_type).first()
    if goal:
        goal.amount = amount
    else:
        goal = Goal(user_id=user_id, name=name, type=goal_type, amount=amount)
        db.session.add(goal)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_income/<int:income_id>', methods=['POST'])
def delete_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    income = Income.query.get_or_404(income_id)
    if income.user_id == session['user_id']:
        db.session.delete(income)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id == session['user_id']:
        db.session.delete(expense)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
