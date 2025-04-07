from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
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
    description = db.Column(db.String(255))
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
    type = db.Column(db.String(50), nullable=False)  # 'income' or 'expense'
    amount = db.Column(db.Float, default=0.0)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expense.query.filter_by(user_id=user_id).all()
    savings = Saving.query.filter_by(user_id=user_id).all()
    goals = Goal.query.filter_by(user_id=user_id).all()
    
    goal_lookup = {(g.name, g.type): g.amount for g in goals}

    income_summary = []
    income_sources = set(i.source for i in incomes)
    for source in income_sources:
        actual = sum(i.amount for i in incomes if i.source == source)
        goal = goal_lookup.get((source, 'income'), 0)
        diff = actual - goal
        income_summary.append({
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
        diff = actual - goal
        expense_summary.append({
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

    return render_template(
        'index.html',
        income_labels=income_labels,
        income_data=income_data,
        expense_labels=expense_labels,
        expense_data=expense_data,
        savings_labels=savings_labels,
        savings_data=savings_data,
        budget=total_income,
        total=total_expenses,
        remaining=total_income - total_expenses,
        planner_data=[],
        expenses=expenses,
        income_summary=income_summary,
        expense_summary=expense_summary
    )

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
        new_goal = Goal(user_id=user_id, name=name, type=goal_type, amount=amount)
        db.session.add(new_goal)
    db.session.commit()
    return redirect(url_for('index'))

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
    source = request.form['source']
    amount = float(request.form['amount'])
    db.session.add(Income(user_id=session['user_id'], source=source, amount=amount))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db.session.add(Expense(
        user_id=session['user_id'],
        date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
        category=request.form['category'],
        description=request.form['description'],
        amount=float(request.form['amount'])
    ))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_savings', methods=['POST'])
def add_savings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db.session.add(Saving(user_id=session['user_id'], amount=float(request.form['amount'])))
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)