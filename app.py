# Импортируем класс datetime (для работы с датой/временем) и date (для дат)
from datetime import datetime, date
# Импортируем Decimal для точной работы с денежными суммами (без ошибок округления float)
from decimal import Decimal

# Импортируем Flask и вспомогательные функции: render_template (рендер HTML), request (данные запроса),
# redirect (перенаправление), url_for (генерация URL), flash (всплывающие сообщения)
from flask import Flask, render_template, request, redirect, url_for, flash
# Импортируем инструменты Flask-Login: LoginManager (менеджер входа),
# UserMixin (миксин для модели пользователя), login_user/logout_user (вход/выход),
# login_required (декоратор защиты), current_user (текущий пользователь)
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# Импортируем SQLAlchemy для ORM (работа с БД через Python-объекты)
from flask_sqlalchemy import SQLAlchemy
# Импортируем func для SQL-функций
from sqlalchemy import func
# Импортируем функции хеширования и проверки пароля
from werkzeug.security import generate_password_hash, check_password_hash

# Создаём глобальный объект БД (инициализируется позже в create_app)
db = SQLAlchemy()
# Создаём глобальный менеджер логина
login_manager = LoginManager()


# Модель пользователя. Наследует UserMixin (базовые методы Flask-Login) и db.Model (ORM-модель)
class User(UserMixin, db.Model):
    # Имя таблицы 
    __tablename__ = "users"

    # Первичный ключ(целое)
    id = db.Column(db.Integer, primary_key=True)
    # Имя пользователя (строка до 80 символов, обязательное)
    name = db.Column(db.String(80), nullable=False)
    # Email: уникальный, обязательный, строка до 120 символов)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    # Хеш пароля (никогда не храним пароль в открытом виде)
    password_hash = db.Column(db.String(255), nullable=False)
    # Дата создания записи (по умолчанию — текущее UTC-время)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Связь один-к-одному с профилем (uselist=False), с каскадным удалением
    profile = db.relationship(
        "Profile", back_populates="user", uselist=False,
        cascade="all, delete-orphan"
    )
    # Связь один-ко-многим с транзакциями, каскадное удаление
    transactions = db.relationship(
        "Transaction", back_populates="user",
        cascade="all, delete-orphan"
    )
    # Связь один-ко-многим с категориями, каскадное удаление
    categories = db.relationship(
        "Category", back_populates="user",
        cascade="all, delete-orphan"
    )
    # Связь один-ко-многим с тегами, каскадное удаление
    tags = db.relationship(
        "Tag", back_populates="user",
        cascade="all, delete-orphan"
    )

    # Метод установки пароля: хеширует и сохраняет
    def set_password(self, password):
        # Генерируем хеш из пароля и сохраняем его
        self.password_hash = generate_password_hash(password)

    # Метод проверки пароля: сравнивает введённый пароль с хешем
    def check_password(self, password):
        # Возвращает True, если пароль верный
        return check_password_hash(self.password_hash, password)

    # Возвращает ID пользователя в виде строки (требование Flask-Login)
    def get_id(self):
        return str(self.id)


# Модель профиля пользователя (дополнительные данные)
class Profile(db.Model):
    # Имя таблицы
    __tablename__ = "profiles"

    # Первичный ключ
    id = db.Column(db.Integer, primary_key=True)
    # Внешний ключ на users.id, уникальный (один профиль — один пользователь)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    # Дата рождения (может быть пустой)
    birth_date = db.Column(db.Date, nullable=True)
    # Пол (может быть пустой)
    gender = db.Column(db.String(30), nullable=True)
    # Валюта пользователя (по умолчанию RUB), обязательное
    currency = db.Column(db.String(10), default="RUB", nullable=False)
    # Месячная финансовая цель (денежный тип с точностью 12.2), по умолчанию 0
    monthly_goal = db.Column(db.Numeric(12, 2), default=0, nullable=False)

    # Обратная связь на User
    user = db.relationship("User", back_populates="profile")


# Промежуточная таблица для связи многие-ко-многим между транзакциями и тегами
transaction_tags = db.Table(
    "transaction_tags",
    # ID транзакции (часть составного первичного ключа)
    db.Column("transaction_id", db.Integer, db.ForeignKey("transactions.id"), primary_key=True),
    # ID тега (часть составного первичного ключа)
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)

# Модель категории (например: Продукты, Кафе)
class Category(db.Model):
    # Имя таблицы
    __tablename__ = "categories"

    # Первичный ключ
    id = db.Column(db.Integer, primary_key=True)
    # Название категории
    name = db.Column(db.String(80), nullable=False)
    # Иконка (символ), по умолчанию "•"
    icon = db.Column(db.String(10), default="•", nullable=False)
    # Владелец категории (внешний ключ на users)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Обратная связь с пользователем
    user = db.relationship("User", back_populates="categories")
    # Связь с транзакциями этой категории
    transactions = db.relationship("Transaction", back_populates="category")


# Модель тега
class Tag(db.Model):
    # Имя таблицы
    __tablename__ = "tags"

    # Первичный ключ
    id = db.Column(db.Integer, primary_key=True)
    # Название тега
    name = db.Column(db.String(40), nullable=False)
    # Владелец тега
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Обратная связь с пользователем
    user = db.relationship("User", back_populates="tags")
    # Связь многие-ко-многим с транзакциями через промежуточную таблицу
    transactions = db.relationship(
        "Transaction", secondary=transaction_tags, back_populates="tags"
    )


# Модель транзакции (доход/расход)
class Transaction(db.Model):
    # Имя таблицы
    __tablename__ = "transactions"

    # Первичный ключ
    id = db.Column(db.Integer, primary_key=True)
    # Название операции
    title = db.Column(db.String(120), nullable=False)
    # Сумма (всегда положительная; знак определяется типом)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    # Тип: "income" (доход) или "expense" (расход)
    transaction_type = db.Column(db.String(10), nullable=False)
    # Дата транзакции (по умолчанию — сегодня)
    transaction_date = db.Column(db.Date, nullable=False, default=date.today)
    # Дополнительная заметка (может быть пустой)
    note = db.Column(db.Text, nullable=True)
    # Владелец транзакции
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Категория транзакции (обязательная)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    # Обратная связь с пользователем
    user = db.relationship("User", back_populates="transactions")
    # Обратная связь с категорией
    category = db.relationship("Category", back_populates="transactions")
    # Связь многие-ко-многим с тегами
    tags = db.relationship(
        "Tag", secondary=transaction_tags, back_populates="transactions"
    )

    # Свойство (property) — сумма со знаком:
    @property
    def signed_amount(self):
        # Доход возвращается как есть, расход — с минусом
        return self.amount if self.transaction_type == "income" else -self.amount


# Функция-загрузчик пользователя для Flask-Login (по ID из сессии)
@login_manager.user_loader
def load_user(user_id):
    # Получаем пользователя из БД по ID (приводим к int)
    return db.session.get(User, int(user_id))


# создаём и настраиваем Flask-приложение
def create_app():
    # Создаём приложение; instance_relative_config — папка instance рядом с проектом
    app = Flask(__name__, instance_relative_config=True)
    # Секретный ключ для подписи сессий и flash-сообщений
    app.config["SECRET_KEY"] = "change-this-secret-key-in-production"
    # URL базы данных
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finora.db"
    # Отключаем отслеживание модификаций (экономит память)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Инициализируем БД с этим приложением
    db.init_app(app)
    # Инициализируем менеджер логина
    login_manager.init_app(app)
    # Указываем, какой маршрут использовать для входа
    login_manager.login_view = "login"
    # Сообщение, если неавторизованный пользователь пытается попасть на защищённую страницу
    login_manager.login_message = "Войдите в аккаунт, чтобы продолжить."
    # Категория для стилизации flash-сообщения
    login_manager.login_message_category = "info"

    # Контекстный процессор — добавляет переменные во все шаблоны
    @app.context_processor
    def inject_helpers():
        # Возвращает функцию перевода кода валюты в символ
        return {
            "currency_symbol": lambda code: {"RUB": "₽", "USD": "$", "EUR": "€", "GBP": "£"}.get(code, code),
        }

    # Главная страница "/"
    @app.route("/")
    def index():
        # Если пользователь авторизован -на дашборд(статистика пользователя)
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        # Иначе — на страницу входа
        return redirect(url_for("login"))

    # Регистрация: доступны GET (показать форму) и POST (обработать)
    @app.route("/register", methods=["GET", "POST"])
    def register():
        # Если уже авторизован - на дашборд
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        # Обработка отправки формы
        if request.method == "POST":
            # Получаем имя (обрезаем пробелы)
            name = request.form.get("name", "").strip()
            # Получаем email и приводим к нижнему регистру
            email = request.form.get("email", "").strip().lower()
            # Получаем пароль
            password = request.form.get("password", "")
            # Получаем повтор пароля
            password_repeat = request.form.get("password_repeat", "")

            # Проверка, что обязательные поля заполнены
            if not name or not email or not password:
                flash("Заполните все обязательные поля.", "error")
                return render_template("auth/register.html")

            # Проверка, что пароли совпадают
            if password != password_repeat:
                flash("Пароли не совпадают.", "error")
                return render_template("auth/register.html")

            # Проверка минимальной длины пароля
            if len(password) < 6:
                flash("Пароль должен содержать минимум 6 символов.", "error")
                return render_template("auth/register.html")

            # Проверка уникальности email
            if User.query.filter_by(email=email).first():
                flash("Пользователь с такой почтой уже существует.", "error")
                return render_template("auth/register.html")

            # Создаём объект пользователя
            user = User(name=name, email=email)
            # Хешируем и сохраняем пароль
            user.set_password(password)

            # Добавляем пользователя в сессию БД
            db.session.add(user)
            # flush — получаем user.id без commit (нужно для связанных объектов)
            db.session.flush()

            # Создаём профиль по умолчанию с валютой RUB
            user.profile = Profile(currency="RUB")
            # Список стандартных категорий (название, иконка)
            default_categories = [
                ("Продукты", "⌁"), ("Кафе", "☕"), ("Транспорт", "⌁"),
                ("Жильё", "⌂"), ("Развлечения", "♡"), ("Зарплата", "↗"),
            ]
            # Добавляем каждую категорию пользователю
            for category_name, icon in default_categories:
                db.session.add(Category(name=category_name, icon=icon, user=user))

            # Фиксируем изменения в БД
            db.session.commit()
            # Автоматически логиним пользователя
            login_user(user)
            # Приветственное сообщение
            flash("Добро пожаловать в Finora!", "success")
            # Перенаправляем на дашборд
            return redirect(url_for("dashboard"))

        # GET-запрос — просто показываем форму
        return render_template("auth/register.html")

    # Маршрут входа
    @app.route("/login", methods=["GET", "POST"])
    def login():
        # Уже авторизован — на дашборд
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        # Обработка POST-запроса
        if request.method == "POST":
            # Email в нижнем регистре
            email = request.form.get("email", "").strip().lower()
            # Пароль
            password = request.form.get("password", "")
            # Ищем пользователя по email
            user = User.query.filter_by(email=email).first()

            # Проверяем существование пользователя и корректность пароля
            if user and user.check_password(password):
                # Логиним пользователя
                login_user(user)
                # Получаем параметр next (куда вернуть после логина)
                next_page = request.args.get("next")
                # Перенаправляем на next или на дашборд
                return redirect(next_page or url_for("dashboard"))

            # Ошибка входа
            flash("Неверная почта или пароль.", "error")

        # GET или после ошибки — показываем форму
        return render_template("auth/login.html")

    # Выход из аккаунта (только для авторизованных)
    @app.route("/logout")
    @login_required
    def logout():
        # Разлогиниваем пользователя
        logout_user()
        # Информационное сообщение
        flash("Вы вышли из аккаунта.", "info")
        # На страницу входа
        return redirect(url_for("login"))

    # Дашборд с общей статистикой (только для авторизованных)
    @app.route("/dashboard")
    @login_required
    def dashboard():
        # Сумма всех доходов пользователя (coalesce — чтобы вернуть 0 вместо NULL)
        income = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "income"
        ).scalar() or 0

        # Сумма всех расходов
        expenses = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense"
        ).scalar() or 0

        # Последние 6 транзакций (по дате и id по убыванию)
        recent = Transaction.query.filter_by(user_id=current_user.id).order_by(
            Transaction.transaction_date.desc(), Transaction.id.desc()
        ).limit(6).all()

        # Объединение расходов по категориям
        expense_rows = db.session.query(
            Category.name,
            func.coalesce(func.sum(Transaction.amount), 0).label("total")
        ).join(Transaction, Transaction.category_id == Category.id).filter(
            Category.user_id == current_user.id,
            Transaction.transaction_type == "expense"
        ).group_by(Category.id).order_by(func.sum(Transaction.amount).desc()).all()

        # Приводим общую сумму расходов к Decimal
        total_expenses = Decimal(str(expenses))
        # Список статистики по категориям
        category_stats = []
        # Для каждой категории вычисляем долю в процентах
        for name, total in expense_rows:
            value = Decimal(str(total))
            # Процент от общих расходов (защита от деления на ноль)
            percent = float((value / total_expenses * 100) if total_expenses else 0)
            category_stats.append({"name": name, "total": value, "percent": round(percent)})

        # Баланс = доходы - расходы
        balance = Decimal(str(income)) - Decimal(str(expenses))
        # Рендерим страницу дашборда со всеми данными
        return render_template(
            "dashboard.html",
            balance=balance,
            income=Decimal(str(income)),
            expenses=Decimal(str(expenses)),
            recent=recent,
            category_stats=category_stats,
        )

    # Список транзакций с фильтрами
    @app.route("/transactions")
    @login_required
    def transactions():
        # Поиск по названию
        search = request.args.get("search", "").strip()
        # Фильтр по типу (income/expense)
        transaction_type = request.args.get("type", "").strip()
        # Фильтр по категории
        category_id = request.args.get("category", "").strip()

        # Базовый запрос — только транзакции текущего пользователя
        query = Transaction.query.filter_by(user_id=current_user.id)

        # Если есть строка поиска — фильтруем по названию (без учёта регистра)
        if search:
            query = query.filter(Transaction.title.ilike(f"%{search}%"))
        # Если тип валиден — фильтруем
        if transaction_type in {"income", "expense"}:
            query = query.filter_by(transaction_type=transaction_type)
        # Если ID категории — число, фильтруем по нему
        if category_id.isdigit():
            query = query.filter_by(category_id=int(category_id))

        # Сортируем и получаем результат
        transactions_list = query.order_by(
            Transaction.transaction_date.desc(), Transaction.id.desc()
        ).all()

        # Список категорий пользователя для фильтра
        categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()

        # Соединяем шаблон со всеми данными (включая сохранённые фильтры)
        return render_template(
            "transactions/list.html",
            transactions=transactions_list,
            categories=categories,
            search=search,
            selected_type=transaction_type,
            selected_category=category_id,
        )

    # Добавление транзакции
    @app.route("/transactions/add", methods=["GET", "POST"])
    @login_required
    def add_transaction():
        # Получаем категории пользователя
        categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()

        # Обработка POST
        if request.method == "POST":
            # Название
            title = request.form.get("title", "").strip()
            # Сумма: заменяем запятую на точку для Decimal
            amount_raw = request.form.get("amount", "").replace(",", ".").strip()
            # Тип
            transaction_type = request.form.get("transaction_type", "").strip()
            # Дата
            transaction_date = request.form.get("transaction_date", "").strip()
            # ID категории
            category_id = request.form.get("category_id", "").strip()
            # Заметка
            note = request.form.get("note", "").strip()

            # Проверка обязательных полей
            if not title or not amount_raw or transaction_type not in {"income", "expense"}:
                flash("Заполните название, сумму и тип операции.", "error")
                return render_template("transactions/form.html", categories=categories)

            # Блок валидации данных
            try:
                # Преобразуем сумму в Decimal
                amount = Decimal(amount_raw)
                # Считываем дату из строки
                parsed_date = datetime.strptime(transaction_date, "%Y-%m-%d").date()
                # Ищем категорию пользователя по ID
                category = Category.query.filter_by(
                    id=int(category_id), user_id=current_user.id
                ).first()
                # Если сумма не положительная или категории нет — ошибка
                if amount <= 0 or not category:
                    raise ValueError
            except (ValueError, ArithmeticError):
                # Ловим ошибки сбора/валидации
                flash("Проверьте сумму, дату и категорию.", "error")
                return render_template("transactions/form.html", categories=categories)

            # Создаём объект транзакции
            transaction = Transaction(
                title=title,
                amount=amount,
                transaction_type=transaction_type,
                transaction_date=parsed_date,
                note=note,
                user_id=current_user.id,
                category_id=category.id,
            )
            # Добавляем в сессию
            db.session.add(transaction)
            # Фиксируем в БД
            db.session.commit()
            # Сообщение об успехе
            flash("Операция добавлена.", "success")
            # Возвращаемся к списку транзакций
            return redirect(url_for("transactions"))

        # GET — показываем форму
        return render_template("transactions/form.html", categories=categories)

    # Удаление транзакции (только POST)
    @app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
    @login_required
    def delete_transaction(transaction_id):
        # Ищем транзакцию по ID, принадлежащую текущему пользователю (404 если нет)
        transaction = Transaction.query.filter_by(
            id=transaction_id, user_id=current_user.id
        ).first_or_404()
        # Удаляем из сессии
        db.session.delete(transaction)
        # Фиксируем
        db.session.commit()
        # Сообщение
        flash("Операция удалена.", "success")
        # Возвращаемся к списку
        return redirect(url_for("transactions"))

    # Профиль пользователя (просмотр и редактирование)
    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        # Получаем профиль текущего пользователя
        profile_obj = current_user.profile

        # Обработка POST — сохранение изменений
        if request.method == "POST":
            # Обновляем имя (если пусто — оставляем старое)
            current_user.name = request.form.get("name", "").strip() or current_user.name
            # Пол (пустое значение -> None)
            profile_obj.gender = request.form.get("gender", "").strip() or None
            # Валюта (по умолчанию RUB)
            profile_obj.currency = request.form.get("currency", "RUB").strip()
            # Финансовая цель: заменяем запятую на точку
            goal_raw = request.form.get("monthly_goal", "0").replace(",", ".").strip()

            # Валидация финансовой цели
            try:
                profile_obj.monthly_goal = Decimal(goal_raw or "0")
                # Отрицательная цель недопустима
                if profile_obj.monthly_goal < 0:
                    raise ValueError
            except (ValueError, ArithmeticError):
                flash("Некорректная сумма финансовой цели.", "error")
                return render_template("profile/profile.html")

            # Дата рождения
            birth_date_raw = request.form.get("birth_date", "").strip()
            if birth_date_raw:
                # анализируем дату
                try:
                    profile_obj.birth_date = datetime.strptime(birth_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    # Ошибка 
                    flash("Проверьте дату рождения.", "error")
                    return render_template("profile/profile.html")
            else:
                # Пустую дату обнуляем
                profile_obj.birth_date = None

            # Фиксируем изменения
            db.session.commit()
            flash("Профиль сохранён.", "success")
            # Перезагружаем страницу профиля
            return redirect(url_for("profile"))

        # GET - показываем форму с текущими данными
        return render_template("profile/profile.html")

    # В контексте приложения создаём все таблицы, если их ещё нет
    with app.app_context():
        db.create_all()

    # Возвращаем готовое приложение
    return app

# Создаём экземпляр приложения 
app = create_app()

# Точка входа: если файл запущен напрямую — запускаем dev-сервер с debug=True
if __name__ == "__main__":
    app.run(debug=True)
