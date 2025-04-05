from flask import Flask, render_template, request, redirect
import pandas as pd
import os

app = Flask(__name__)
DATA_FILE = 'data/expenses.csv'

# Make sure CSV exists
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Date", "Category", "Description", "Amount"])
    df.to_csv(DATA_FILE, index=False)

@app.route("/")
def index():
    df = pd.read_csv(DATA_FILE)
    total = df["Amount"].sum()
    grouped = df.groupby("Category")["Amount"].sum().to_dict()
    return render_template("index.html", expenses=df.to_dict(orient="records"), total=total, grouped=grouped)

@app.route("/add", methods=["POST"])
def add():
    new_expense = {
        "Date": request.form["date"],
        "Category": request.form["category"],
        "Description": request.form["description"],
        "Amount": float(request.form["amount"])
    }

    df = pd.read_csv(DATA_FILE)
    df = pd.concat([df, pd.DataFrame([new_expense])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    return redirect("/")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    if file and file.filename.endswith(".csv"):
        uploaded_df = pd.read_csv(file)
        current_df = pd.read_csv(DATA_FILE)
        combined_df = pd.concat([current_df, uploaded_df], ignore_index=True)
        combined_df.to_csv(DATA_FILE, index=False)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
