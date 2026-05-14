#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
АИС Автосервис - Desktop приложение
Python + PyQt6 + MySQL
С генерацией PDF отчётов и заказ-нарядов (русский язык поддерживается)
"""

import sys
import os
from datetime import datetime

import mysql.connector
from mysql.connector import Error

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QTextEdit, QStackedWidget, QListWidget,
    QSpinBox, QDoubleSpinBox, QTabWidget, QFileDialog,
    QStatusBar, QGroupBox, QInputDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

# Для PDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Регистрируем русский шрифт при загрузке
    RUSSIAN_FONT = None
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/verdana.ttf",
        "C:/Windows/Fonts/times.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('RussianFont', font_path))
                RUSSIAN_FONT = 'RussianFont'
                print(f"✓ Русский шрифт загружен: {font_path}")
                break
            except Exception as e:
                print(f"⚠ Не удалось загрузить шрифт {font_path}: {e}")
                continue

    if not RUSSIAN_FONT:
        print("⚠ Русский шрифт не найден, будет использоваться Helvetica")
        RUSSIAN_FONT = 'Helvetica'

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    RUSSIAN_FONT = 'Helvetica'
    print("⚠ reportlab не установлен. PDF не будет работать.")
    print("  Установите: pip install reportlab")

# ============================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ
# ============================================
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "12543"  # <-- ВАШ ПАРОЛЬ К MYSQL
DB_NAME = "autoservice"


# ============================================
# КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
# ============================================
class Database:
    """Управление подключением к MySQL."""

    _connection = None

    @classmethod
    def get_connection(cls):
        try:
            if cls._connection is None or not cls._connection.is_connected():
                cls._connection = mysql.connector.connect(
                    host=DB_HOST, port=DB_PORT,
                    user=DB_USER, password=DB_PASSWORD,
                    database=DB_NAME, autocommit=False,
                    charset='utf8mb4', use_pure=True
                )
            else:
                cls._connection.ping(reconnect=True, attempts=3, delay=2)
            return cls._connection
        except Error as e:
            print(f"✗ Ошибка подключения к БД: {e}")
            raise

    @classmethod
    def execute_query(cls, query, params=None, fetch=True):
        conn = cls.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            if fetch:
                result = cursor.fetchall()
            else:
                result = cursor.rowcount
            conn.commit()
            return result
        except Error as e:
            conn.rollback()
            print(f"✗ Ошибка SQL: {e}")
            print(f"  Запрос: {query[:200]}")
            raise
        finally:
            cursor.close()

    @classmethod
    def close(cls):
        if cls._connection and cls._connection.is_connected():
            cls._connection.close()
            cls._connection = None


# ============================================
# АУТЕНТИФИКАЦИЯ
# ============================================
def authenticate_user(username, password):
    try:
        users = Database.execute_query(
            "SELECT * FROM users WHERE username = %s AND password = %s AND is_active = TRUE",
            (username, password)
        )
        return users[0] if users else None
    except Error as e:
        print(f"✗ Ошибка аутентификации: {e}")
        return None


def register_user(username, password, full_name, role):
    try:
        existing = Database.execute_query("SELECT id FROM users WHERE username = %s", (username,))
        if existing:
            return False, "Пользователь с таким логином уже существует!"
        Database.execute_query(
            "INSERT INTO users (username, password, full_name, role, is_active) VALUES (%s,%s,%s,%s,TRUE)",
            (username, password, full_name, role), fetch=False
        )
        return True, "Регистрация успешна!"
    except Error as e:
        return False, f"Ошибка: {e}"


# ============================================
# PDF ГЕНЕРАТОР (с поддержкой русского языка)
# ============================================
class PDFGenerator:
    """Генератор PDF документов с поддержкой русского языка."""

    @staticmethod
    def generate_order_pdf(order_id, filename):
        """Генерация печатной формы заказ-наряда."""
        if not PDF_AVAILABLE:
            QMessageBox.critical(None, "Ошибка", "reportlab не установлен!\npip install reportlab")
            return False

        try:
            # Получаем данные заказа
            order = Database.execute_query("""
                SELECT ro.*, 
                       c.full_name_or_company AS client_name, c.phone AS client_phone,
                       v.plate_number, v.brand, v.model, v.vin, v.mileage,
                       e.full_name AS mechanic_name
                FROM repair_orders ro
                JOIN clients c ON ro.client_id = c.id
                JOIN vehicles v ON ro.vehicle_id = v.id
                LEFT JOIN employees e ON ro.mechanic_id = e.id
                WHERE ro.id = %s
            """, (order_id,))

            if not order:
                return False

            o = order[0]

            # Услуги
            services = Database.execute_query(
                "SELECT * FROM order_services WHERE order_id = %s", (order_id,)
            )

            # Запчасти
            parts = Database.execute_query("""
                SELECT op.*, pc.name AS part_name, pc.article
                FROM order_parts op
                JOIN parts_catalog pc ON op.part_id = pc.id
                WHERE op.order_id = %s
            """, (order_id,))

            # Используем русский шрифт
            font = RUSSIAN_FONT

            # Создаём PDF
            c = pdf_canvas.Canvas(filename, pagesize=A4)
            width, height = A4

            # Заголовок
            c.setFont(font, 18)
            c.drawCentredString(width / 2, height - 30, "ЗАКАЗ-НАРЯД")

            c.setFont(font, 14)
            c.drawCentredString(width / 2, height - 50, f"№ {order_id}")

            # Информация о заказе
            y = height - 80
            x_left = 30

            c.setFont(font, 10)
            date_str = o['created_at'].strftime('%d.%m.%Y %H:%M') if o['created_at'] else '-'
            c.drawString(x_left, y, f"Дата создания: {date_str}")
            y -= 18
            c.drawString(x_left, y, f"Статус: {o['status']}")
            y -= 18
            c.drawString(x_left, y, f"Механик: {o['mechanic_name'] or 'Не назначен'}")

            # Правая колонка
            y = height - 80
            x_right = 300
            c.drawString(x_right, y, f"Клиент: {o['client_name']}")
            y -= 18
            c.drawString(x_right, y, f"Телефон: {o['client_phone'] or '-'}")
            y -= 18

            # Автомобиль
            y -= 25
            c.setFont(font, 12)
            c.drawString(x_left, y, "АВТОМОБИЛЬ:")
            y -= 18
            c.setFont(font, 10)
            c.drawString(x_left, y, f"{o['brand']} {o['model']} | Госномер: {o['plate_number']}")
            y -= 16
            c.drawString(x_left, y, f"VIN: {o['vin'] or '-'} | Пробег: {o['mileage'] or '-'} км")

            # Описание
            y -= 30
            c.setFont(font, 12)
            c.drawString(x_left, y, "ОПИСАНИЕ РАБОТ:")
            y -= 18
            c.setFont(font, 9)
            if o['description']:
                for line in o['description'].split('\n')[:5]:
                    c.drawString(x_left, y, line[:100])
                    y -= 14

            # Таблица услуг
            y -= 20
            c.setFont(font, 12)
            c.drawString(x_left, y, "ВЫПОЛНЕННЫЕ РАБОТЫ:")
            y -= 20

            # Заголовки таблицы
            c.setFont(font, 9)
            c.drawString(x_left, y, "Наименование")
            c.drawString(x_left + 250, y, "Часы")
            c.drawString(x_left + 310, y, "Ставка")
            c.drawString(x_left + 380, y, "Сумма")
            y -= 5
            c.line(x_left, y, width - 30, y)
            y -= 15

            total_labor = 0
            c.setFont(font, 9)
            for s in services:
                name = s['custom_name'] or f"Услуга #{s['service_id']}"
                c.drawString(x_left, y, name[:40])
                c.drawString(x_left + 250, y, str(s['hours']))
                c.drawString(x_left + 310, y, f"{s['rate']:.2f}")
                c.drawString(x_left + 380, y, f"{s['total']:.2f}")
                total_labor += float(s['total'])
                y -= 16

            # Итого услуги
            y -= 5
            c.line(x_left, y, width - 30, y)
            y -= 16
            c.setFont(font, 10)
            c.drawString(x_left + 250, y, "Итого работы:")
            c.drawString(x_left + 380, y, f"{total_labor:.2f}")

            # Таблица запчастей
            y -= 30
            c.setFont(font, 12)
            c.drawString(x_left, y, "ЗАПЧАСТИ И МАТЕРИАЛЫ:")
            y -= 20

            c.setFont(font, 9)
            c.drawString(x_left, y, "Наименование")
            c.drawString(x_left + 200, y, "Артикул")
            c.drawString(x_left + 300, y, "Кол-во")
            c.drawString(x_left + 350, y, "Цена")
            c.drawString(x_left + 420, y, "Сумма")
            y -= 5
            c.line(x_left, y, width - 30, y)
            y -= 15

            total_parts = 0
            c.setFont(font, 9)
            for p in parts:
                c.drawString(x_left, y, p['part_name'][:28])
                c.drawString(x_left + 200, y, (p['article'] or "-")[:15])
                c.drawString(x_left + 300, y, str(p['quantity']))
                c.drawString(x_left + 350, y, f"{p['unit_price']:.2f}")
                c.drawString(x_left + 420, y, f"{p['total']:.2f}")
                total_parts += float(p['total'])
                y -= 16

            # Итого запчасти
            y -= 5
            c.line(x_left, y, width - 30, y)
            y -= 16
            c.setFont(font, 10)
            c.drawString(x_left + 300, y, "Итого запчасти:")
            c.drawString(x_left + 420, y, f"{total_parts:.2f}")

            # Общий итог
            y -= 25
            c.line(x_left, y, width - 30, y)
            y -= 20
            c.setFont(font, 14)
            grand_total = total_labor + total_parts
            discount = float(o['discount_percent']) if o['discount_percent'] else 0
            if discount > 0:
                grand_total = grand_total * (1 - discount / 100)
            c.drawString(x_left + 300, y, "ИТОГО К ОПЛАТЕ:")
            c.drawString(x_left + 420, y, f"{grand_total:.2f} руб.")

            # Подписи
            y -= 50
            c.setFont(font, 10)
            c.drawString(x_left, y, "Мастер-приёмщик: ___________________")
            c.drawString(x_left + 250, y, "Клиент: ___________________")

            y -= 25
            c.drawString(x_left, y, "Механик: ___________________")
            c.drawString(x_left + 250, y, "Дата выдачи: ___________________")

            c.save()
            return True
        except Exception as e:
            print(f"✗ Ошибка PDF: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def generate_report_pdf(filename, title, data_text):
        """Генерация PDF отчёта."""
        if not PDF_AVAILABLE:
            return False

        try:
            font = RUSSIAN_FONT
            c = pdf_canvas.Canvas(filename, pagesize=A4)
            width, height = A4

            c.setFont(font, 16)
            c.drawCentredString(width / 2, height - 30, title)

            c.setFont(font, 10)
            text = c.beginText(30, height - 60)
            for line in data_text.split('\n'):
                text.textLine(line[:120])
            c.drawText(text)

            c.save()
            return True
        except Exception as e:
            print(f"✗ Ошибка PDF: {e}")
            return False


# ============================================
# ОКНО ВХОДА И РЕГИСТРАЦИИ
# ============================================
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Автосервис Pro - Вход")
        self.setFixedSize(420, 350)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        title = QLabel("🚗 АВТОСЕРВИС PRO")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50; padding: 15px;")
        main_layout.addWidget(title)

        self.tabs = QTabWidget()

        # Вкладка ВХОД
        login_tab = QWidget()
        login_layout = QVBoxLayout()
        login_form = QFormLayout()

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Введите логин")
        self.login_username.setMinimumHeight(38)
        self.login_username.setText("admin")

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Введите пароль")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setMinimumHeight(38)
        self.login_password.setText("admin")

        login_form.addRow("👤 Логин:", self.login_username)
        login_form.addRow("🔒 Пароль:", self.login_password)
        login_layout.addLayout(login_form)

        login_btn = QPushButton("🔑 ВОЙТИ")
        login_btn.clicked.connect(self.try_login)
        login_btn.setMinimumHeight(42)
        login_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-size: 15px;
                font-weight: bold; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #219a52; }
        """)
        login_layout.addWidget(login_btn)
        login_tab.setLayout(login_layout)
        self.tabs.addTab(login_tab, "🔑 ВХОД")

        # Вкладка РЕГИСТРАЦИЯ
        register_tab = QWidget()
        register_layout = QVBoxLayout()
        reg_form = QFormLayout()

        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Логин (мин. 3 символа)")
        self.reg_username.setMinimumHeight(35)
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Пароль (мин. 4 символа)")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password.setMinimumHeight(35)
        self.reg_password2 = QLineEdit()
        self.reg_password2.setPlaceholderText("Повторите пароль")
        self.reg_password2.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password2.setMinimumHeight(35)
        self.reg_fullname = QLineEdit()
        self.reg_fullname.setPlaceholderText("Иванов Иван Иванович")
        self.reg_fullname.setMinimumHeight(35)
        self.reg_role = QComboBox()
        self.reg_role.addItems(["manager", "mechanic", "accountant"])
        self.reg_role.setMinimumHeight(35)

        reg_form.addRow("👤 Логин:", self.reg_username)
        reg_form.addRow("🔒 Пароль:", self.reg_password)
        reg_form.addRow("🔒 Повторите:", self.reg_password2)
        reg_form.addRow("📝 ФИО:", self.reg_fullname)
        reg_form.addRow("👔 Роль:", self.reg_role)
        register_layout.addLayout(reg_form)

        register_btn = QPushButton("📝 ЗАРЕГИСТРИРОВАТЬСЯ")
        register_btn.clicked.connect(self.try_register)
        register_btn.setMinimumHeight(42)
        register_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; font-size: 15px;
                font-weight: bold; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        register_layout.addWidget(register_btn)
        register_tab.setLayout(register_layout)
        self.tabs.addTab(register_tab, "📝 РЕГИСТРАЦИЯ")

        main_layout.addWidget(self.tabs)

        info_label = QLabel("По умолчанию: логин 'admin', пароль 'admin'")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        main_layout.addWidget(info_label)

        self.setLayout(main_layout)
        self.login_password.returnPressed.connect(self.try_login)

    def try_login(self):
        username = self.login_username.text().strip()
        password = self.login_password.text()
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return
        user = authenticate_user(username, password)
        if user:
            self.current_user = user
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль!")

    def try_register(self):
        username = self.reg_username.text().strip()
        password = self.reg_password.text()
        password2 = self.reg_password2.text()
        full_name = self.reg_fullname.text().strip()
        role = self.reg_role.currentText()

        if not username or not password or not full_name:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return
        if len(username) < 3:
            QMessageBox.warning(self, "Ошибка", "Логин не менее 3 символов!")
            return
        if len(password) < 4:
            QMessageBox.warning(self, "Ошибка", "Пароль не менее 4 символов!")
            return
        if password != password2:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают!")
            return

        success, message = register_user(username, password, full_name, role)
        if success:
            QMessageBox.information(self, "Успех",
                                    f"✅ Регистрация успешна!\n\n👤 Логин: {username}\n🔒 Пароль: {password}")
            self.tabs.setCurrentIndex(0)
            self.login_username.setText(username)
            self.login_password.setFocus()
        else:
            QMessageBox.critical(self, "Ошибка", message)


# ============================================
# МОДУЛЬ "КЛИЕНТЫ"
# ============================================
class ClientWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout()
        title = QLabel("👥 УПРАВЛЕНИЕ КЛИЕНТАМИ")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Тип", "ФИО/Компания", "Телефон", "Email", "Дата"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        for text, handler, color in [
            ("➕ Добавить", self.add_client, "#27ae60"),
            ("✏️ Редактировать", self.edit_client, "#2980b9"),
            ("🗑️ Удалить", self.delete_client, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {color}; color: white; padding: 8px 20px;
                    border: none; border-radius: 5px; font-weight: bold; }}
                QPushButton:hover {{ opacity: 0.85; }}
            """)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        try:
            rows = Database.execute_query(
                "SELECT id, type, full_name_or_company, phone, email, created_at FROM clients ORDER BY id DESC"
            )
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                self.table.setItem(i, 1, QTableWidgetItem("Физ.лицо" if row['type'] == 'individual' else "Юр.лицо"))
                self.table.setItem(i, 2, QTableWidgetItem(row['full_name_or_company']))
                self.table.setItem(i, 3, QTableWidgetItem(row['phone'] or "-"))
                self.table.setItem(i, 4, QTableWidgetItem(row['email'] or "-"))
                self.table.setItem(i, 5, QTableWidgetItem(
                    row['created_at'].strftime('%d.%m.%Y') if row['created_at'] else "-"))
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def add_client(self):
        dialog = ClientDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_client(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите клиента")
            return
        dialog = ClientDialog(self.user, client_id=int(self.table.item(row, 0).text()), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_client(self):
        row = self.table.currentRow()
        if row < 0:
            return
        client_id = int(self.table.item(row, 0).text())
        if QMessageBox.question(self, "Подтверждение", "Удалить клиента?") == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM clients WHERE id = %s", (client_id,), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", str(e))


class ClientDialog(QDialog):
    def __init__(self, user, client_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.client_id = client_id
        self.setWindowTitle("Редактирование клиента" if client_id else "Новый клиент")
        self.setMinimumWidth(480)

        layout = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItem("Физическое лицо", "individual")
        self.type_combo.addItem("Юридическое лицо", "legal")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Иванов Иван Иванович")
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.address_edit = QTextEdit()
        self.address_edit.setMaximumHeight(65)
        self.inn_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(65)

        layout.addRow("Тип:", self.type_combo)
        layout.addRow("ФИО/Компания *:", self.name_edit)
        layout.addRow("Телефон:", self.phone_edit)
        layout.addRow("Email:", self.email_edit)
        layout.addRow("Адрес:", self.address_edit)
        layout.addRow("ИНН:", self.inn_edit)
        layout.addRow("Заметки:", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)

        if client_id:
            self.load_data()

    def load_data(self):
        data = Database.execute_query("SELECT * FROM clients WHERE id = %s", (self.client_id,))
        if data:
            d = data[0]
            self.type_combo.setCurrentIndex(0 if d['type'] == 'individual' else 1)
            self.name_edit.setText(d['full_name_or_company'])
            self.phone_edit.setText(d['phone'] or "")
            self.email_edit.setText(d['email'] or "")
            self.address_edit.setPlainText(d['address'] or "")
            self.inn_edit.setText(d['inn'] or "")
            self.notes_edit.setPlainText(d['notes'] or "")

    def save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название!")
            return
        try:
            if self.client_id:
                Database.execute_query(
                    """UPDATE clients SET type=%s, full_name_or_company=%s, phone=%s, email=%s, 
                       address=%s, inn=%s, notes=%s WHERE id=%s""",
                    (self.type_combo.currentData(), name, self.phone_edit.text().strip() or None,
                     self.email_edit.text().strip() or None, self.address_edit.toPlainText().strip() or None,
                     self.inn_edit.text().strip() or None, self.notes_edit.toPlainText().strip() or None,
                     self.client_id), fetch=False
                )
            else:
                Database.execute_query(
                    """INSERT INTO clients (type, full_name_or_company, phone, email, address, inn, notes)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (self.type_combo.currentData(), name, self.phone_edit.text().strip() or None,
                     self.email_edit.text().strip() or None, self.address_edit.toPlainText().strip() or None,
                     self.inn_edit.text().strip() or None, self.notes_edit.toPlainText().strip() or None),
                    fetch=False
                )
            self.accept()
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# ============================================
# МОДУЛЬ "АВТОМОБИЛИ"
# ============================================
class VehicleWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout()
        title = QLabel("🚗 АВТОМОБИЛИ")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Клиент", "Госномер", "Марка", "Модель", "Год", "Пробег"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        for text, handler, color in [
            ("➕ Добавить", self.add_vehicle, "#27ae60"),
            ("✏️ Редактировать", self.edit_vehicle, "#2980b9"),
            ("🗑️ Удалить", self.delete_vehicle, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {color}; color: white; padding: 8px 20px;
                    border: none; border-radius: 5px; font-weight: bold; }}
                QPushButton:hover {{ opacity: 0.85; }}
            """)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        try:
            rows = Database.execute_query("""
                SELECT v.id, c.full_name_or_company AS client, v.plate_number, v.brand, v.model, v.year, v.mileage
                FROM vehicles v JOIN clients c ON v.client_id = c.id ORDER BY v.id DESC
            """)
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['client']))
                self.table.setItem(i, 2, QTableWidgetItem(row['plate_number'] or "-"))
                self.table.setItem(i, 3, QTableWidgetItem(row['brand'] or "-"))
                self.table.setItem(i, 4, QTableWidgetItem(row['model'] or "-"))
                self.table.setItem(i, 5, QTableWidgetItem(str(row['year']) if row['year'] else "-"))
                self.table.setItem(i, 6, QTableWidgetItem(f"{row['mileage']:,} км" if row['mileage'] else "-"))
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def add_vehicle(self):
        dialog = VehicleDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_vehicle(self):
        row = self.table.currentRow()
        if row < 0:
            return
        dialog = VehicleDialog(self.user, vehicle_id=int(self.table.item(row, 0).text()), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_vehicle(self):
        row = self.table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, "Удаление", "Удалить автомобиль?") == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM vehicles WHERE id=%s", (int(self.table.item(row, 0).text()),),
                                       fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", str(e))


class VehicleDialog(QDialog):
    def __init__(self, user, vehicle_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.vehicle_id = vehicle_id
        self.setWindowTitle("Автомобиль")
        self.setMinimumWidth(450)

        layout = QFormLayout()
        self.client_combo = QComboBox()
        self.load_clients()
        self.plate_edit = QLineEdit()
        self.vin_edit = QLineEdit()
        self.brand_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, datetime.now().year + 1)
        self.year_spin.setValue(datetime.now().year)
        self.mileage_spin = QSpinBox()
        self.mileage_spin.setRange(0, 9999999)
        self.mileage_spin.setSuffix(" км")
        self.engine_edit = QLineEdit()

        layout.addRow("Клиент *:", self.client_combo)
        layout.addRow("Госномер:", self.plate_edit)
        layout.addRow("VIN:", self.vin_edit)
        layout.addRow("Марка:", self.brand_edit)
        layout.addRow("Модель:", self.model_edit)
        layout.addRow("Год:", self.year_spin)
        layout.addRow("Пробег:", self.mileage_spin)
        layout.addRow("Двигатель:", self.engine_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)

        if vehicle_id:
            self.load_data()

    def load_clients(self):
        try:
            clients = Database.execute_query(
                "SELECT id, full_name_or_company FROM clients ORDER BY full_name_or_company")
            for c in clients:
                self.client_combo.addItem(c['full_name_or_company'], c['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_data(self):
        data = Database.execute_query("SELECT * FROM vehicles WHERE id=%s", (self.vehicle_id,))
        if data:
            d = data[0]
            idx = self.client_combo.findData(d['client_id'])
            if idx >= 0:
                self.client_combo.setCurrentIndex(idx)
            self.plate_edit.setText(d['plate_number'] or "")
            self.vin_edit.setText(d['vin'] or "")
            self.brand_edit.setText(d['brand'] or "")
            self.model_edit.setText(d['model'] or "")
            self.year_spin.setValue(d['year'] or datetime.now().year)
            self.mileage_spin.setValue(d['mileage'] or 0)
            self.engine_edit.setText(d['engine_type'] or "")

    def save(self):
        client_id = self.client_combo.currentData()
        if not client_id:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента!")
            return
        try:
            if self.vehicle_id:
                Database.execute_query(
                    """UPDATE vehicles SET client_id=%s, plate_number=%s, vin=%s, brand=%s, model=%s, year=%s, mileage=%s, engine_type=%s WHERE id=%s""",
                    (client_id, self.plate_edit.text(), self.vin_edit.text(), self.brand_edit.text(),
                     self.model_edit.text(), self.year_spin.value(), self.mileage_spin.value(),
                     self.engine_edit.text(), self.vehicle_id), fetch=False
                )
            else:
                Database.execute_query(
                    """INSERT INTO vehicles (client_id, plate_number, vin, brand, model, year, mileage, engine_type) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (client_id, self.plate_edit.text(), self.vin_edit.text(), self.brand_edit.text(),
                     self.model_edit.text(), self.year_spin.value(), self.mileage_spin.value(),
                     self.engine_edit.text()), fetch=False
                )
            self.accept()
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# ============================================
# МОДУЛЬ "ЗАКАЗ-НАРЯДЫ"
# ============================================
class OrderWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout()
        title = QLabel("🔧 ЗАКАЗ-НАРЯДЫ")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Клиент", "Авто", "Статус", "Работы", "Запчасти", "Итого"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        for text, handler, color in [
            ("➕ Новый заказ", self.add_order, "#27ae60"),
            ("✏️ Редактировать", self.edit_order, "#2980b9"),
            ("🔄 Сменить статус", self.change_status, "#e67e22"),
            ("🖨️ Печать наряда", self.print_order, "#8e44ad"),
            ("🗑️ Удалить", self.delete_order, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {color}; color: white; padding: 8px 15px;
                    border: none; border-radius: 5px; font-weight: bold; font-size: 12px; }}
                QPushButton:hover {{ opacity: 0.85; }}
            """)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        try:
            rows = Database.execute_query("""
                SELECT ro.id, c.full_name_or_company AS client, 
                       CONCAT(v.brand, ' ', v.model, ' (', v.plate_number, ')') AS auto,
                       ro.status, ro.total_labor, ro.total_parts, ro.final_total
                FROM repair_orders ro
                JOIN clients c ON ro.client_id = c.id
                JOIN vehicles v ON ro.vehicle_id = v.id
                ORDER BY ro.id DESC
            """)

            status_names = {'new': 'Новый', 'in_progress': 'В работе', 'completed': 'Выполнен',
                            'closed': 'Закрыт', 'cancelled': 'Отменён'}

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['client']))
                self.table.setItem(i, 2, QTableWidgetItem(row['auto']))
                self.table.setItem(i, 3, QTableWidgetItem(status_names.get(row['status'], row['status'])))
                self.table.setItem(i, 4, QTableWidgetItem(f"{float(row['total_labor'] or 0):.2f}"))
                self.table.setItem(i, 5, QTableWidgetItem(f"{float(row['total_parts'] or 0):.2f}"))
                self.table.setItem(i, 6, QTableWidgetItem(f"{float(row['final_total'] or 0):.2f}"))
            print(f"✓ Загружено {len(rows)} заказов")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def add_order(self):
        dialog = OrderDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите заказ")
            return
        dialog = OrderDialog(self.user, order_id=int(self.table.item(row, 0).text()), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def change_status(self):
        row = self.table.currentRow()
        if row < 0:
            return
        order_id = int(self.table.item(row, 0).text())

        statuses = ['new', 'in_progress', 'completed', 'closed', 'cancelled']
        status_names = ['Новый', 'В работе', 'Выполнен', 'Закрыт', 'Отменён']

        status, ok = QInputDialog.getItem(self, "Сменить статус", "Новый статус:", status_names, editable=False)
        if ok:
            new_status = statuses[status_names.index(status)]
            try:
                if new_status == 'closed':
                    self._close_order(order_id)
                else:
                    Database.execute_query(
                        "UPDATE repair_orders SET status=%s WHERE id=%s",
                        (new_status, order_id), fetch=False
                    )
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def _close_order(self, order_id):
        """Закрытие заказа с пересчётом сумм."""
        try:
            labor = Database.execute_query(
                "SELECT COALESCE(SUM(total), 0) AS s FROM order_services WHERE order_id=%s", (order_id,)
            )[0]['s']
            parts = Database.execute_query(
                "SELECT COALESCE(SUM(total), 0) AS s FROM order_parts WHERE order_id=%s", (order_id,)
            )[0]['s']

            discount = Database.execute_query(
                "SELECT discount_percent FROM repair_orders WHERE id=%s", (order_id,)
            )[0]['discount_percent']

            total = (float(labor) + float(parts)) * (1 - float(discount or 0) / 100)

            # Списание запчастей
            order_parts = Database.execute_query(
                "SELECT part_id, quantity FROM order_parts WHERE order_id=%s", (order_id,)
            )
            for op in order_parts:
                Database.execute_query(
                    "UPDATE parts_catalog SET stock_quantity = stock_quantity - %s WHERE id=%s",
                    (op['quantity'], op['part_id']), fetch=False
                )

            Database.execute_query(
                """UPDATE repair_orders SET total_labor=%s, total_parts=%s, final_total=%s,
                   status='closed', completed_at=NOW() WHERE id=%s""",
                (labor, parts, total, order_id), fetch=False
            )
            QMessageBox.information(self, "Успех", f"Заказ #{order_id} закрыт!\nИтого: {total:.2f} руб.")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def print_order(self):
        """Печать заказ-наряда в PDF."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите заказ")
            return

        order_id = int(self.table.item(row, 0).text())
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить наряд", f"order_{order_id}.pdf", "PDF (*.pdf)"
        )
        if filename:
            if PDFGenerator.generate_order_pdf(order_id, filename):
                QMessageBox.information(self, "Успех", f"Наряд сохранён:\n{filename}")
                try:
                    os.startfile(filename)
                except:
                    pass
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось создать PDF")

    def delete_order(self):
        row = self.table.currentRow()
        if row < 0:
            return
        order_id = int(self.table.item(row, 0).text())
        if QMessageBox.question(self, "Удаление", f"Удалить заказ #{order_id}?") == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM repair_orders WHERE id=%s", (order_id,), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", str(e))


class OrderDialog(QDialog):
    """Диалог заказ-наряда."""

    def __init__(self, user, order_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.order_id = order_id
        self.setWindowTitle("Заказ-наряд" if not order_id else f"Заказ #{order_id}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        layout = QVBoxLayout()

        form = QFormLayout()
        self.client_combo = QComboBox()
        self.load_clients()
        self.client_combo.currentIndexChanged.connect(self.load_vehicles)

        self.vehicle_combo = QComboBox()
        self.mechanic_combo = QComboBox()
        self.load_mechanics()

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Описание проблемы...")
        self.desc_edit.setMaximumHeight(70)

        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, 100)
        self.discount_spin.setSuffix(" %")

        form.addRow("Клиент *:", self.client_combo)
        form.addRow("Автомобиль *:", self.vehicle_combo)
        form.addRow("Механик:", self.mechanic_combo)
        form.addRow("Описание:", self.desc_edit)
        form.addRow("Скидка:", self.discount_spin)
        layout.addLayout(form)

        tabs = QTabWidget()

        # Услуги
        services_widget = QWidget()
        services_layout = QVBoxLayout()

        self.services_table = QTableWidget()
        self.services_table.setColumnCount(4)
        self.services_table.setHorizontalHeaderLabels(["Наименование", "Часы", "Ставка (₽)", "Сумма"])
        self.services_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.services_table.setColumnWidth(1, 80)
        self.services_table.setColumnWidth(2, 100)
        self.services_table.setColumnWidth(3, 120)
        services_layout.addWidget(self.services_table)

        s_btn_layout = QHBoxLayout()
        add_service_btn = QPushButton("➕ Добавить услугу")
        add_service_btn.clicked.connect(lambda: self._add_service_row())
        s_btn_layout.addWidget(add_service_btn)
        remove_service_btn = QPushButton("🗑️ Удалить услугу")
        remove_service_btn.clicked.connect(lambda: self._remove_row(self.services_table))
        s_btn_layout.addWidget(remove_service_btn)
        s_btn_layout.addStretch()
        services_layout.addLayout(s_btn_layout)

        self.labor_total_label = QLabel("Итого работы: 0.00 ₽")
        self.labor_total_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        services_layout.addWidget(self.labor_total_label)
        services_widget.setLayout(services_layout)
        tabs.addTab(services_widget, "🔧 Услуги")

        # Запчасти
        parts_widget = QWidget()
        parts_layout = QVBoxLayout()

        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(4)
        self.parts_table.setHorizontalHeaderLabels(["Наименование", "Кол-во", "Цена (₽)", "Сумма"])
        self.parts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.parts_table.setColumnWidth(1, 80)
        self.parts_table.setColumnWidth(2, 100)
        self.parts_table.setColumnWidth(3, 120)
        parts_layout.addWidget(self.parts_table)

        p_btn_layout = QHBoxLayout()
        add_part_btn = QPushButton("➕ Добавить запчасть")
        add_part_btn.clicked.connect(self._add_part_dialog)
        p_btn_layout.addWidget(add_part_btn)
        remove_part_btn = QPushButton("🗑️ Удалить запчасть")
        remove_part_btn.clicked.connect(lambda: self._remove_row(self.parts_table))
        p_btn_layout.addWidget(remove_part_btn)
        p_btn_layout.addStretch()
        parts_layout.addLayout(p_btn_layout)

        self.parts_total_label = QLabel("Итого запчасти: 0.00 ₽")
        self.parts_total_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        parts_layout.addWidget(self.parts_total_label)
        parts_widget.setLayout(parts_layout)
        tabs.addTab(parts_widget, "📦 Запчасти")

        layout.addWidget(tabs)

        self.grand_total_label = QLabel("ВСЕГО: 0.00 ₽")
        self.grand_total_label.setStyleSheet("font-weight: bold; font-size: 18px; color: #27ae60; padding: 10px;")
        layout.addWidget(self.grand_total_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_order)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        self.services_table.cellChanged.connect(self._update_totals)
        self.parts_table.cellChanged.connect(self._update_totals)
        self.discount_spin.valueChanged.connect(self._update_totals)

        if order_id:
            self.load_order_data()

    def load_clients(self):
        try:
            clients = Database.execute_query(
                "SELECT id, full_name_or_company FROM clients ORDER BY full_name_or_company")
            self.client_combo.clear()
            self.client_combo.addItem("-- Выберите клиента --", None)
            for c in clients:
                self.client_combo.addItem(c['full_name_or_company'], c['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_vehicles(self):
        self.vehicle_combo.clear()
        client_id = self.client_combo.currentData()
        if not client_id:
            return
        try:
            vehicles = Database.execute_query(
                "SELECT id, CONCAT(brand,' ',model,' (',plate_number,')') AS info FROM vehicles WHERE client_id=%s",
                (client_id,)
            )
            self.vehicle_combo.addItem("-- Выберите авто --", None)
            for v in vehicles:
                self.vehicle_combo.addItem(v['info'], v['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_mechanics(self):
        try:
            mechanics = Database.execute_query("SELECT id, full_name FROM employees WHERE position='механик'")
            self.mechanic_combo.clear()
            self.mechanic_combo.addItem("-- Не назначен --", None)
            for m in mechanics:
                self.mechanic_combo.addItem(m['full_name'], m['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _add_service_row(self, name="Новая услуга", hours="1.0", rate="1000"):
        self.services_table.cellChanged.disconnect(self._update_totals)
        row = self.services_table.rowCount()
        self.services_table.insertRow(row)
        self.services_table.setItem(row, 0, QTableWidgetItem(name))
        self.services_table.setItem(row, 1, QTableWidgetItem(hours))
        self.services_table.setItem(row, 2, QTableWidgetItem(rate))
        total = float(hours) * float(rate)
        self.services_table.setItem(row, 3, QTableWidgetItem(f"{total:.2f}"))
        self.services_table.cellChanged.connect(self._update_totals)
        self._update_totals()

    def _add_part_dialog(self):
        try:
            parts = Database.execute_query(
                "SELECT id, name, retail_price, stock_quantity FROM parts_catalog WHERE stock_quantity > 0 ORDER BY name")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return

        if not parts:
            QMessageBox.information(self, "Информация", "Нет запчастей на складе!")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Выбор запчасти")
        dialog.setMinimumWidth(400)
        d_layout = QVBoxLayout()

        d_table = QTableWidget()
        d_table.setColumnCount(3)
        d_table.setHorizontalHeaderLabels(["Наименование", "Цена", "На складе"])
        d_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        d_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        d_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        d_table.setRowCount(len(parts))
        for i, p in enumerate(parts):
            d_table.setItem(i, 0, QTableWidgetItem(p['name']))
            d_table.setItem(i, 1, QTableWidgetItem(f"{p['retail_price']:.2f}"))
            d_table.setItem(i, 2, QTableWidgetItem(str(p['stock_quantity'])))
            d_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, p)

        d_layout.addWidget(d_table)

        d_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        d_buttons.accepted.connect(dialog.accept)
        d_buttons.rejected.connect(dialog.reject)
        d_layout.addWidget(d_buttons)
        dialog.setLayout(d_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            row = d_table.currentRow()
            if row >= 0:
                part_data = d_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if part_data:
                    self._add_part_row(part_data['name'], "1", str(part_data['retail_price']))

    def _add_part_row(self, name="Запчасть", qty="1", price="500"):
        self.parts_table.cellChanged.disconnect(self._update_totals)
        row = self.parts_table.rowCount()
        self.parts_table.insertRow(row)
        self.parts_table.setItem(row, 0, QTableWidgetItem(name))
        self.parts_table.setItem(row, 1, QTableWidgetItem(qty))
        self.parts_table.setItem(row, 2, QTableWidgetItem(price))
        total = float(qty) * float(price)
        self.parts_table.setItem(row, 3, QTableWidgetItem(f"{total:.2f}"))
        self.parts_table.cellChanged.connect(self._update_totals)
        self._update_totals()

    def _remove_row(self, table):
        row = table.currentRow()
        if row >= 0:
            table.cellChanged.disconnect(self._update_totals)
            table.removeRow(row)
            table.cellChanged.connect(self._update_totals)
            self._update_totals()

    def _update_totals(self):
        try:
            labor_total = 0
            for row in range(self.services_table.rowCount()):
                try:
                    h = float(self.services_table.item(row, 1).text() if self.services_table.item(row, 1) else 0)
                    r = float(self.services_table.item(row, 2).text() if self.services_table.item(row, 2) else 0)
                    total = h * r
                    self.services_table.cellChanged.disconnect(self._update_totals)
                    self.services_table.setItem(row, 3, QTableWidgetItem(f"{total:.2f}"))
                    self.services_table.cellChanged.connect(self._update_totals)
                    labor_total += total
                except (ValueError, AttributeError):
                    pass

            parts_total = 0
            for row in range(self.parts_table.rowCount()):
                try:
                    q = float(self.parts_table.item(row, 1).text() if self.parts_table.item(row, 1) else 0)
                    p = float(self.parts_table.item(row, 2).text() if self.parts_table.item(row, 2) else 0)
                    total = q * p
                    self.parts_table.cellChanged.disconnect(self._update_totals)
                    self.parts_table.setItem(row, 3, QTableWidgetItem(f"{total:.2f}"))
                    self.parts_table.cellChanged.connect(self._update_totals)
                    parts_total += total
                except (ValueError, AttributeError):
                    pass

            discount = self.discount_spin.value()
            grand_total = (labor_total + parts_total) * (1 - discount / 100)

            self.labor_total_label.setText(f"Итого работы: {labor_total:.2f} ₽")
            self.parts_total_label.setText(f"Итого запчасти: {parts_total:.2f} ₽")
            self.grand_total_label.setText(f"ВСЕГО: {grand_total:.2f} ₽ (скидка {discount}%)")
        except Exception as e:
            print(f"Ошибка пересчёта: {e}")

    def load_order_data(self):
        try:
            data = Database.execute_query("SELECT * FROM repair_orders WHERE id=%s", (self.order_id,))
            if not data:
                return
            d = data[0]

            idx = self.client_combo.findData(d['client_id'])
            if idx >= 0:
                self.client_combo.setCurrentIndex(idx)

            self.load_vehicles()
            idx_v = self.vehicle_combo.findData(d['vehicle_id'])
            if idx_v >= 0:
                self.vehicle_combo.setCurrentIndex(idx_v)

            idx_m = self.mechanic_combo.findData(d['mechanic_id'])
            if idx_m >= 0:
                self.mechanic_combo.setCurrentIndex(idx_m)

            self.desc_edit.setPlainText(d['description'] or "")
            self.discount_spin.setValue(float(d['discount_percent'] or 0))

            # Загружаем услуги
            services = Database.execute_query("SELECT * FROM order_services WHERE order_id=%s", (self.order_id,))
            self.services_table.setRowCount(0)
            for s in services:
                name = s['custom_name'] or f"Услуга #{s['service_id']}"
                self._add_service_row(name, str(s['hours']), str(s['rate']))

            # Загружаем запчасти
            parts = Database.execute_query("""
                SELECT op.*, pc.name AS part_name FROM order_parts op
                JOIN parts_catalog pc ON op.part_id = pc.id WHERE op.order_id=%s
            """, (self.order_id,))
            self.parts_table.setRowCount(0)
            for p in parts:
                self._add_part_row(p['part_name'], str(p['quantity']), str(p['unit_price']))
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def save_order(self):
        client_id = self.client_combo.currentData()
        vehicle_id = self.vehicle_combo.currentData()

        if not client_id or not vehicle_id:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента и автомобиль!")
            return

        mechanic_id = self.mechanic_combo.currentData()
        desc = self.desc_edit.toPlainText()
        discount = self.discount_spin.value()

        self._update_totals()

        # Считаем финальные суммы
        labor_total = sum(
            float(self.services_table.item(row, 3).text())
            for row in range(self.services_table.rowCount())
            if self.services_table.item(row, 3)
        )
        parts_total = sum(
            float(self.parts_table.item(row, 3).text())
            for row in range(self.parts_table.rowCount())
            if self.parts_table.item(row, 3)
        )
        final_total = (labor_total + parts_total) * (1 - discount / 100)

        try:
            if self.order_id:
                Database.execute_query("DELETE FROM order_services WHERE order_id=%s", (self.order_id,), fetch=False)
                Database.execute_query("DELETE FROM order_parts WHERE order_id=%s", (self.order_id,), fetch=False)
                Database.execute_query(
                    """UPDATE repair_orders 
                       SET client_id=%s, vehicle_id=%s, mechanic_id=%s, description=%s, 
                           discount_percent=%s, total_labor=%s, total_parts=%s, final_total=%s 
                       WHERE id=%s""",
                    (client_id, vehicle_id, mechanic_id, desc, discount,
                     labor_total, parts_total, final_total, self.order_id),
                    fetch=False
                )
                order_id = self.order_id
            else:
                cursor = Database.get_connection().cursor()
                cursor.execute(
                    """INSERT INTO repair_orders 
                       (client_id, vehicle_id, mechanic_id, description, discount_percent, 
                        total_labor, total_parts, final_total, status) 
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'new')""",
                    (client_id, vehicle_id, mechanic_id, desc, discount,
                     labor_total, parts_total, final_total)
                )
                order_id = cursor.lastrowid
                Database.get_connection().commit()
                cursor.close()

            # Сохраняем услуги
            for row in range(self.services_table.rowCount()):
                name = self.services_table.item(row, 0)
                hours = self.services_table.item(row, 1)
                rate = self.services_table.item(row, 2)
                if name and hours and rate and name.text().strip():
                    Database.execute_query(
                        "INSERT INTO order_services (order_id, custom_name, hours, rate) VALUES (%s,%s,%s,%s)",
                        (order_id, name.text(), float(hours.text()), float(rate.text())), fetch=False
                    )

            # Сохраняем запчасти
            for row in range(self.parts_table.rowCount()):
                name = self.parts_table.item(row, 0)
                qty = self.parts_table.item(row, 1)
                price = self.parts_table.item(row, 2)
                if name and qty and price and name.text().strip():
                    parts = Database.execute_query("SELECT id FROM parts_catalog WHERE name=%s LIMIT 1", (name.text(),))
                    if parts:
                        Database.execute_query(
                            "INSERT INTO order_parts (order_id, part_id, quantity, unit_price) VALUES (%s,%s,%s,%s)",
                            (order_id, parts[0]['id'], int(float(qty.text())), float(price.text())), fetch=False
                        )

            self.accept()
            QMessageBox.information(self, "Успех",
                                    f"Заказ #{order_id} сохранён!\nРаботы: {labor_total:.2f}\nЗапчасти: {parts_total:.2f}\nИТОГО: {final_total:.2f} руб.")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# ============================================
# МОДУЛЬ "СКЛАД"
# ============================================
class InventoryWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout()
        title = QLabel("📦 СКЛАД ЗАПЧАСТЕЙ")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Наименование", "Артикул", "Цена розн.", "Остаток", "Мин."])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        for text, handler, color in [
            ("➕ Добавить", self.add_part, "#27ae60"),
            ("✏️ Изменить", self.edit_part, "#2980b9"),
            ("📥 Приход", self.receive_part, "#8e44ad"),
            ("🗑️ Удалить", self.delete_part, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {color}; color: white; padding: 8px 20px;
                    border: none; border-radius: 5px; font-weight: bold; }}
                QPushButton:hover {{ opacity: 0.85; }}
            """)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        try:
            rows = Database.execute_query(
                "SELECT id, name, article, retail_price, stock_quantity, min_stock FROM parts_catalog ORDER BY name"
            )
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['name']))
                self.table.setItem(i, 2, QTableWidgetItem(row['article'] or ""))
                self.table.setItem(i, 3, QTableWidgetItem(f"{row['retail_price']:.2f}"))
                qty_item = QTableWidgetItem(f"{row['stock_quantity']} шт.")
                if row['stock_quantity'] <= row['min_stock']:
                    qty_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(i, 4, qty_item)
                self.table.setItem(i, 5, QTableWidgetItem(str(row['min_stock'])))
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def add_part(self):
        dialog = PartDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_part(self):
        row = self.table.currentRow()
        if row < 0:
            return
        dialog = PartDialog(self.user, part_id=int(self.table.item(row, 0).text()), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def receive_part(self):
        row = self.table.currentRow()
        if row < 0:
            return
        part_id = int(self.table.item(row, 0).text())
        qty, ok = QInputDialog.getInt(self, "Приход", "Количество:", minValue=1)
        if ok:
            try:
                Database.execute_query(
                    "UPDATE parts_catalog SET stock_quantity = stock_quantity + %s WHERE id=%s",
                    (qty, part_id), fetch=False
                )
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def delete_part(self):
        row = self.table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, "Удаление", "Удалить запчасть?") == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM parts_catalog WHERE id=%s",
                                       (int(self.table.item(row, 0).text()),), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", str(e))


class PartDialog(QDialog):
    def __init__(self, user, part_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.part_id = part_id
        self.setWindowTitle("Запчасть")
        self.setMinimumWidth(400)

        layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.article_edit = QLineEdit()
        self.manufact_edit = QLineEdit()
        self.unit_edit = QLineEdit("шт.")
        self.purchase_spin = QDoubleSpinBox()
        self.purchase_spin.setRange(0, 9999999)
        self.retail_spin = QDoubleSpinBox()
        self.retail_spin.setRange(0, 9999999)
        self.stock_spin = QSpinBox()
        self.stock_spin.setRange(0, 99999)
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 99999)
        self.min_spin.setValue(5)

        layout.addRow("Наименование *:", self.name_edit)
        layout.addRow("Артикул:", self.article_edit)
        layout.addRow("Производитель:", self.manufact_edit)
        layout.addRow("Ед.изм:", self.unit_edit)
        layout.addRow("Цена закуп.:", self.purchase_spin)
        layout.addRow("Цена розн.:", self.retail_spin)
        layout.addRow("Остаток:", self.stock_spin)
        layout.addRow("Мин.остаток:", self.min_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)

        if part_id:
            self.load_data()

    def load_data(self):
        data = Database.execute_query("SELECT * FROM parts_catalog WHERE id=%s", (self.part_id,))
        if data:
            d = data[0]
            self.name_edit.setText(d['name'])
            self.article_edit.setText(d['article'] or "")
            self.manufact_edit.setText(d['manufacturer'] or "")
            self.unit_edit.setText(d['unit'] or "шт.")
            self.purchase_spin.setValue(float(d['purchase_price']))
            self.retail_spin.setValue(float(d['retail_price']))
            self.stock_spin.setValue(d['stock_quantity'])
            self.min_spin.setValue(d['min_stock'])

    def save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название!")
            return
        try:
            if self.part_id:
                Database.execute_query(
                    """UPDATE parts_catalog SET name=%s, article=%s, manufacturer=%s, unit=%s,
                       purchase_price=%s, retail_price=%s, stock_quantity=%s, min_stock=%s WHERE id=%s""",
                    (name, self.article_edit.text(), self.manufact_edit.text(), self.unit_edit.text(),
                     self.purchase_spin.value(), self.retail_spin.value(), self.stock_spin.value(),
                     self.min_spin.value(), self.part_id), fetch=False
                )
            else:
                Database.execute_query(
                    """INSERT INTO parts_catalog (name, article, manufacturer, unit, purchase_price, retail_price, stock_quantity, min_stock)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (name, self.article_edit.text(), self.manufact_edit.text(), self.unit_edit.text(),
                     self.purchase_spin.value(), self.retail_spin.value(), self.stock_spin.value(),
                     self.min_spin.value()), fetch=False
                )
            self.accept()
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# ============================================
# МОДУЛЬ "ОТЧЁТЫ"
# ============================================
class ReportWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._last_report_title = ""
        self._last_report_text = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        title = QLabel("📊 ОТЧЁТЫ И АНАЛИТИКА")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title)

        gb = QGroupBox("Генерация отчётов")
        gl = QVBoxLayout()

        for text, handler in [
            ("💰 Выручка за текущий месяц", self.revenue_report),
            ("👨‍🔧 Загруженность механиков", self.mechanics_report),
            ("📦 Продажи запчастей за месяц", self.parts_report),
            ("📋 Все заказы за период", self.orders_report),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(38)
            btn.setStyleSheet("""
                QPushButton { background-color: #3498db; color: white; padding: 10px;
                    border: none; border-radius: 5px; text-align: left; font-size: 13px; }
                QPushButton:hover { background-color: #2980b9; }
            """)
            gl.addWidget(btn)

        gb.setLayout(gl)
        layout.addWidget(gb)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setStyleSheet("font-family: 'Courier New'; font-size: 12px;")
        layout.addWidget(self.report_text)

        export_layout = QHBoxLayout()

        export_pdf_btn = QPushButton("📕 Экспорт в PDF")
        export_pdf_btn.clicked.connect(self.export_pdf)
        export_pdf_btn.setMinimumHeight(38)
        export_pdf_btn.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; padding: 10px;
                border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #c0392b; }
        """)

        export_txt_btn = QPushButton("📄 Экспорт в TXT")
        export_txt_btn.clicked.connect(self.export_txt)
        export_txt_btn.setMinimumHeight(38)
        export_txt_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 10px;
                border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #219a52; }
        """)

        export_layout.addWidget(export_pdf_btn)
        export_layout.addWidget(export_txt_btn)
        export_layout.addStretch()
        layout.addLayout(export_layout)

        self.setLayout(layout)

    def _set_report(self, title, text):
        self._last_report_title = title
        self._last_report_text = text
        self.report_text.setText(text)

    def revenue_report(self):
        try:
            data = Database.execute_query("""
                SELECT COALESCE(SUM(final_total),0) AS total, COUNT(*) AS cnt
                FROM repair_orders WHERE status='closed'
                AND MONTH(completed_at)=MONTH(CURDATE()) AND YEAR(completed_at)=YEAR(CURDATE())
            """)
            d = data[0]
            text = f"ВЫРУЧКА ЗА ТЕКУЩИЙ МЕСЯЦ\n{'=' * 40}\n"
            text += f"Закрыто заказов: {d['cnt']}\n"
            text += f"Общая выручка: {d['total']:.2f} руб.\n"
            self._set_report("Выручка за месяц", text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def mechanics_report(self):
        try:
            data = Database.execute_query("""
                SELECT e.full_name, COUNT(ro.id) AS cnt, COALESCE(SUM(ro.final_total),0) AS total
                FROM employees e
                LEFT JOIN repair_orders ro ON e.id=ro.mechanic_id AND ro.status IN ('completed','closed')
                    AND MONTH(ro.completed_at)=MONTH(CURDATE())
                WHERE e.position='механик'
                GROUP BY e.id, e.full_name
            """)
            text = "ЗАГРУЖЕННОСТЬ МЕХАНИКОВ (текущий месяц)\n" + "=" * 50 + "\n"
            for d in data:
                text += f"{d['full_name']}: {d['cnt']} заказов, {d['total']:.2f} руб.\n"
            self._set_report("Загрузка механиков", text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def parts_report(self):
        try:
            data = Database.execute_query("""
                SELECT pc.name, SUM(op.quantity) AS qty, SUM(op.total) AS total
                FROM order_parts op
                JOIN parts_catalog pc ON op.part_id=pc.id
                JOIN repair_orders ro ON op.order_id=ro.id
                WHERE ro.status='closed' AND MONTH(ro.completed_at)=MONTH(CURDATE())
                GROUP BY pc.id, pc.name ORDER BY total DESC
            """)
            text = "ПРОДАННЫЕ ЗАПЧАСТИ (текущий месяц)\n" + "=" * 50 + "\n"
            if data:
                for d in data:
                    text += f"{d['name']}: {d['qty']} шт., {d['total']:.2f} руб.\n"
            else:
                text += "Нет продаж за месяц.\n"
            self._set_report("Продажи запчастей", text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def orders_report(self):
        try:
            data = Database.execute_query("""
                SELECT ro.id, c.full_name_or_company AS client, v.plate_number,
                       ro.status, ro.final_total, ro.created_at
                FROM repair_orders ro
                JOIN clients c ON ro.client_id=c.id
                JOIN vehicles v ON ro.vehicle_id=v.id
                ORDER BY ro.created_at DESC
            """)
            text = "ВСЕ ЗАКАЗ-НАРЯДЫ\n" + "=" * 60 + "\n"
            status_names = {'new': 'Новый', 'in_progress': 'В работе', 'completed': 'Выполнен',
                            'closed': 'Закрыт', 'cancelled': 'Отменён'}
            for d in data:
                date_str = d['created_at'].strftime('%d.%m.%Y') if d['created_at'] else "-"
                text += (f"#{d['id']} | {date_str} | {d['client'][:20]} | {d['plate_number']} | "
                         f"{status_names.get(d['status'], d['status'])} | {d['final_total']:.2f} руб.\n")
            self._set_report("Все заказы", text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def export_pdf(self):
        if not self._last_report_text.strip():
            QMessageBox.information(self, "Информация", "Сначала сгенерируйте отчёт!")
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить PDF", "report.pdf", "PDF (*.pdf)")
        if filename:
            if PDFGenerator.generate_report_pdf(filename, self._last_report_title, self._last_report_text):
                QMessageBox.information(self, "Успех", f"Отчёт сохранён в PDF:\n{filename}")
                try:
                    os.startfile(filename)
                except:
                    pass
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось создать PDF")

    def export_txt(self):
        if not self._last_report_text.strip():
            QMessageBox.information(self, "Информация", "Сначала сгенерируйте отчёт!")
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить TXT", "report.txt", "Text (*.txt)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self._last_report_text)
                QMessageBox.information(self, "Успех", f"Отчёт сохранён:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))


# ============================================
# ГЛАВНОЕ ОКНО
# ============================================
class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.setWindowTitle(f"Автосервис Pro — {user['full_name']} ({user['role']})")
        self.setMinimumSize(1200, 750)

        central = QWidget()
        self.setCentralWidget(central)

        self.stack = QStackedWidget()
        self.menu_list = QListWidget()
        self.menu_list.setMaximumWidth(200)
        self.menu_list.setStyleSheet("""
            QListWidget { background-color: #2c3e50; color: white; font-size: 14px; border: none; }
            QListWidget::item { padding: 14px 18px; border-bottom: 1px solid #34495e; }
            QListWidget::item:selected { background-color: #3498db; }
            QListWidget::item:hover { background-color: #34495e; }
        """)

        for item in ["👥 Клиенты", "🚗 Автомобили", "🔧 Заказ-наряды", "📦 Склад", "📊 Отчёты"]:
            self.menu_list.addItem(item)

        self.menu_list.setCurrentRow(0)
        self.menu_list.currentRowChanged.connect(self.switch_module)

        self.pages = {
            'clients': ClientWidget(self.current_user),
            'vehicles': VehicleWidget(self.current_user),
            'orders': OrderWidget(self.current_user),
            'inventory': InventoryWidget(self.current_user),
            'reports': ReportWidget(self.current_user)
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        layout = QHBoxLayout()
        layout.addWidget(self.menu_list)
        layout.addWidget(self.stack)
        central.setLayout(layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            f"👤 {self.current_user['full_name']} | 👔 {self.current_user['role']} | 📅 {datetime.now().strftime('%d.%m.%Y')}"
        )

        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def switch_module(self, index):
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if hasattr(page, 'load_data'):
            page.load_data()


# ============================================
# ЗАПУСК
# ============================================
def main():
    print("=" * 50)
    print("🚗 АВТОСЕРВИС PRO - ЗАПУСК")
    print("=" * 50)

    if RUSSIAN_FONT != 'Helvetica':
        print(f"✓ Русский шрифт загружен: {RUSSIAN_FONT}")
    else:
        print("⚠ Русский шрифт не найден, PDF может отображаться некорректно")

    if not PDF_AVAILABLE:
        print("⚠ reportlab не установлен. PDF не будет работать.")
        print("  Установите: pip install reportlab")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    try:
        Database.get_connection()
        print("✓ База данных подключена")
    except Error as e:
        QMessageBox.critical(None, "Ошибка",
                             f"Нет подключения к БД!\n\n{e}\n\n"
                             "Проверьте:\n1. Запущен ли MySQL\n2. Выполнен ли database.sql\n3. Пароль в DB_PASSWORD")
        sys.exit(1)

    login = LoginDialog()
    if login.exec() == QDialog.DialogCode.Accepted:
        user = login.current_user
        window = MainWindow(user)
        window.show()
        exit_code = app.exec()
        Database.close()
        sys.exit(exit_code)
    else:
        Database.close()
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"✗ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)