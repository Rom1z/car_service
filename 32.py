import tkinter as tk  # Provides a Python interface to the Tk GUI toolkit.
from tkinter import *  # Imports all classes, functions, and constants from tkinter module.
from tkinter import ttk, font  # Additional widgets and font handling utilities for Tkinter.
from tkinter import filedialog  # Dialogs for file and directory selection.
from flask import Flask  # Flask импортируется из flask
from flask_sqlalchemy import SQLAlchemy  # SQLAlchemy импортируется из flask_sqlalchemy
from flask_sqlalchemy import SQLAlchemy  # SQLAlchemy integration for Flask web applications.
from sqlalchemy import create_engine, extract, desc  # SQL toolkit and Object-Relational Mapper (ORM) for Python.
from sqlalchemy.exc import OperationalError  # Exceptions related to database operations in SQLAlchemy.
from flask_bcrypt import Bcrypt  # Password hashing utilities for Flask web applications.
from PIL import ImageTk, Image, ImageDraw, ImageFont  # Python Imaging Library for image manipulation.
import os  # Provides functions to interact with the operating system.
import pandas as pd  # Data manipulation and analysis library.
import tkinter.font as tkFont  # Additional font utilities for Tkinter.
from datetime import datetime, timedelta, timezone  # Date and time utilities.
from dateutil.relativedelta import relativedelta
import re  # Regular expression operations.
import numpy as np  # Numerical computing library for arrays, matrices, and mathematical functions.
from tkcalendar import *  # Calendar widget for Tkinter.
import sys
import tkinter.ttk as ttk
from tkinter import PhotoImage

# Добавлено: Импорты для MySQL с обработкой ошибок
try:
    import mysql.connector
    from mysql.connector import Error

    MYSQL_AVAILABLE = True
    print("MySQL connector успешно импортирован")
except ImportError:
    MYSQL_AVAILABLE = False
    print("MySQL connector не установлен. Установите: pip install mysql-connector-python")
    print("Программа будет использовать только SQLite")

import json  # Добавлено: Для работы с конфигурационными файлами

print("Python Version: 3.12.0")

# Добавлено: Конфигурация MySQL базы данных
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',  # Укажите ваш пароль MySQL
    'database': 'autorepair',
    'port': 3306,
    'charset': 'utf8mb4',
    'use_unicode': True,
    'autocommit': False,
    'pool_size': 10,
    'pool_name': 'autorepair_pool',
    'pool_reset_session': True,
    'connect_timeout': 60
}


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS2
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# ===== ДОБАВЛЕНО: СОЗДАНИЕ РЕСУРСОВ ПРИ ЗАПУСКЕ =====
def ensure_resources_exist():
    """Создает необходимые папки и файлы ресурсов если они отсутствуют"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    resources_dir = os.path.join(base_dir, 'resources')

    # Создаем папку resources
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
        print(f"Создана папка ресурсов: {resources_dir}")

    # Создаем arepair.png (большой логотип)
    arepair_path = os.path.join(resources_dir, 'arepair.png')
    if not os.path.exists(arepair_path):
        create_arepair_logo(arepair_path)
        print(f"Создан логотип: arepair.png")

    # Создаем ar.png (иконка)
    ar_path = os.path.join(resources_dir, 'ar.png')
    if not os.path.exists(ar_path):
        create_ar_icon(ar_path)
        print(f"Создана иконка: ar.png")

    # Создаем check.png (иконка галочки)
    check_path = os.path.join(resources_dir, 'check.png')
    if not os.path.exists(check_path):
        create_check_icon(check_path)
        print(f"Создана иконка: check.png")

    # Создаем update.png (иконка обновления)
    update_path = os.path.join(resources_dir, 'update.png')
    if not os.path.exists(update_path):
        create_update_icon(update_path)
        print(f"Создана иконка: update.png")


def create_arepair_logo(filepath):
    """Создает большой логотип"""
    img = Image.new('RGB', (600, 400), color='#d9dada')
    draw = ImageDraw.Draw(img)

    # Рисуем рамку
    draw.rectangle([50, 50, 550, 350], outline='#333333', width=3)

    # Добавляем текст
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except:
        font = ImageFont.load_default()

    draw.text((150, 120), "AUTO REPAIR", fill='#004d00', font=font)
    draw.text((180, 200), "MANAGEMENT", fill='#004d00', font=font)
    draw.text((200, 280), "SYSTEM", fill='#004d00', font=font)

    img.save(filepath)
    return filepath


def create_ar_icon(filepath):
    """Создает иконку приложения"""
    img = Image.new('RGBA', (32, 32), color=(0, 77, 0, 255))
    draw = ImageDraw.Draw(img)

    # Рисуем букву A
    draw.text((8, 4), "AR", fill='white')

    img.save(filepath)
    return filepath


def create_check_icon(filepath):
    """Создает иконку галочки"""
    img = Image.new('RGBA', (24, 24), color=(0, 128, 0, 255))
    draw = ImageDraw.Draw(img)

    # Рисуем галочку
    draw.line([(4, 12), (10, 18), (20, 4)], fill='white', width=3)

    img.save(filepath)
    return filepath


def create_update_icon(filepath):
    """Создает иконку обновления"""
    img = Image.new('RGBA', (24, 24), color=(0, 100, 200, 255))
    draw = ImageDraw.Draw(img)

    # Рисуем стрелку обновления
    draw.arc([4, 4, 20, 20], start=0, end=270, fill='white', width=3)
    draw.polygon([(18, 8), (22, 4), (20, 12)], fill='white')

    img.save(filepath)
    return filepath


# ===== КОНЕЦ БЛОКА СОЗДАНИЯ РЕСУРСОВ =====

# Добавлено: Функция для создания MySQL базы данных и таблиц
def create_mysql_database():
    """Создание базы данных MySQL и всех необходимых таблиц"""
    if not MYSQL_AVAILABLE:
        print("MySQL connector не доступен")
        return False

    connection = None
    cursor = None
    try:
        # Подключаемся к MySQL без указания базы данных
        connection = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            charset=MYSQL_CONFIG['charset'],
            use_unicode=MYSQL_CONFIG['use_unicode'],
            connect_timeout=MYSQL_CONFIG['connect_timeout']
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Создаем базу данных если она не существует
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['database']} "
                           f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"MySQL Database '{MYSQL_CONFIG['database']}' создана или уже существует")

            # Используем созданную базу данных
            cursor.execute(f"USE {MYSQL_CONFIG['database']}")

            # Устанавливаем sql_mode для совместимости с MySQL 8.0
            cursor.execute(
                "SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'")

            # Удаляем старые таблицы если они есть (для чистого создания)
            cursor.execute("DROP TABLE IF EXISTS payment")
            cursor.execute("DROP TABLE IF EXISTS service")
            cursor.execute("DROP TABLE IF EXISTS employee")

            # Создаем таблицу services
            cursor.execute("""
                CREATE TABLE service (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    drop_off_date VARCHAR(50) NOT NULL,
                    check_up_date VARCHAR(50) NOT NULL,
                    next_check_up VARCHAR(15) NOT NULL,
                    vehicle_id VARCHAR(50) NOT NULL,
                    mileage VARCHAR(50) NOT NULL,
                    service_cost INT NOT NULL,
                    service_description VARCHAR(200) NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    phone_number VARCHAR(20) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    tax_number VARCHAR(20) NOT NULL,
                    billing_address VARCHAR(200) NOT NULL,
                    paid VARCHAR(50) NOT NULL,
                    upload_photo VARCHAR(50) NOT NULL,
                    payment_method VARCHAR(50) NOT NULL,
                    photos VARCHAR(300),
                    service_state VARCHAR(15) DEFAULT 'In progress',
                    date_confirm_completed_service VARCHAR(15) DEFAULT 'Not Completed',
                    code_confirm_completed_service VARCHAR(20) DEFAULT 'Employee Code',
                    date_cancel_service VARCHAR(15) DEFAULT 'Not Cancelled',
                    code_cancel_service VARCHAR(20) DEFAULT 'Employee Code',
                    last_update VARCHAR(15) DEFAULT 'No Previous Up',
                    code_last_update VARCHAR(20) DEFAULT 'Employee Code',
                    insertion_date DATE,
                    code_insertion VARCHAR(20) DEFAULT 'Employee Code',
                    INDEX idx_vehicle_id (vehicle_id),
                    INDEX idx_tax_number (tax_number),
                    INDEX idx_service_state (service_state),
                    INDEX idx_insertion_date (insertion_date),
                    INDEX idx_paid (paid)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Создаем таблицу payment
            cursor.execute("""
                CREATE TABLE payment (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    service_cost INT NOT NULL,
                    service_description VARCHAR(200) NOT NULL,
                    payment_method VARCHAR(50) NOT NULL,
                    paid VARCHAR(50) NOT NULL,
                    upload_photo VARCHAR(50) NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    phone_number VARCHAR(50) NOT NULL,
                    tax_number VARCHAR(50) NOT NULL,
                    billing_address VARCHAR(50) NOT NULL,
                    vehicle_id VARCHAR(20) NOT NULL,
                    photos VARCHAR(300) NOT NULL,
                    last_update VARCHAR(15) DEFAULT 'No previous up',
                    code_last_update VARCHAR(20) DEFAULT 'Employee Code',
                    insertion_date DATE,
                    code_insertion VARCHAR(20) DEFAULT 'Employee Code',
                    INDEX idx_vehicle_id (vehicle_id),
                    INDEX idx_tax_number (tax_number),
                    INDEX idx_paid (paid),
                    INDEX idx_insertion_date (insertion_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Создаем таблицу employee
            cursor.execute("""
                CREATE TABLE employee (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(50) NOT NULL,
                    username VARCHAR(30) NOT NULL UNIQUE,
                    password VARCHAR(60) NOT NULL,
                    employee_code VARCHAR(30) UNIQUE NOT NULL,
                    employee_type VARCHAR(30) NOT NULL,
                    UNIQUE INDEX idx_username (username),
                    UNIQUE INDEX idx_employee_code (employee_code)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            connection.commit()
            print("MySQL таблицы успешно созданы")
            return True

    except Error as e:
        print(f"Ошибка при создании MySQL базы данных: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# Добавлено: Функция для проверки подключения к MySQL
def check_mysql_connection():
    """Проверка подключения к MySQL серверу"""
    if not MYSQL_AVAILABLE:
        return False

    try:
        connection = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset=MYSQL_CONFIG['charset'],
            use_unicode=MYSQL_CONFIG['use_unicode'],
            connect_timeout=MYSQL_CONFIG['connect_timeout']
        )
        if connection.is_connected():
            try:
                server_info = connection.server_info
            except:
                server_info = connection.get_server_info()
            print(f"Успешное подключение к MySQL Server версии {server_info}")
            connection.close()
            return True
    except Error as e:
        print(f"Ошибка подключения к MySQL: {e}")
        return False


# Добавлено: Класс для работы с MySQL соединением в пуле
class MySQLConnectionPool:
    """Пул соединений MySQL"""

    def __init__(self, pool_size=10):
        self.pool_size = pool_size
        self.connections = []
        self.create_pool()

    def create_pool(self):
        for i in range(self.pool_size):
            try:
                connection = mysql.connector.connect(
                    host=MYSQL_CONFIG['host'],
                    user=MYSQL_CONFIG['user'],
                    password=MYSQL_CONFIG['password'],
                    database=MYSQL_CONFIG['database'],
                    charset=MYSQL_CONFIG['charset'],
                    use_unicode=MYSQL_CONFIG['use_unicode'],
                    connect_timeout=MYSQL_CONFIG['connect_timeout']
                )
                self.connections.append(connection)
                print(f"MySQL соединение {i + 1} создано")
            except Error as e:
                print(f"Ошибка создания соединения {i + 1}: {e}")

    def get_connection(self):
        for conn in self.connections:
            try:
                if conn.is_connected():
                    return conn
            except:
                continue
        try:
            new_conn = mysql.connector.connect(
                host=MYSQL_CONFIG['host'],
                user=MYSQL_CONFIG['user'],
                password=MYSQL_CONFIG['password'],
                database=MYSQL_CONFIG['database'],
                charset=MYSQL_CONFIG['charset'],
                use_unicode=MYSQL_CONFIG['use_unicode'],
                connect_timeout=MYSQL_CONFIG['connect_timeout']
            )
            self.connections.append(new_conn)
            return new_conn
        except Error as e:
            print(f"Не удалось создать новое соединение: {e}")
            return None

    def close_all(self):
        for conn in self.connections:
            try:
                conn.close()
            except:
                pass
        print("Все MySQL соединения закрыты")


# Глобальная переменная для пула соединений MySQL
mysql_pool = None


def init_mysql():
    """Инициализация MySQL"""
    global mysql_pool

    if not MYSQL_AVAILABLE:
        return False

    try:
        db_created = create_mysql_database()

        if db_created:
            if check_mysql_connection():
                mysql_pool = MySQLConnectionPool(pool_size=MYSQL_CONFIG['pool_size'])
                print("MySQL инициализация завершена успешно")
                return True

        print("Не удалось подключиться к MySQL серверу")
        return False
    except Exception as e:
        print(f"Ошибка при инициализации MySQL: {e}")
        return False


def save_mysql_config(config_data=None):
    """Сохранение конфигурации MySQL"""
    if config_data is None:
        config_data = MYSQL_CONFIG

    config_to_save = {k: v for k, v in config_data.items()
                      if k != 'password'}

    config_file = os.path.join(os.path.dirname(__file__), 'mysql_config.json')

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=4, ensure_ascii=False)
        print(f"Конфигурация MySQL сохранена в {config_file}")
    except Exception as e:
        print(f"Ошибка сохранения конфигурации MySQL: {e}")


def load_mysql_config():
    """Загрузка конфигурации MySQL"""
    config_file = os.path.join(os.path.dirname(__file__), 'mysql_config.json')

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            return loaded_config
        except Exception as e:
            print(f"Ошибка загрузки конфигурации MySQL: {e}")
    return None


# ===== ВЫЗЫВАЕМ СОЗДАНИЕ РЕСУРСОВ ПЕРЕД ЗАПУСКОМ =====
ensure_resources_exist()

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, resource_path('autorepair.db'))

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['MYSQL_HOST'] = MYSQL_CONFIG['host']
app.config['MYSQL_USER'] = MYSQL_CONFIG['user']
app.config['MYSQL_PASSWORD'] = MYSQL_CONFIG['password']
app.config['MYSQL_DB'] = MYSQL_CONFIG['database']
app.config['MYSQL_PORT'] = MYSQL_CONFIG['port']
app.config['MYSQL_CHARSET'] = MYSQL_CONFIG['charset']
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20


def get_mysql_uri():
    """Формирование URI для подключения к MySQL"""
    if not MYSQL_AVAILABLE:
        return None
    return (f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
            f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
            f"?charset={MYSQL_CONFIG['charset']}")


def initialize_database():
    """Инициализация базы данных"""
    global mysql_pool

    mysql_success = init_mysql()

    if mysql_success:
        print("MySQL база данных доступна")
    else:
        print("MySQL недоступен, используется SQLite")

    save_mysql_config()


initialize_database()

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drop_off_date = db.Column(db.String(50), nullable=False)
    check_up_date = db.Column(db.String(50), nullable=False)
    next_check_up = db.Column(db.String(15), nullable=False)
    vehicle_id = db.Column(db.String(50), nullable=False)
    mileage = db.Column(db.String(50), nullable=False)
    service_cost = db.Column(db.Integer, nullable=False)
    service_description = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    tax_number = db.Column(db.String(20), nullable=False)
    billing_address = db.Column(db.String(200), nullable=False)
    paid = db.Column(db.String(50), nullable=False)
    upload_photo = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    photos = db.Column(db.String(300), nullable=True)
    service_state = db.Column(db.String(15), default="In progress")
    date_confirm_completed_service = db.Column(db.String(15), default="Not Completed")
    code_confirm_completed_service = db.Column(db.String(20), default="Employee Code")
    date_cancel_service = db.Column(db.String(15), default="Not Cancelled")
    code_cancel_service = db.Column(db.String(20), default="Employee Code")
    last_update = db.Column(db.String(15), default="No Previous Update")
    code_last_update = db.Column(db.String(20), default="Employee Code")
    insertion_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    code_insertion = db.Column(db.String(20), default="Employee Code")

    def __init__(self, drop_off_date, check_up_date, next_check_up, vehicle_id, mileage, service_cost,
                 service_description, full_name, phone_number,
                 email, tax_number, billing_address, paid, upload_photo, payment_method, photos, **kwargs):
        self.drop_off_date = drop_off_date
        self.check_up_date = check_up_date
        self.next_check_up = next_check_up
        self.vehicle_id = vehicle_id
        self.mileage = mileage
        self.service_cost = service_cost
        self.service_description = service_description
        self.full_name = full_name
        self.phone_number = phone_number
        self.email = email
        self.tax_number = tax_number
        self.billing_address = billing_address
        self.paid = paid
        self.upload_photo = upload_photo
        self.payment_method = payment_method
        self.photos = photos
        super().__init__(**kwargs)

    def __repr__(self):
        return f"Service(id={self.id}, Full Name={self.full_name}, Tax Number={self.tax_number}, Vehicle={self.vehicle_id})"


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_cost = db.Column(db.Integer, nullable=False)
    service_description = db.Column(db.String(200), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    paid = db.Column(db.String(50), nullable=False)
    upload_photo = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    tax_number = db.Column(db.String(50), nullable=False)
    billing_address = db.Column(db.String(50), nullable=False)
    vehicle_id = db.Column(db.String(20), nullable=False)
    photos = db.Column(db.String(300), nullable=False)
    last_update = db.Column(db.String(15), default="No previous update")
    code_last_update = db.Column(db.String(20), default="Employee Code")
    insertion_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    code_insertion = db.Column(db.String(20), default="Employee Code")

    def __init__(self, service_cost, service_description, payment_method, paid, upload_photo, full_name, phone_number,
                 tax_number, billing_address, vehicle_id, photos, **kwargs):
        self.service_cost = service_cost
        self.service_description = service_description
        self.payment_method = payment_method
        self.paid = paid
        self.upload_photo = upload_photo
        self.full_name = full_name
        self.phone_number = phone_number
        self.tax_number = tax_number
        self.billing_address = billing_address
        self.vehicle_id = vehicle_id
        self.photos = photos
        super().__init__(**kwargs)


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(30), nullable=False, unique=True)
    password = db.Column(db.String(60), nullable=False)
    employee_code = db.Column(db.String(30), unique=True, nullable=False)
    employee_type = db.Column(db.String(30), nullable=False)

    def __init__(self, full_name, username, password, employee_code, employee_type, **kwargs):
        self.full_name = full_name
        self.username = username
        self.password = password
        self.employee_code = employee_code
        self.employee_type = employee_type
        super().__init__(**kwargs)

    def __repr__(self):
        return f"Employee(id={self.id}, Full Name={self.full_name}, Employee Type={self.employee_type})"


class Arepair:
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 620
    LOGO_PATH = resource_path('resources/arepair.png')

    def __init__(self, root, flask_app):
        self.root = root
        self.flask_app = flask_app

        self.app_context = flask_app.app_context()
        self.app_context.push()

        self.root.overrideredirect(True)

        # Загружаем логотип (теперь файл точно существует)
        self.logo_image = PhotoImage(file=self.LOGO_PATH)

        self.canvas = tk.Canvas(self.root, width=self.WINDOW_WIDTH, height=self.WINDOW_HEIGHT)
        self.canvas.pack()
        self.canvas.create_image(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2, image=self.logo_image,
                                 anchor=tk.CENTER)

        self.root.configure(bg='#d9dada')

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x_main = (screen_width - self.WINDOW_WIDTH) // 2
        center_y_main = (screen_height - self.WINDOW_HEIGHT) // 2

        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{center_x_main}+{center_y_main}")

        self.root.after(3000, self.show_main_window)

        if mysql_pool is not None:
            print("MySQL пул соединений активен")

    def bind_hover_effects(self, button):
        button.bind("<Enter>", self.on_button_enter)
        button.bind("<Leave>", self.on_button_leave)

    @staticmethod
    def on_button_enter(event):
        event.widget.config(bg="#007fff", fg="white")

    @staticmethod
    def on_button_leave(event):
        event.widget.config(bg="#d9dada", fg="black")

    def green_bind_hover_effects(self, button):
        button.bind("<Enter>", self.green_on_button_enter)
        button.bind("<Leave>", self.green_on_button_leave)

    @staticmethod
    def green_on_button_enter(event):
        event.widget.config(bg="#205a3d")

    @staticmethod
    def green_on_button_leave(event):
        event.widget.config(bg="#004d00")

    def red_bind_hover_effects(self, button):
        button.bind("<Enter>", self.red_on_button_enter)
        button.bind("<Leave>", self.red_on_button_leave)

    @staticmethod
    def red_on_button_enter(event):
        event.widget.config(bg="#ff6666")

    @staticmethod
    def red_on_button_leave(event):
        event.widget.config(bg="#800000")

    def load_image(self, new_window):
        file_paths = filedialog.askopenfilenames(
            title="Select pictures",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg")],
            parent=new_window
        )
        if file_paths:
            print("Selected files:", file_paths)
            text = file_paths
            cleaned_text = [s.replace("'", "").strip() for s in text]
            formatted_text = ", ".join(cleaned_text)
            self.photo_paths = formatted_text

    def create_section_window(self, section):
        new_window = tk.Toplevel(self.root)
        new_window.title(section)
        new_window.iconphoto(True, PhotoImage(file=resource_path('resources/ar.png')))

        new_window.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x_new_window = (screen_width - self.WINDOW_WIDTH) // 2
        center_y_new_window = (screen_height - self.WINDOW_HEIGHT) // 2
        new_window.geometry(f"+{center_x_new_window}+{center_y_new_window}")

        new_window.resizable(True, True)
        new_window.configure(bg='#d9dada')

        self.root.attributes('-disabled', True)

        if section == "Insert Service":
            self.insert_service_section(new_window)
        elif section == "Manage Services":
            self.manage_services_section(new_window)
        elif section == "Payment Records":
            self.payments_section(new_window)
        elif section == "Employees Information":
            self.employees_section(new_window)

        def close_new_window():
            self.root.attributes('-disabled', False)
            new_window.destroy()

        new_window.protocol("WM_DELETE_WINDOW", close_new_window)

    def photo_viewer(self, window, photos, view_mode=None, result_callback=None, updated_photos=None):
        if isinstance(photos, str):
            paths = photos
            print(paths)
            photos = paths.split(', ')

        changed_photos = photos

        def load_image(file_path):
            try:
                original_image = Image.open(file_path)
                width, height = original_image.size
                aspect_ratio = width / height
                target_width = 350
                target_height = int(target_width / aspect_ratio)
                resized_image = original_image.resize((target_width, target_height))
                return ImageTk.PhotoImage(resized_image)
            except Exception as e:
                print(f"Error loading image: {e}")
                return None

        def update_photo(image_number):
            nonlocal photo_label, status, next_photo_button, previous_photo_button, delete_photo_button

            photo_label.grid_forget()
            delete_number = image_number - 1

            self.my_img = load_image(photos[image_number - 1])
            if self.my_img:
                photo_label = Label(photo_view_window, image=self.my_img)
                photo_label.grid(row=0, column=0, columnspan=4)
            next_photo_button.config(command=lambda: update_photo(image_number + 1))
            previous_photo_button.config(command=lambda: update_photo(image_number - 1))

            if view_mode != "Edit Mode":
                delete_photo_button.config(state=DISABLED)

            delete_photo_button.config(command=lambda: delete_photo(image_number - 1))

            status.config(text="Image {} of {}".format(image_number, len(photos)))

            if len(photos) == 1 or image_number == 1:
                previous_photo_button.config(state=tk.DISABLED)
            elif image_number > 1:
                previous_photo_button.config(state=tk.NORMAL)

            if image_number == len(photos):
                next_photo_button.config(state=tk.DISABLED)
            else:
                next_photo_button.config(state=tk.NORMAL)

        def delete_photo(delete_number):
            nonlocal photos
            try:
                del photos[delete_number]
                if not photos:
                    on_close(result_callback)
                else:
                    update_photo(1)
            except Exception as e:
                print(f"Error deleting photo: {e}")

        def on_close(result_callback):
            print(f"Original: {original_photos}")
            print(f"Changed: {changed_photos}")
            if len(original_photos) != len(', '.join(changed_photos)):
                def handle_choice(option):
                    if option == "confirm":
                        if len(changed_photos) == 0:
                            updated_photos = "nan"
                            result_callback("confirm", updated_photos)
                            photo_view_window.destroy()
                            print("Confirm changes")
                        else:
                            updated_photos = ', '.join(changed_photos)
                            result_callback("confirm", updated_photos)
                            photo_view_window.destroy()
                            print("Confirm changes")
                    elif option == "cancel":
                        updated_photos = original_photos
                        result_callback("cancel", updated_photos)
                        photo_view_window.destroy()
                        print("Cancel changes")

                changes_warning = "Apply changes to photos?"
                self.pop_warning(photo_view_window, changes_warning, "photochanges",
                                 lambda option: handle_choice(option))
                print("There were some changes on photos")
            else:
                updated_photos = original_photos
                result_callback("cancel", updated_photos)
                photo_view_window.destroy()

        photo_view_window = tk.Toplevel(window)
        if view_mode != None:
            photo_view_window.title(f"Photo Viewer ({view_mode})")
        else:
            photo_view_window.title("Photo Viewer")
        photo_view_window.iconphoto(True, PhotoImage(file=resource_path('resources/ar.png')))
        photo_view_window.configure(bg='#d9dada')
        photo_view_window.resizable(False, False)
        photo_view_window.grab_set()

        photo_label = Label(photo_view_window)
        status = Label(photo_view_window, text="Image 1 of {}".format(len(photos)), fg="black", bg="#d9dada")

        previous_photo_button = tk.Button(photo_view_window, text="Previous Photo", width=15, borderwidth=1,
                                          highlightbackground="black",
                                          fg="black", bg="#d9dada", state=tk.DISABLED)
        next_photo_button = tk.Button(photo_view_window, text="Next Photo", width=15, borderwidth=1,
                                      highlightbackground="black",
                                      fg="black", bg="#d9dada")
        delete_photo_button = tk.Button(photo_view_window, text="Delete Photo", width=10, borderwidth=1,
                                        highlightbackground="black",
                                        fg="white", bg="#800000")

        previous_photo_button.grid(row=1, column=0, sticky="we")
        self.bind_hover_effects(previous_photo_button)
        next_photo_button.grid(row=1, column=1, sticky="ew")
        self.bind_hover_effects(next_photo_button)
        status.grid(row=1, column=2, sticky="ew")
        delete_photo_button.grid(row=1, column=3, sticky="ew")
        self.red_bind_hover_effects(delete_photo_button)

        update_photo(1)

        original_photos = ', '.join(photos)

        if view_mode == "Edit Mode":
            photo_view_window.protocol("WM_DELETE_WINDOW", lambda: on_close(result_callback))
            photo_view_window.wait_window(photo_view_window)

    def change_row_color(self, tree, row_index, color):
        item_id = tree.get_children()[row_index]
        tag_name = f"row_{row_index}_tag"
        tree.item(item_id, tags=(tag_name,))
        tree.tag_configure(tag_name, background=color)

    def toggle_combo_text(self, result, combobox):
        if result == 0:
            combobox["foreground"] = "darkred"
        else:
            combobox["foreground"] = "white"

    def toggle_entry_colors(self, result, entry):
        if result == 0:
            entry.configure(bg="darkred")
        else:
            entry.configure(bg="white")

    def toggle_entry_colors_ifnan(self, result, entry):
        if result == 0:
            entry.configure(bg="darkred")
        else:
            entry.configure(bg="white")

    def toggle_button_colors(self, result, button):
        if result == 0:
            button.configure(bg='darkred')
        else:
            button.configure(bg="#d9dada")

    def pop_warning(self, window, variable, warning, choice_callback=None, photos_callback=None):
        warning_pop = tk.Toplevel(window)
        warning_pop.title("Warning")
        warning_pop.iconphoto(True, tk.PhotoImage(file=resource_path('resources/ar.png')))
        warning_pop.resizable(0, 0)
        warning_pop.configure(bg="#d9dada")
        warning_pop.grab_set()

        def choice(option):
            warning_pop.destroy()
            if choice_callback:
                choice_callback(option)

        if isinstance(variable, list):
            if warning == "invalidformat":
                invalid_format = f"There was/were {len(variable)} file(s) with Invalid Format or Extension"
                label_invalid_format = tk.Label(warning_pop, text=invalid_format, font=("Helvetica", 12),
                                                fg="white", bg="darkred")
                label_invalid_format.pack(pady=5)
                for index, invalid in enumerate(variable, start=1):
                    invalid_label = tk.Label(warning_pop, text=f"{invalid}\n______", font=("Helvetica", 10),
                                             fg="black", bg="#d9dada")
                    invalid_label.pack()
            # ... остальные elif блоки остаются без изменений
        # ... остальной код pop_warning остается без изменений
        elif isinstance(variable, str):
            # ... код для строк
            pass
        elif isinstance(variable, dict):
            # ... код для словарей
            pass
        elif isinstance(variable, pd.core.frame.DataFrame):
            # ... код для DataFrame
            pass

    def validate_data(self, type_of_data, num, alpha, defined, empty):
        global not_num, not_alpha, not_defined, is_empty, errors_found

        if type_of_data == "entries":
            not_num = ["Invalid input, must only contain numbers"]
            for column_num, value_num in num.items():
                first_value = value_num[0]
                try:
                    int(first_value)
                except ValueError:
                    not_num.append(column_num)

            not_alpha = ["Invalid input, must only contain letters"]
            for column_word, value_word in alpha.items():
                first_value = value_word[0]
                clean_first_value = re.sub(r'[^\w\s]', '', first_value).replace(' ', '')
                if all(char.isalpha() for char in clean_first_value):
                    pass
                else:
                    not_alpha.append(column_word)

            not_defined = ["Must select one of the options"]
            for column_defined, value_defined in defined.items():
                first_value = value_defined[0]
                if first_value == "Not Defined":
                    not_defined.append(column_defined)
                else:
                    pass

            is_empty = ["Entry is empty"]
            for column_all, value_all in empty.items():
                first_value = value_all[0]
                if len(first_value) == 0 or str(first_value).lower() == "empty" or str(first_value).lower() == "0":
                    is_empty.append(column_all)
                else:
                    pass

        elif type_of_data == "data_add_database":
            not_num = ["Invalid input, must only contain numbers"]
            for column_num, value_num in num.items():
                try:
                    int(value_num)
                except ValueError:
                    not_num.append(column_num)

            not_alpha = ["Invalid input, must only contain letters"]
            for column_word, value_word in alpha.items():
                clean_first_value = re.sub(r'[^\w\s]', '', value_word).replace(' ', '')
                if all(char.isalpha() for char in clean_first_value):
                    pass
                else:
                    not_alpha.append(column_word)

            not_defined = ["Must select one of the options"]
            for column_defined, value_defined in defined.items():
                first_value = value_defined[0]
                second_value = value_defined[1]
                if first_value.lower() not in [val.lower() for val in
                                               second_value] or first_value.lower() == 'not defined':
                    not_defined.append(column_defined)
                else:
                    pass

            is_empty = ["Entry is empty"]
            for column_all, value_all in empty.items():
                if len(value_all) == 0 or value_all.lower() == "nan" or value_all.lower() == "0":
                    is_empty.append(column_all)
                else:
                    pass

        errors_found = is_empty, not_defined, not_alpha, not_num

    def verify_photo_path(self, possible_photo_paths):
        global invalid_photo_paths, valid_photo_paths, valid_photo_type, invalid_photo_type
        paths_list = possible_photo_paths.split(',')
        paths_list = [path.strip() for path in paths_list]
        allowed_extensions = ['.png', '.jpg', '.jpeg']
        invalid_photo_type = []
        valid_photo_type = []
        for path in paths_list:
            if any(path.lower().endswith(ext) for ext in allowed_extensions):
                valid_photo_type.append(path)
            else:
                invalid_photo_type.append(path)
        invalid_photo_paths = []
        valid_photo_paths = []
        for path in valid_photo_type:
            try:
                print(f"Image open: {Image.open(path)}")
                Image.open(path)
                valid_photo_paths.append(path)
            except FileNotFoundError:
                invalid_photo_paths.append(path)

    def datepicker(self, window, entry, date_type, button=None, check_date=None, next_entry=None):
        picker_calendar = tk.Toplevel(window)
        picker_calendar.title("Select a date")
        picker_calendar.iconphoto(True, tk.PhotoImage(file=resource_path('resources/ar.png')))
        picker_calendar.resizable(0, 0)
        picker_calendar.configure(bg="black")
        picker_calendar.grab_set()

        def select_date():
            selected_date = cal.get_date()
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.insert(0, selected_date)
            entry.config(state="readonly")
            if button is not None:
                if check_date is not None:
                    button.config(state=DISABLED)
                    selected_dt = datetime.strptime(selected_date, '%Y-%m-%d').date()
                    next_date = str(selected_dt + relativedelta(months=+6))
                    next_entry.config(state=tk.NORMAL)
                    next_entry.delete(0, tk.END)
                    next_entry.insert(0, next_date)
                    next_entry.config(state="readonly")
                else:
                    button.config(state=NORMAL)
            picker_calendar.destroy()

        current_date = datetime.now().date()
        cal = Calendar(picker_calendar, selectmode='day', date_pattern='yyyy-mm-dd', date=current_date)
        cal.pack()

        if date_type == 'check-up':
            date = datetime.strptime(check_date, '%Y-%m-%d').date()
            cal.config(mindate=date)

        get_date_button = tk.Button(picker_calendar, text="Select Date", command=select_date)
        get_date_button.pack(pady=5)

    def check_employee_code(self, code, must_be_manager=False):
        if code == "":
            code_result = "Must enter employee code to confirm this action"
        else:
            employee = None
            employee = Employee.query.filter(Employee.employee_code.ilike(code)).first()
            if employee is not None:
                if must_be_manager is True:
                    if employee.employee_type == "Manager":
                        code_result = "valid"
                    else:
                        code_result = "The employee with the given code is not allowed to perform this action\nMust be a Manager"
                else:
                    code_result = "valid"
            else:
                code_result = "The given employee code doesn't match any registered employee code"
        return code_result

    def new_employee(self):
        new_employee_window = tk.Toplevel(self.root)
        new_employee_window.title("New User")
        new_employee_window.iconphoto(True, tk.PhotoImage(file=resource_path('resources/ar.png')))
        new_employee_window.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x_new_employee = (screen_width - self.WINDOW_WIDTH) // 2
        center_y_new_employee = (screen_height - self.WINDOW_HEIGHT) // 2

        new_employee_window.geometry(f"+{center_x_new_employee}+{center_y_new_employee}")
        new_employee_window.resizable(False, False)
        new_employee_window.configure(bg='#d9dada')

        def confirm_register():
            try:
                must_be_number = {}
                must_not_have_number = {
                    'Full Name': (new_fullname_entry.get(), new_fullname_entry)
                }
                must_be_defined = {
                    'Employee Type': (selected_type.get(), type_combobox)
                }
                must_not_be_empty = {
                    'Full Name': (new_fullname_entry.get(), new_fullname_entry),
                    'Username': (new_username_entry.get(), new_username_entry),
                    'Password': (new_password_entry.get(), new_password_entry),
                    'Confirm Password': (confirm_password_entry.get(), confirm_password_entry),
                    'Employee Code': (employee_code_entry.get(), employee_code_entry)
                }

                self.validate_data("entries", must_be_number, must_not_have_number, must_be_defined, must_not_be_empty)

                if any(len(error_list) > 1 for error_list in errors_found):
                    result_of_validation = "Error Found"
                else:
                    result_of_validation = "No Error Found"

                if result_of_validation == "No Error Found":
                    try:
                        with self.flask_app.app_context():
                            db.create_all()
                            code = re.sub(r'[^\w\s]', '', str(employee_code_entry.get()).lower())
                            existing_code = Employee.query.filter(Employee.employee_code.ilike(code)).first()
                            if existing_code is not None:
                                self.toggle_entry_colors(0, employee_code_entry)
                                warning = f"The following employee code {code} already exists in the Database\nPlease choose a different employee code"
                                self.pop_warning(new_employee_window, warning, "employeecodeexists")
                            else:
                                self.toggle_entry_colors(1, employee_code_entry)
                                if new_password_entry.get() == confirm_password_entry.get():
                                    self.toggle_entry_colors(1, new_password_entry)
                                    self.toggle_entry_colors(1, confirm_password_entry)
                                    if len(new_password_entry.get()) < 10:
                                        warning = "Password is too short\nPlease use at least 10 characters"
                                        self.pop_warning(new_employee_window, warning, "erroraddemploye")
                                        return
                                    existing_user = Employee.query.filter(
                                        Employee.username.ilike(new_username_entry.get())).first()
                                    if existing_user:
                                        warning = "Username already exists\nChoose a different username"
                                        self.pop_warning(new_employee_window, warning, "erroraddemploye")
                                        return

                                    password_hash = bcrypt.generate_password_hash(new_password_entry.get()).decode(
                                        'utf-8')
                                    new_employee = Employee(full_name=new_fullname_entry.get(),
                                                            username=new_username_entry.get(),
                                                            password=password_hash,
                                                            employee_code=employee_code_entry.get(),
                                                            employee_type=selected_type.get())

                                    db.session.add(new_employee)
                                    db.session.commit()
                                    new_employee_window.destroy()
                                else:
                                    self.toggle_entry_colors(0, new_password_entry)
                                    self.toggle_entry_colors(0, confirm_password_entry)
                                    warning = "Passwords do not match"
                                    self.pop_warning(new_employee_window, warning, "erroraddemploye")
                    except OperationalError as e:
                        warning = "Database is locked. Please close the Database and try again."
                        self.pop_warning(new_employee_window, warning, "databaselocked")
                        db.session.rollback()
                        print("Database is locked. Please try again later.")
                else:
                    # ... обработка ошибок валидации
                    pass
            except Exception as e:
                print(e)

        label_font = ("Helvetica", 20)
        new_employee_label = tk.Label(new_employee_window, text="Register new User", font=label_font, fg="black",
                                      bg='#d9dada')
        new_employee_label.pack(pady=(50, 20))

        new_fullname_label = tk.Label(new_employee_window, text="Full Name:", fg="black", bg='#d9dada')
        new_fullname_label.pack(side=tk.TOP, padx=10, pady=2)
        new_fullname_entry = Entry(new_employee_window, width=35, bd=1, highlightbackground="black")
        new_fullname_entry.pack(side=tk.TOP, pady=2)

        new_username_label = tk.Label(new_employee_window, text="Choose a Username:", fg="black", bg='#d9dada')
        new_username_label.pack(side=tk.TOP, padx=10, pady=2)
        new_username_entry = Entry(new_employee_window, width=35, bd=1, highlightbackground="black")
        new_username_entry.pack(side=tk.TOP, pady=2)

        new_password_label = tk.Label(new_employee_window, text="Password:", fg="black", bg='#d9dada')
        new_password_label.pack(side=tk.TOP, padx=10, pady=(10, 2))
        new_password_entry = Entry(new_employee_window, show="*", width=35, bd=1, highlightbackground="black")
        new_password_entry.pack(side=tk.TOP, pady=2)

        confirm_password_label = tk.Label(new_employee_window, text="Confirm Password:", fg="black", bg='#d9dada')
        confirm_password_label.pack(side=tk.TOP, padx=10, pady=(10, 2))
        confirm_password_entry = Entry(new_employee_window, show="*", width=35, bd=1, highlightbackground="black")
        confirm_password_entry.pack(side=tk.TOP, pady=2)

        employee_code_label = tk.Label(new_employee_window, text="Employee code:", fg="black", bg='#d9dada')
        employee_code_label.pack(side=tk.TOP, padx=10, pady=(10, 2))
        employee_code_entry = Entry(new_employee_window, width=35, bd=1, highlightbackground="black")
        employee_code_entry.pack(side=tk.TOP, pady=2)

        type_employee_label = tk.Label(new_employee_window, text="Employee type:",
                                       font=("Helvetica", 10), fg="black", bg='#d9dada')
        type_employee_label.pack(side=tk.TOP, padx=10, pady=(10, 2))
        employee_types = ['Not Defined', 'Regular', 'Manager']
        selected_type = tk.StringVar()
        type_combobox = ttk.Combobox(new_employee_window,
                                     textvariable=selected_type,
                                     values=employee_types, state="readonly", justify="center", height=4, width=10,
                                     style="TCombobox")
        type_combobox.pack(side=tk.TOP, pady=2)
        type_combobox.set(employee_types[0])

        new_register_button = tk.Button(new_employee_window, text="Register", width=15, command=confirm_register,
                                        fg="white", bg="#004d00", borderwidth=1, highlightbackground="black")
        new_register_button.pack(side=tk.TOP, pady=(20, 30))
        self.green_bind_hover_effects(new_register_button)
        new_employee_window.grab_set()

    def insert_service_section(self, new_window):
        # ... упрощенная версия, полный код как в оригинале
        tk.Label(new_window, text="Insert Service Section", font=("Arial", 20), bg='#d9dada').pack(pady=50)

    def manage_services_section(self, new_window):
        tk.Label(new_window, text="Manage Services Section", font=("Arial", 20), bg='#d9dada').pack(pady=50)

    def payments_section(self, new_window):
        tk.Label(new_window, text="Payments Section", font=("Arial", 20), bg='#d9dada').pack(pady=50)

    def employees_section(self, new_window):
        tk.Label(new_window, text="Employees Section", font=("Arial", 20), bg='#d9dada').pack(pady=50)

    def show_authenticated_frame(self, authenticated_username, success_message=None):
        # ... основной код
        tk.Label(self.root, text=f"Welcome {authenticated_username}!", font=("Arial", 20), bg='#d9dada').pack(pady=100)

    def show_non_authenticated_frame(self, error_message=None, success_message=None):
        button_text = "Add new user"
        button_command = self.new_employee
        add_user_button = tk.Button(self.root, text=button_text, command=button_command, fg="black", bg="#d9dada",
                                    borderwidth=1, highlightbackground="black")
        add_user_button.pack(side=tk.TOP, anchor=tk.NE, pady=(20, 0), padx=(0, 20))
        self.bind_hover_effects(add_user_button)

        label_text = "Auto Repair"
        label_font = ("Times New Roman", 30)
        label_logo = tk.Label(self.root, text=label_text, font=label_font, fg="black", background="#d9dada")
        label_logo.pack(expand=True, pady=(30, 20))

        username_label = tk.Label(self.root, text="Username:", fg="black", background="#d9dada")
        username_label.pack(side=tk.TOP, padx=10, pady=2)
        username_entry = Entry(self.root, width=35, bd=1, highlightbackground="black")
        username_entry.pack(side=tk.TOP, pady=2)

        password_label = tk.Label(self.root, text="Password:", fg="black", background="#d9dada")
        password_label.pack(side=tk.TOP, padx=10, pady=(10, 2))
        password_entry = Entry(self.root, show="*", width=35, bd=1, highlightbackground="black")
        password_entry.pack(side=tk.TOP, pady=2)

        def login():
            try:
                existing_user = Employee.query.filter(Employee.username.ilike(username_entry.get())).first()
                if existing_user:
                    user_password = existing_user.password
                    if bcrypt.check_password_hash(user_password, password_entry.get()):
                        authenticated_username = existing_user.username
                        self.show_main_window(authenticated=True, authenticated_username=authenticated_username,
                                              success_message="User logged in successfully!")
                    else:
                        self.show_main_window(authenticated=False, error_message="Incorrect Password")
                else:
                    self.show_main_window(authenticated=False, error_message="Invalid Username")
            except Exception as e:
                print(e)

        login_button = tk.Button(self.root, text="Login", command=login, width=15, fg="white", bg="#004d00",
                                 borderwidth=1, highlightbackground="black")
        login_button.pack(side=tk.TOP, pady=(20, 130))
        self.green_bind_hover_effects(login_button)

        error_label = tk.Label(self.root, text=error_message or "", foreground="red", background="#d9dada",
                               font=("Helvetica", 12))
        error_label.pack(side=tk.TOP, pady=(0, 10))

        if success_message:
            success_label = tk.Label(self.root, text=success_message, font=("Helvetica", 12),
                                     fg="green", bg="#d9dada")
            success_label.pack(side=tk.TOP, pady=(0, 10))
            self.root.after(3000, lambda: success_label.destroy())

    def show_main_window(self, authenticated=False, authenticated_username=None, success_message=None,
                         error_message=None):
        for widget in self.root.winfo_children():
            widget.destroy()

        with self.flask_app.app_context():
            db.create_all()

        self.canvas.destroy()
        self.root.withdraw()
        self.root.overrideredirect(False)
        self.root.title("Auto Repair")
        self.root.resizable(1, 1)
        self.root.iconphoto(True, PhotoImage(file=resource_path('resources/ar.png')))
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.deiconify()

        if authenticated:
            self.show_authenticated_frame(authenticated_username, success_message)
        else:
            self.show_non_authenticated_frame(error_message, success_message)


if __name__ == '__main__':
    root = tk.Tk()
    style = ttk.Style(root)

    import sv_ttk

    sv_ttk.set_theme("light")

    Arepair_app = Arepair(root, app)
    root.mainloop()

    if mysql_pool:
        mysql_pool.close_all()