from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from sqlalchemy import select
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "finora-dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finora.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Сначала войдите в аккаунт."


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    transactions = db.relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    transactions = db.relationship("Transaction", back_populates="category")


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    user = db.relationship("User", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def seed_categories():
    if db.session.scalar(select(Category.id).limit(1)) is None:
        db.session.add_all([Category(name=name) for name in ["Зарплата", "Еда", "Транспорт", "Покупки", "Развлечения", "Другое"]])
        db.session.commit()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Заполните все поля.", "warning")
        elif User.query.filter_by(username=username).first():
            flash("Пользователь уже существует.", "warning")
        else:
            user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(user); db.session.commit(); login_user(user)
            flash("Регистрация прошла успешно.", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user); flash("Вы вошли.", "success"); return redirect(url_for("dashboard"))
        flash("Неверные данные.", "warning")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user(); flash("Вы вышли.", "success"); return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.transaction_date.desc()).all()
    return render_template("dashboard.html", transactions=transactions)


@app.route("/transactions")
@login_required
def transactions():
    items = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.transaction_date.desc()).all()
    return render_template("transactions.html", transactions=items)


@app.route("/transaction/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount_text = request.form.get("amount", "").replace(",", ".")
        transaction_type = request.form.get("transaction_type", "")
        date_text = request.form.get("transaction_date", "")
        category_id = request.form.get("category_id") or None
        try:
            amount = Decimal(amount_text)
            transaction_date = date.fromisoformat(date_text)
        except (InvalidOperation, ValueError):
            flash("Проверьте сумму и дату.", "warning")
            return render_template("add_transaction.html", categories=categories)
        if not title or amount <= 0 or transaction_type not in {"income", "expense"}:
            flash("Проверьте введённые данные.", "warning")
            return render_template("add_transaction.html", categories=categories)
        item = Transaction(title=title, amount=amount, transaction_type=transaction_type, transaction_date=transaction_date, user_id=current_user.id, category_id=int(category_id) if category_id else None)
        db.session.add(item); db.session.commit()
        flash("Операция добавлена.", "success")
        return redirect(url_for("transactions"))
    return render_template("add_transaction.html", categories=categories)


with app.app_context():
    db.create_all()
    seed_categories()


if __name__ == "__main__":
    app.run(debug=True)
