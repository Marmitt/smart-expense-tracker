from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime, timedelta
import database  # local database helper

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

@app.before_request
def require_login():
    allowed = ["login", "register", "static"]
    if request.endpoint not in allowed and "user_id" not in session:
        return redirect("/login")

@app.route("/")
def index():
    user_id = session["user_id"]
    path = f"data/user_{user_id}_expenses.csv"
    df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["Date", "Category", "Description", "Amount"])
    df["Date"] = pd.to_datetime(df["Date"])
    filter_type = request.args.get("filter", "all")
    now = datetime.now()

    if filter_type == "month":
        df = df[df["Date"].dt.month == now.month]
    elif filter_type == "week":
        start = now - timedelta(days=now.weekday())
        end = start + timedelta(days=6)
        df = df[(df["Date"] >= start) & (df["Date"] <= end)]
    elif filter_type == "fortnight":
        start = now - timedelta(days=13)
        df = df[df["Date"] >= start]

    total = df["Amount"].sum()
    grouped = df.groupby("Category")["Amount"].sum()
    chart_labels = grouped.index.tolist()
    chart_data = grouped.values.tolist()

    return render_template("index.html", expenses=df.to_dict(orient="records"), total=total, grouped=grouped, chart_labels=chart_labels, chart_data=chart_data, selected_filter=filter_type)

@app.route("/add", methods=["POST"])
def add():
    user_id = session["user_id"]
    new = {
        "Date": request.form["date"],
        "Category": request.form["category"],
        "Description": request.form["description"],
        "Amount": float(request.form["amount"])
    }
    path = f"data/user_{user_id}_expenses.csv"
    df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["Date", "Category", "Description", "Amount"])
    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
    df.to_csv(path, index=False)
    return redirect("/")

@app.route("/upload", methods=["POST"])
def upload():
    user_id = session["user_id"]
    file = request.files["file"]
    path = f"data/user_{user_id}_expenses.csv"
    if file and file.filename.endswith(".csv"):
        new_df = pd.read_csv(file)
        current_df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["Date", "Category", "Description", "Amount"])
        combined = pd.concat([current_df, new_df], ignore_index=True)
        combined.to_csv(path, index=False)
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if database.create_user(username, password):
            return redirect("/login")
        return "Username already taken"
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user_id = database.validate_user(username, password)
        if user_id:
            session["user_id"] = user_id
            return redirect("/")
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
