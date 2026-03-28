from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func
import os
from datetime import datetime

app = Flask(__name__)

# DB CONFIG
db_url = os.getenv('DATABASE_URL')

if not db_url:
    raise ValueError("DATABASE_URL not set")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.secret_key = os.getenv("SECRET_KEY", "dev")

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# MODELS
class User(db.Model):
    __tablename__ = 'user_data'

    username = db.Column(db.String(100), nullable=False)
    email_id = db.Column(db.String(200), primary_key=True)
    password = db.Column(db.Text, nullable=False)

    expenses = db.relationship('Expenses', backref='user', lazy=True)


class Expenses(db.Model):
    __tablename__ = 'user_expenses'

    expense_id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.String(200), db.ForeignKey('user_data.email_id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    expense_name = db.Column(db.String(100), nullable=False)
    expense_amount = db.Column(db.Integer, nullable=False)


# ROUTES
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        delete_instruction = request.form.get("delete_button")

        # DELETE
        if delete_instruction:
            expense = Expenses.query.filter_by(
                expense_id=int(delete_instruction),
                email_id=session['user']
            ).first()

            if expense:
                db.session.delete(expense)
                db.session.commit()

            return redirect(url_for("dashboard"))

        # ADD
        expense_name = request.form.get("expense")
        expense_amount = request.form.get("amount")
        expense_date = request.form.get("date")
        expense_category = request.form.get("category")

        if expense_name and expense_amount and expense_date and expense_category:
            new_expense = Expenses(
                email_id=session['user'],
                date=datetime.strptime(expense_date, "%Y-%m-%d").date(),
                expense_name=expense_name,
                expense_amount=int(expense_amount),
                category=expense_category
            )

            db.session.add(new_expense)
            db.session.commit()

        return redirect(url_for("dashboard"))

    user_expenses = Expenses.query.filter_by(email_id=session['user']).all()
    return render_template("dashboard.html", expenses=user_expenses)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email_id=email).first()

        if user and check_password_hash(user.password, password):
            session['user'] = email
            return redirect(url_for("dashboard"))

        return render_template("login.html", alert_messege="Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/logup", methods=["GET", "POST"])
def logup():
    if request.method == "POST":
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))
        username = request.form.get("username")

        if User.query.filter_by(email_id=email).first():
            return render_template("login.html", alert_messege="Email already exists")

        new_user = User(username=username, email_id=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("logup.html")


@app.route("/analytics")
def analytics():
    return render_template("analytics.html")


# API: ALL DATA
@app.route("/api/v1/analytics", methods=['POST'])
def get_all_data_between_dates():
    starting_date = datetime.strptime(request.form.get('starting_date'), "%Y-%m-%d").date()
    ending_date = datetime.strptime(request.form.get('ending_date'), "%Y-%m-%d").date()

    data = Expenses.query.filter(
        Expenses.date >= starting_date,
        Expenses.date <= ending_date,
        Expenses.email_id == session['user']
    ).all()

    return jsonify([
        {
            "category": e.category,
            "expense_name": e.expense_name,
            "expense_amount": e.expense_amount,
            "date": e.date.strftime("%Y-%m-%d")
        }
        for e in data
    ])


# API: CATEGORY SUM
@app.route("/api/v1/category_expenses", methods=['POST'])
def get_amount_between_dates():
    starting_date = datetime.strptime(request.form.get('starting_date'), "%Y-%m-%d").date()
    ending_date = datetime.strptime(request.form.get('ending_date'), "%Y-%m-%d").date()

    result = db.session.query(
        Expenses.category,
        func.sum(Expenses.expense_amount)
    ).filter(
        Expenses.date >= starting_date,
        Expenses.date <= ending_date,
        Expenses.email_id == session['user']
    ).group_by(Expenses.category).all()

    return jsonify([
        {"category": r[0], "total": r[1]}
        for r in result
    ])


if __name__ == "__main__":
    app.run(debug=True)