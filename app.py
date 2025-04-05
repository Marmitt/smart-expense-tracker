from flask import Flask, render_template, request, redirect
import pandas as pd
import os
from datetime import datetime, timedelta

app = Flask(__name__)
DATA_FILE = 'data/expenses.csv'

# Create the file if it doesn't exist
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=["Date", "Category", "Description", "Amount"]).to_csv(DATA_FILE, index=False)

@app.route("/")
def index():
    df = pd.read_csv(DATA_FILE)
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

    return render_template(
        "index.html",
        expenses=df.to_dict(orient="records"),
        total=total,
        grouped=grouped,
        chart_labels=chart_labels,
        chart_data=chart_data,
        selected_filter=filter_type
    )

@app.route("/add", methods=["POST"])
def add():
    new = {
        "Date": request.form["date"],
        "Category": request.form["category"],
        "Description": request.form["description"],
        "Amount": float(request.form["amount"])
    }
    df = pd.read_csv(DATA_FILE)
    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    return redirect("/")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    if file and file.filename.endswith(".csv"):
        new_df = pd.read_csv(file)
        current_df = pd.read_csv(DATA_FILE)
        combined = pd.concat([current_df, new_df], ignore_index=True)
        combined.to_csv(DATA_FILE, index=False)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
