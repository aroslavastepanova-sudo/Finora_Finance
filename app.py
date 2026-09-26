from datetime import datetime, date
from decimal import Decimal

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()
login_manager = LoginManager()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    profile = db.relationship(
        "Profile", back_populates="user", uselist=False,
        cascade="all, delete-orphan"
    )
    transactions = db.relationship(
        "Transaction", back_populates="user",
        cascade="all, delete-orphan"
    )
    categories = db.relationship(
        "Category", back_populates="user",
        cascade="all, delete-orphan"
    )
    tags = db.relationship(
        "Tag", back_populates="user",
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        # Werkzeug uses a salted password hash; the salt is stored as part of the hash.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)


class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(30), nullable=True)
    currency = db.Column(db.String(10), default="RUB", nullable=False)
    monthly_goal = db.Column(db.Numeric(12, 2), default=0, nullable=False)

    user = db.relationship("User", back_populates="profile")


transaction_tags = db.Table(
    "transaction_tags",
    db.Column("transaction_id", db.Integer, db.ForeignKey("transactions.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    icon = db.Column(db.String(10), default="•", nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", back_populates="categories")
    transactions = db.relationship("Transaction", back_populates="category")


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", back_populates="tags")
    transactions = db.relationship(
        "Transaction", secondary=transaction_tags, back_populates="tags"
    )


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # income / expense
    transaction_date = db.Column(db.Date, nullable=False, default=date.today)
    note = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    user = db.relationship("User", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")
    tags = db.relationship(
        "Tag", secondary=transaction_tags, back_populates="transactions"
    )

    @property
    def signed_amount(self):
        return self.amount if self.transaction_type == "income" else -self.amount


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = "change-this-secret-key-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finora.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = "Войдите в аккаунт, чтобы продолжить."
    login_manager.login_message_category = "info"

    @app.context_processor
    def inject_helpers():
        return {
            "currency_symbol": lambda code: {"RUB": "₽", "USD": "$", "EUR": "€", "GBP": "£"}.get(code, code),
        }

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            password_repeat = request.form.get("password_repeat", "")

            if not name or not email or not password:
                flash("Заполните все обязательные поля.", "error")
                return render_template("auth/register.html")

            if password != password_repeat:
                flash("Пароли не совпадают.", "error")
                return render_template("auth/register.html")

            if len(password) < 6:
                flash("Пароль должен содержать минимум 6 символов.", "error")
                return render_template("auth/register.html")

            if User.query.filter_by(email=email).first():
                flash("Пользователь с такой почтой уже существует.", "error")
                return render_template("auth/register.html")

            user = User(name=name, email=email)
            user.set_password(password)

            db.session.add(user)
            db.session.flush()

            user.profile = Profile(currency="RUB")
            default_categories = [
                ("Продукты", "⌁"), ("Кафе", "☕"), ("Транспорт", "⌁"),
                ("Жильё", "⌂"), ("Развлечения", "♡"), ("Зарплата", "↗"),
            ]
            for category_name, icon in default_categories:
                db.session.add(Category(name=category_name, icon=icon, user=user))

            db.session.commit()
            login_user(user)
            flash("Добро пожаловать в Finora!", "success")
            return redirect(url_for("dashboard"))

        return render_template("auth/register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard"))

            flash("Неверная почта или пароль.", "error")

        return render_template("auth/login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Вы вышли из аккаунта.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        income = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "income"
        ).scalar() or 0

        expenses = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense"
        ).scalar() or 0

        recent = Transaction.query.filter_by(user_id=current_user.id).order_by(
            Transaction.transaction_date.desc(), Transaction.id.desc()
        ).limit(6).all()

        expense_rows = db.session.query(
            Category.name,
            func.coalesce(func.sum(Transaction.amount), 0).label("total")
        ).join(Transaction, Transaction.category_id == Category.id).filter(
            Category.user_id == current_user.id,
            Transaction.transaction_type == "expense"
        ).group_by(Category.id).order_by(func.sum(Transaction.amount).desc()).all()

        total_expenses = Decimal(str(expenses))
        category_stats = []
        for name, total in expense_rows:
            value = Decimal(str(total))
            percent = float((value / total_expenses * 100) if total_expenses else 0)
            category_stats.append({"name": name, "total": value, "percent": round(percent)})

        balance = Decimal(str(income)) - Decimal(str(expenses))
        return render_template(
            "dashboard.html",
            balance=balance,
            income=Decimal(str(income)),
            expenses=Decimal(str(expenses)),
            recent=recent,
            category_stats=category_stats,
        )

    @app.route("/transactions")
    @login_required
    def transactions():
        # GET parameters are used for search/filtering as required by the assignment.
        search = request.args.get("search", "").strip()
        transaction_type = request.args.get("type", "").strip()
        category_id = request.args.get("category", "").strip()

        query = Transaction.query.filter_by(user_id=current_user.id)

        if search:
            query = query.filter(Transaction.title.ilike(f"%{search}%"))
        if transaction_type in {"income", "expense"}:
            query = query.filter_by(transaction_type=transaction_type)
        if category_id.isdigit():
            query = query.filter_by(category_id=int(category_id))

        transactions_list = query.order_by(
            Transaction.transaction_date.desc(), Transaction.id.desc()
        ).all()

        categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()

        return render_template(
            "transactions/list.html",
            transactions=transactions_list,
            categories=categories,
            search=search,
            selected_type=transaction_type,
            selected_category=category_id,
        )

    @app.route("/transactions/add", methods=["GET", "POST"])
    @login_required
    def add_transaction():
        categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            amount_raw = request.form.get("amount", "").replace(",", ".").strip()
            transaction_type = request.form.get("transaction_type", "").strip()
            transaction_date = request.form.get("transaction_date", "").strip()
            category_id = request.form.get("category_id", "").strip()
            note = request.form.get("note", "").strip()

            if not title or not amount_raw or transaction_type not in {"income", "expense"}:
                flash("Заполните название, сумму и тип операции.", "error")
                return render_template("transactions/form.html", categories=categories)

            try:
                amount = Decimal(amount_raw)
                parsed_date = datetime.strptime(transaction_date, "%Y-%m-%d").date()
                category = Category.query.filter_by(
                    id=int(category_id), user_id=current_user.id
                ).first()
                if amount <= 0 or not category:
                    raise ValueError
            except (ValueError, ArithmeticError):
                flash("Проверьте сумму, дату и категорию.", "error")
                return render_template("transactions/form.html", categories=categories)

            transaction = Transaction(
                title=title,
                amount=amount,
                transaction_type=transaction_type,
                transaction_date=parsed_date,
                note=note,
                user_id=current_user.id,
                category_id=category.id,
            )
            db.session.add(transaction)
            db.session.commit()
            flash("Операция добавлена.", "success")
            return redirect(url_for("transactions"))

        return render_template("transactions/form.html", categories=categories)

    @app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
    @login_required
    def delete_transaction(transaction_id):
        transaction = Transaction.query.filter_by(
            id=transaction_id, user_id=current_user.id
        ).first_or_404()
        db.session.delete(transaction)
        db.session.commit()
        flash("Операция удалена.", "success")
        return redirect(url_for("transactions"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        profile_obj = current_user.profile

        if request.method == "POST":
            current_user.name = request.form.get("name", "").strip() or current_user.name
            profile_obj.gender = request.form.get("gender", "").strip() or None
            profile_obj.currency = request.form.get("currency", "RUB").strip()
            goal_raw = request.form.get("monthly_goal", "0").replace(",", ".").strip()

            try:
                profile_obj.monthly_goal = Decimal(goal_raw or "0")
                if profile_obj.monthly_goal < 0:
                    raise ValueError
            except (ValueError, ArithmeticError):
                flash("Некорректная сумма финансовой цели.", "error")
                return render_template("profile/profile.html")

            birth_date_raw = request.form.get("birth_date", "").strip()
            if birth_date_raw:
                try:
                    profile_obj.birth_date = datetime.strptime(birth_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    flash("Проверьте дату рождения.", "error")
                    return render_template("profile/profile.html")
            else:
                profile_obj.birth_date = None

            db.session.commit()
            flash("Профиль сохранён.", "success")
            return redirect(url_for("profile"))

        return render_template("profile/profile.html")

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
