#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
АИС Автосервис - Desktop приложение
Python + PyQt6 + MySQL
Пароли хранятся открытым текстом (для простоты)
"""

import sys
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

# ============================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ
# ИЗМЕНИТЕ ПОД СВОИ ДАННЫЕ!
# ============================================
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "12543hRGB2001"  # ВАШ ПАРОЛЬ К MYSQL
DB_NAME = "autoservice"


# ============================================
# КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
# ============================================
class Database:
    """Управление подключением к MySQL."""

    _connection = None

    @classmethod
    def get_connection(cls):
        """Получить соединение с БД."""
        try:
            if cls._connection is None or not cls._connection.is_connected():
                cls._connection = mysql.connector.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    autocommit=False,
                    charset='utf8mb4',
                    use_pure=True
                )
                print("✓ Подключение к БД установлено")
            else:
                cls._connection.ping(reconnect=True, attempts=3, delay=2)
            return cls._connection
        except Error as e:
            print(f"✗ Ошибка подключения к БД: {e}")
            raise

    @classmethod
    def execute_query(cls, query, params=None, fetch=True):
        """Выполнить SQL-запрос."""
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
            raise
        finally:
            cursor.close()

    @classmethod
    def close(cls):
        """Закрыть соединение."""
        if cls._connection and cls._connection.is_connected():
            cls._connection.close()
            cls._connection = None
            print("✓ Подключение к БД закрыто")


# ============================================
# АУТЕНТИФИКАЦИЯ (без хеширования)
# ============================================
def authenticate_user(username, password):
    """Проверка логина и пароля (открытым текстом)."""
    try:
        users = Database.execute_query(
            "SELECT * FROM users WHERE username = %s AND password = %s AND is_active = TRUE",
            (username, password)
        )
        if users:
            print(f"✓ Пользователь '{username}' авторизован")
            return users[0]
        print(f"✗ Неверный логин или пароль для '{username}'")
        return None
    except Error as e:
        print(f"✗ Ошибка аутентификации: {e}")
        return None


def register_user(username, password, full_name, role):
    """Регистрация нового пользователя."""
    try:
        # Проверяем, существует ли пользователь
        existing = Database.execute_query(
            "SELECT id FROM users WHERE username = %s",
            (username,)
        )
        if existing:
            return False, "Пользователь с таким логином уже существует!"

        # Создаём пользователя (пароль хранится открыто)
        Database.execute_query(
            """INSERT INTO users (username, password, full_name, role, is_active) 
               VALUES (%s, %s, %s, %s, TRUE)""",
            (username, password, full_name, role),
            fetch=False
        )

        print(f"✓ Пользователь '{username}' зарегистрирован")
        return True, "Регистрация успешна!"
    except Error as e:
        print(f"✗ Ошибка регистрации: {e}")
        return False, f"Ошибка: {e}"


# ============================================
# ОКНО ВХОДА И РЕГИСТРАЦИИ
# ============================================
class LoginDialog(QDialog):
    """Окно аутентификации и регистрации."""

    def __init__(self):
        super().__init__()
        self.current_user = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Автосервис Pro - Вход")
        self.setFixedSize(420, 350)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # Заголовок
        title = QLabel("🚗 АВТОСЕРВИС PRO")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 22px; 
            font-weight: bold; 
            color: #2c3e50; 
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 8px;
        """)
        main_layout.addWidget(title)

        # Вкладки Вход / Регистрация
        self.tabs = QTabWidget()

        # --- Вкладка ВХОД ---
        login_tab = QWidget()
        login_layout = QVBoxLayout()
        login_layout.setSpacing(12)

        login_form = QFormLayout()
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Введите логин")
        self.login_username.setMinimumHeight(38)
        self.login_username.setText("admin")  # Для удобства

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Введите пароль")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setMinimumHeight(38)
        self.login_password.setText("admin")  # Для удобства

        login_form.addRow("👤 Логин:", self.login_username)
        login_form.addRow("🔒 Пароль:", self.login_password)
        login_layout.addLayout(login_form)

        login_btn = QPushButton("🔑 ВОЙТИ")
        login_btn.clicked.connect(self.try_login)
        login_btn.setMinimumHeight(42)
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #219a52; }
        """)
        login_layout.addWidget(login_btn)
        login_tab.setLayout(login_layout)
        self.tabs.addTab(login_tab, "🔑 ВХОД")

        # --- Вкладка РЕГИСТРАЦИЯ ---
        register_tab = QWidget()
        register_layout = QVBoxLayout()
        register_layout.setSpacing(10)

        reg_form = QFormLayout()
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Придумайте логин (мин. 3 символа)")
        self.reg_username.setMinimumHeight(35)

        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Придумайте пароль (мин. 4 символа)")
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
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        register_layout.addWidget(register_btn)
        register_tab.setLayout(register_layout)
        self.tabs.addTab(register_tab, "📝 РЕГИСТРАЦИЯ")

        main_layout.addWidget(self.tabs)

        # Информация
        info_label = QLabel("По умолчанию: логин 'admin', пароль 'admin'")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        main_layout.addWidget(info_label)

        self.setLayout(main_layout)

        # Enter на кнопку входа
        self.login_password.returnPressed.connect(self.try_login)

    def try_login(self):
        """Попытка входа."""
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
            self.login_password.clear()
            self.login_password.setFocus()

    def try_register(self):
        """Попытка регистрации."""
        username = self.reg_username.text().strip()
        password = self.reg_password.text()
        password2 = self.reg_password2.text()
        full_name = self.reg_fullname.text().strip()
        role = self.reg_role.currentText()

        # Проверки
        if not username or not password or not full_name:
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля!")
            return

        if len(username) < 3:
            QMessageBox.warning(self, "Ошибка", "Логин должен быть не менее 3 символов!")
            return

        if len(password) < 4:
            QMessageBox.warning(self, "Ошибка", "Пароль должен быть не менее 4 символов!")
            return

        if password != password2:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают!")
            return

        # Регистрация
        success, message = register_user(username, password, full_name, role)

        if success:
            QMessageBox.information(self, "Успех",
                                    f"✅ Регистрация успешна!\n\n"
                                    f"👤 Логин: {username}\n"
                                    f"🔒 Пароль: {password}\n"
                                    f"👔 Роль: {role}\n\n"
                                    f"Теперь вы можете войти в систему.")

            # Очищаем поля
            self.reg_username.clear()
            self.reg_password.clear()
            self.reg_password2.clear()
            self.reg_fullname.clear()

            # Переключаем на вкладку входа
            self.tabs.setCurrentIndex(0)
            self.login_username.setText(username)
            self.login_password.setFocus()
        else:
            QMessageBox.critical(self, "Ошибка", message)


# ============================================
# МОДУЛЬ "КЛИЕНТЫ"
# ============================================
class ClientWidget(QWidget):
    """Виджет управления клиентами."""

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

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Тип", "ФИО/Компания", "Телефон", "Email", "Дата"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """)
        layout.addWidget(self.table)

        # Кнопки
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
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 20px;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 13px;
                }}
                QPushButton:hover {{ opacity: 0.85; }}
            """)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        """Загрузка списка клиентов."""
        try:
            rows = Database.execute_query(
                """SELECT id, type, full_name_or_company, phone, email, created_at 
                   FROM clients ORDER BY id DESC"""
            )
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                type_text = "Физ.лицо" if row['type'] == 'individual' else "Юр.лицо"
                self.table.setItem(i, 1, QTableWidgetItem(type_text))
                self.table.setItem(i, 2, QTableWidgetItem(row['full_name_or_company']))
                self.table.setItem(i, 3, QTableWidgetItem(row['phone'] or "-"))
                self.table.setItem(i, 4, QTableWidgetItem(row['email'] or "-"))
                created = row['created_at'].strftime('%d.%m.%Y') if row['created_at'] else "-"
                self.table.setItem(i, 5, QTableWidgetItem(created))
            print(f"✓ Загружено {len(rows)} клиентов")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить клиентов:\n{e}")

    def add_client(self):
        dialog = ClientDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_client(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите клиента для редактирования")
            return
        client_id = int(self.table.item(row, 0).text())
        dialog = ClientDialog(self.user, client_id=client_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_client(self):
        row = self.table.currentRow()
        if row < 0:
            return
        client_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 2).text()

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить клиента '{name}' и все связанные данные?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM clients WHERE id = %s", (client_id,), fetch=False)
                self.load_data()
                QMessageBox.information(self, "Успех", "Клиент удалён")
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить:\n{e}")


class ClientDialog(QDialog):
    """Диалог добавления/редактирования клиента."""

    def __init__(self, user, client_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.client_id = client_id
        self.setWindowTitle("Редактирование клиента" if client_id else "Новый клиент")
        self.setMinimumWidth(480)

        layout = QFormLayout()
        layout.setSpacing(12)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Физическое лицо", "individual")
        self.type_combo.addItem("Юридическое лицо", "legal")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Иванов Иван Иванович или ООО 'Ромашка'")
        self.name_edit.setMinimumHeight(32)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+7 (999) 123-45-67")
        self.phone_edit.setMinimumHeight(32)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("example@mail.ru")
        self.email_edit.setMinimumHeight(32)

        self.address_edit = QTextEdit()
        self.address_edit.setPlaceholderText("Город, улица, дом")
        self.address_edit.setMaximumHeight(65)

        self.inn_edit = QLineEdit()
        self.inn_edit.setPlaceholderText("ИНН (для юр.лиц)")

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Дополнительная информация")
        self.notes_edit.setMaximumHeight(65)

        layout.addRow("Тип клиента:", self.type_combo)
        layout.addRow("ФИО / Компания *:", self.name_edit)
        layout.addRow("Телефон:", self.phone_edit)
        layout.addRow("Email:", self.email_edit)
        layout.addRow("Адрес:", self.address_edit)
        layout.addRow("ИНН:", self.inn_edit)
        layout.addRow("Заметки:", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_client)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        if client_id:
            self.load_client_data()

    def load_client_data(self):
        try:
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
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{e}")

    def save_client(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО или название компании!")
            return

        try:
            if self.client_id:
                Database.execute_query(
                    """UPDATE clients 
                       SET type=%s, full_name_or_company=%s, phone=%s, 
                           email=%s, address=%s, inn=%s, notes=%s 
                       WHERE id=%s""",
                    (self.type_combo.currentData(), name,
                     self.phone_edit.text().strip() or None,
                     self.email_edit.text().strip() or None,
                     self.address_edit.toPlainText().strip() or None,
                     self.inn_edit.text().strip() or None,
                     self.notes_edit.toPlainText().strip() or None,
                     self.client_id),
                    fetch=False
                )
            else:
                Database.execute_query(
                    """INSERT INTO clients 
                       (type, full_name_or_company, phone, email, address, inn, notes) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (self.type_combo.currentData(), name,
                     self.phone_edit.text().strip() or None,
                     self.email_edit.text().strip() or None,
                     self.address_edit.toPlainText().strip() or None,
                     self.inn_edit.text().strip() or None,
                     self.notes_edit.toPlainText().strip() or None),
                    fetch=False
                )
            self.accept()
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")


# ============================================
# МОДУЛЬ "АВТОМОБИЛИ"
# ============================================
class VehicleWidget(QWidget):
    """Виджет управления автомобилями."""

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
        self.table.setHorizontalHeaderLabels([
            "ID", "Клиент", "Госномер", "Марка", "Модель", "Год", "Пробег"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
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
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 20px;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ opacity: 0.85; }}
            """)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        try:
            rows = Database.execute_query("""
                SELECT v.id, c.full_name_or_company AS client_name,
                       v.plate_number, v.brand, v.model, v.year, v.mileage
                FROM vehicles v 
                JOIN clients c ON v.client_id = c.id 
                ORDER BY v.id DESC
            """)
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['client_name']))
                self.table.setItem(i, 2, QTableWidgetItem(row['plate_number'] or "-"))
                self.table.setItem(i, 3, QTableWidgetItem(row['brand'] or "-"))
                self.table.setItem(i, 4, QTableWidgetItem(row['model'] or "-"))
                self.table.setItem(i, 5, QTableWidgetItem(str(row['year']) if row['year'] else "-"))
                self.table.setItem(i, 6, QTableWidgetItem(f"{row['mileage']:,} км" if row['mileage'] else "-"))
            print(f"✓ Загружено {len(rows)} автомобилей")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить:\n{e}")

    def add_vehicle(self):
        dialog = VehicleDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_vehicle(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите автомобиль")
            return
        vehicle_id = int(self.table.item(row, 0).text())
        dialog = VehicleDialog(self.user, vehicle_id=vehicle_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_vehicle(self):
        row = self.table.currentRow()
        if row < 0:
            return
        vehicle_id = int(self.table.item(row, 0).text())
        plate = self.table.item(row, 2).text()

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить автомобиль {plate}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM vehicles WHERE id = %s", (vehicle_id,), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить:\n{e}")


class VehicleDialog(QDialog):
    """Диалог автомобиля."""

    def __init__(self, user, vehicle_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.vehicle_id = vehicle_id
        self.setWindowTitle("Редактирование автомобиля" if vehicle_id else "Новый автомобиль")
        self.setMinimumWidth(450)

        layout = QFormLayout()
        layout.setSpacing(10)

        self.client_combo = QComboBox()
        self.load_clients()

        self.plate_edit = QLineEdit()
        self.plate_edit.setPlaceholderText("А123БВ 177")

        self.vin_edit = QLineEdit()
        self.vin_edit.setPlaceholderText("VIN-код")

        self.brand_edit = QLineEdit()
        self.brand_edit.setPlaceholderText("Toyota, BMW, LADA...")

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Camry, X5, Vesta...")

        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, datetime.now().year + 1)
        self.year_spin.setValue(datetime.now().year)

        self.mileage_spin = QSpinBox()
        self.mileage_spin.setRange(0, 9999999)
        self.mileage_spin.setSingleStep(1000)
        self.mileage_spin.setSuffix(" км")

        self.engine_edit = QLineEdit()
        self.engine_edit.setPlaceholderText("Бензин 2.0, Дизель 3.0...")

        layout.addRow("Клиент *:", self.client_combo)
        layout.addRow("Госномер:", self.plate_edit)
        layout.addRow("VIN:", self.vin_edit)
        layout.addRow("Марка:", self.brand_edit)
        layout.addRow("Модель:", self.model_edit)
        layout.addRow("Год выпуска:", self.year_spin)
        layout.addRow("Пробег:", self.mileage_spin)
        layout.addRow("Двигатель:", self.engine_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_vehicle)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        if vehicle_id:
            self.load_vehicle_data()

    def load_clients(self):
        try:
            clients = Database.execute_query(
                "SELECT id, full_name_or_company FROM clients ORDER BY full_name_or_company"
            )
            self.client_combo.clear()
            for c in clients:
                self.client_combo.addItem(c['full_name_or_company'], c['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить клиентов:\n{e}")

    def load_vehicle_data(self):
        try:
            data = Database.execute_query("SELECT * FROM vehicles WHERE id = %s", (self.vehicle_id,))
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
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить:\n{e}")

    def save_vehicle(self):
        client_id = self.client_combo.currentData()
        if not client_id:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента!")
            return

        try:
            if self.vehicle_id:
                Database.execute_query(
                    """UPDATE vehicles 
                       SET client_id=%s, plate_number=%s, vin=%s, brand=%s, 
                           model=%s, year=%s, mileage=%s, engine_type=%s 
                       WHERE id=%s""",
                    (client_id, self.plate_edit.text().strip(),
                     self.vin_edit.text().strip(), self.brand_edit.text().strip(),
                     self.model_edit.text().strip(), self.year_spin.value(),
                     self.mileage_spin.value(), self.engine_edit.text().strip(),
                     self.vehicle_id),
                    fetch=False
                )
            else:
                Database.execute_query(
                    """INSERT INTO vehicles 
                       (client_id, plate_number, vin, brand, model, year, mileage, engine_type) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (client_id, self.plate_edit.text().strip(),
                     self.vin_edit.text().strip(), self.brand_edit.text().strip(),
                     self.model_edit.text().strip(), self.year_spin.value(),
                     self.mileage_spin.value(), self.engine_edit.text().strip()),
                    fetch=False
                )
            self.accept()
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")


# ============================================
# МОДУЛЬ "ЗАКАЗ-НАРЯДЫ" (упрощённый)
# ============================================
class OrderWidget(QWidget):
    """Виджет заказ-нарядов."""

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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Клиент", "Авто", "Статус", "Итого", "Дата"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        for text, handler, color in [
            ("➕ Новый", self.add_order, "#27ae60"),
            ("✏️ Изменить", self.edit_order, "#2980b9"),
            ("🔄 Статус", self.change_status, "#e67e22"),
            ("🗑️ Удалить", self.delete_order, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 20px;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
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
                       CONCAT(v.brand, ' ', v.model) AS auto,
                       ro.status, ro.final_total, ro.created_at
                FROM repair_orders ro
                JOIN clients c ON ro.client_id = c.id
                JOIN vehicles v ON ro.vehicle_id = v.id
                ORDER BY ro.id DESC
            """)

            status_names = {
                'new': 'Новый', 'in_progress': 'В работе',
                'completed': 'Выполнен', 'closed': 'Закрыт', 'cancelled': 'Отменён'
            }

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['client']))
                self.table.setItem(i, 2, QTableWidgetItem(row['auto']))
                self.table.setItem(i, 3, QTableWidgetItem(status_names.get(row['status'], row['status'])))
                self.table.setItem(i, 4, QTableWidgetItem(f"{row['final_total']:.2f}"))
                created = row['created_at'].strftime('%d.%m.%Y %H:%M') if row['created_at'] else ""
                self.table.setItem(i, 5, QTableWidgetItem(created))
            print(f"✓ Загружено {len(rows)} заказов")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить:\n{e}")

    def add_order(self):
        dialog = OrderDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите заказ")
            return
        order_id = int(self.table.item(row, 0).text())
        dialog = OrderDialog(self.user, order_id=order_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def change_status(self):
        row = self.table.currentRow()
        if row < 0:
            return
        order_id = int(self.table.item(row, 0).text())

        statuses = ['new', 'in_progress', 'completed', 'closed', 'cancelled']
        status_names = ['Новый', 'В работе', 'Выполнен', 'Закрыт', 'Отменён']

        status, ok = QInputDialog.getItem(
            self, "Сменить статус", "Новый статус:", status_names, editable=False
        )
        if ok:
            new_status = statuses[status_names.index(status)]
            try:
                if new_status == 'closed':
                    # Расчёт суммы
                    labor = Database.execute_query(
                        "SELECT COALESCE(SUM(total),0) AS s FROM order_services WHERE order_id=%s",
                        (order_id,)
                    )[0]['s']
                    parts = Database.execute_query(
                        "SELECT COALESCE(SUM(total),0) AS s FROM order_parts WHERE order_id=%s",
                        (order_id,)
                    )[0]['s']
                    total = float(labor) + float(parts)

                    Database.execute_query(
                        """UPDATE repair_orders 
                           SET total_labor=%s, total_parts=%s, final_total=%s, status='closed', completed_at=NOW() 
                           WHERE id=%s""",
                        (labor, parts, total, order_id), fetch=False
                    )
                else:
                    Database.execute_query(
                        "UPDATE repair_orders SET status=%s WHERE id=%s",
                        (new_status, order_id), fetch=False
                    )
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сменить статус:\n{e}")

    def delete_order(self):
        row = self.table.currentRow()
        if row < 0:
            return
        order_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "Подтверждение", f"Удалить заказ #{order_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM repair_orders WHERE id=%s", (order_id,), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить:\n{e}")


class OrderDialog(QDialog):
    """Диалог заказ-наряда."""

    def __init__(self, user, order_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.order_id = order_id
        self.setWindowTitle("Заказ-наряд" if not order_id else f"Заказ #{order_id}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

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

        form.addRow("Клиент *:", self.client_combo)
        form.addRow("Автомобиль *:", self.vehicle_combo)
        form.addRow("Механик:", self.mechanic_combo)
        form.addRow("Описание:", self.desc_edit)
        layout.addLayout(form)

        # Таблицы услуг и запчастей
        tabs = QTabWidget()

        # Услуги
        sw = QWidget()
        sl = QVBoxLayout()
        self.services_table = QTableWidget()
        self.services_table.setColumnCount(3)
        self.services_table.setHorizontalHeaderLabels(["Услуга", "Часы", "Ставка"])
        self.services_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        sl.addWidget(self.services_table)
        add_s = QPushButton("➕ Добавить услугу")
        add_s.clicked.connect(lambda: self.add_row(self.services_table, ["", "1.0", "1000"]))
        sl.addWidget(add_s)
        sw.setLayout(sl)
        tabs.addTab(sw, "🔧 Услуги")

        # Запчасти
        pw = QWidget()
        pl = QVBoxLayout()
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(3)
        self.parts_table.setHorizontalHeaderLabels(["Запчасть", "Кол-во", "Цена"])
        self.parts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        pl.addWidget(self.parts_table)
        add_p = QPushButton("➕ Добавить запчасть")
        add_p.clicked.connect(lambda: self.add_row(self.parts_table, ["", "1", "500"]))
        pl.addWidget(add_p)
        pw.setLayout(pl)
        tabs.addTab(pw, "📦 Запчасти")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_order)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

        if order_id:
            self.load_order_data()

    def load_clients(self):
        try:
            clients = Database.execute_query(
                "SELECT id, full_name_or_company FROM clients ORDER BY full_name_or_company"
            )
            self.client_combo.clear()
            self.client_combo.addItem("-- Выберите --", None)
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
            self.vehicle_combo.addItem("-- Выберите --", None)
            for v in vehicles:
                self.vehicle_combo.addItem(v['info'], v['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_mechanics(self):
        try:
            mechanics = Database.execute_query(
                "SELECT id, full_name FROM employees WHERE position='механик'"
            )
            self.mechanic_combo.clear()
            self.mechanic_combo.addItem("-- Не назначен --", None)
            for m in mechanics:
                self.mechanic_combo.addItem(m['full_name'], m['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def add_row(self, table, defaults):
        row = table.rowCount()
        table.insertRow(row)
        for col, val in enumerate(defaults):
            table.setItem(row, col, QTableWidgetItem(val))

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

            # Услуги
            services = Database.execute_query("SELECT * FROM order_services WHERE order_id=%s", (self.order_id,))
            self.services_table.setRowCount(len(services))
            for i, s in enumerate(services):
                self.services_table.setItem(i, 0, QTableWidgetItem(s['custom_name'] or ""))
                self.services_table.setItem(i, 1, QTableWidgetItem(str(s['hours'])))
                self.services_table.setItem(i, 2, QTableWidgetItem(str(s['rate'])))

            # Запчасти
            parts = Database.execute_query(
                "SELECT op.*, pc.name FROM order_parts op JOIN parts_catalog pc ON op.part_id=pc.id WHERE op.order_id=%s",
                (self.order_id,)
            )
            self.parts_table.setRowCount(len(parts))
            for i, p in enumerate(parts):
                self.parts_table.setItem(i, 0, QTableWidgetItem(p['name']))
                self.parts_table.setItem(i, 1, QTableWidgetItem(str(p['quantity'])))
                self.parts_table.setItem(i, 2, QTableWidgetItem(str(p['unit_price'])))
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

        try:
            if self.order_id:
                Database.execute_query("DELETE FROM order_services WHERE order_id=%s", (self.order_id,), fetch=False)
                Database.execute_query("DELETE FROM order_parts WHERE order_id=%s", (self.order_id,), fetch=False)
                Database.execute_query(
                    "UPDATE repair_orders SET client_id=%s, vehicle_id=%s, mechanic_id=%s, description=%s WHERE id=%s",
                    (client_id, vehicle_id, mechanic_id, desc, self.order_id), fetch=False
                )
                order_id = self.order_id
            else:
                cursor = Database.get_connection().cursor()
                cursor.execute(
                    "INSERT INTO repair_orders (client_id, vehicle_id, mechanic_id, description, status) VALUES (%s,%s,%s,%s,'new')",
                    (client_id, vehicle_id, mechanic_id, desc)
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
                            (order_id, parts[0]['id'], int(qty.text()), float(price.text())), fetch=False
                        )

            self.accept()
            QMessageBox.information(self, "Успех", f"Заказ #{order_id} сохранён!")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# ============================================
# МОДУЛЬ "СКЛАД"
# ============================================
class InventoryWidget(QWidget):
    """Виджет склада."""

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
        self.table.setHorizontalHeaderLabels([
            "ID", "Наименование", "Артикул", "Цена розн.", "Остаток", "Мин."
        ])
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
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 20px;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
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
                qty = row['stock_quantity']
                qty_item = QTableWidgetItem(f"{qty} шт.")
                if qty <= row['min_stock']:
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
        part_id = int(self.table.item(row, 0).text())
        dialog = PartDialog(self.user, part_id=part_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def receive_part(self):
        row = self.table.currentRow()
        if row < 0:
            return
        part_id = int(self.table.item(row, 0).text())
        qty, ok = QInputDialog.getInt(self, "Приход", "Количество:", minValue=1, value=1)
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
        part_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(self, "Удаление", "Удалить запчасть?")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM parts_catalog WHERE id=%s", (part_id,), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", str(e))


class PartDialog(QDialog):
    """Диалог запчасти."""

    def __init__(self, user, part_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.part_id = part_id
        self.setWindowTitle("Запчасть")
        self.setMinimumWidth(400)

        layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.article_edit = QLineEdit()
        self.retail_spin = QDoubleSpinBox()
        self.retail_spin.setRange(0, 9999999)
        self.retail_spin.setDecimals(2)
        self.stock_spin = QSpinBox()
        self.stock_spin.setRange(0, 99999)
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 99999)
        self.min_spin.setValue(5)

        layout.addRow("Наименование *:", self.name_edit)
        layout.addRow("Артикул:", self.article_edit)
        layout.addRow("Цена розн.:", self.retail_spin)
        layout.addRow("Остаток:", self.stock_spin)
        layout.addRow("Мин.остаток:", self.min_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
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
                    "UPDATE parts_catalog SET name=%s, article=%s, retail_price=%s, stock_quantity=%s, min_stock=%s WHERE id=%s",
                    (name, self.article_edit.text(), self.retail_spin.value(),
                     self.stock_spin.value(), self.min_spin.value(), self.part_id),
                    fetch=False
                )
            else:
                Database.execute_query(
                    "INSERT INTO parts_catalog (name, article, retail_price, stock_quantity, min_stock) VALUES (%s,%s,%s,%s,%s)",
                    (name, self.article_edit.text(), self.retail_spin.value(),
                     self.stock_spin.value(), self.min_spin.value()),
                    fetch=False
                )
            self.accept()
        except Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# ============================================
# МОДУЛЬ "ОТЧЁТЫ"
# ============================================
class ReportWidget(QWidget):
    """Виджет отчётов."""

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        title = QLabel("📊 ОТЧЁТЫ")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title)

        for text, handler in [
            ("💰 Выручка за месяц", self.revenue_report),
            ("👨‍🔧 Загрузка механиков", self.mechanics_report),
            ("📦 Продажи запчастей", self.parts_report),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(38)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 10px;
                    border: none;
                    border-radius: 5px;
                    font-size: 13px;
                    text-align: left;
                }
                QPushButton:hover { background-color: #2980b9; }
            """)
            layout.addWidget(btn)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setStyleSheet("font-family: 'Courier New'; font-size: 13px;")
        layout.addWidget(self.report_text)

        self.setLayout(layout)

    def revenue_report(self):
        try:
            data = Database.execute_query("""
                SELECT COALESCE(SUM(final_total),0) AS total, COUNT(*) AS cnt
                FROM repair_orders WHERE status='closed' 
                AND MONTH(completed_at)=MONTH(CURDATE()) AND YEAR(completed_at)=YEAR(CURDATE())
            """)
            d = data[0]
            self.report_text.setText(
                f"ВЫРУЧКА ЗА ТЕКУЩИЙ МЕСЯЦ\n{'=' * 40}\n"
                f"Закрыто заказов: {d['cnt']}\n"
                f"Общая выручка: {d['total']:.2f} руб.\n"
            )
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def mechanics_report(self):
        try:
            data = Database.execute_query("""
                SELECT e.full_name, COUNT(ro.id) AS cnt, COALESCE(SUM(ro.final_total),0) AS total
                FROM employees e
                LEFT JOIN repair_orders ro ON e.id=ro.mechanic_id AND ro.status IN ('completed','closed')
                WHERE e.position='механик'
                GROUP BY e.id, e.full_name
            """)
            text = "ЗАГРУЗКА МЕХАНИКОВ\n" + "=" * 40 + "\n"
            for d in data:
                text += f"{d['full_name']}: {d['cnt']} заказов, {d['total']:.2f} руб.\n"
            self.report_text.setText(text)
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
                GROUP BY pc.id, pc.name
                ORDER BY total DESC
            """)
            text = "ПРОДАННЫЕ ЗАПЧАСТИ (месяц)\n" + "=" * 40 + "\n"
            for d in data:
                text += f"{d['name']}: {d['qty']} шт., {d['total']:.2f} руб.\n"
            if not data:
                text += "Нет продаж за месяц.\n"
            self.report_text.setText(text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")


# ============================================
# ГЛАВНОЕ ОКНО
# ============================================
class MainWindow(QMainWindow):
    """Основное окно."""

    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.setWindowTitle(f"Автосервис Pro — {user['full_name']} ({user['role']})")
        self.setMinimumSize(1200, 750)

        central = QWidget()
        self.setCentralWidget(central)

        self.stack = QStackedWidget()

        # Боковое меню
        self.menu_list = QListWidget()
        self.menu_list.setMaximumWidth(200)
        self.menu_list.setStyleSheet("""
            QListWidget {
                background-color: #2c3e50;
                color: white;
                font-size: 14px;
                border: none;
            }
            QListWidget::item {
                padding: 14px 18px;
                border-bottom: 1px solid #34495e;
            }
            QListWidget::item:selected {
                background-color: #3498db;
            }
            QListWidget::item:hover {
                background-color: #34495e;
            }
        """)

        for item in ["👥 Клиенты", "🚗 Автомобили", "🔧 Заказ-наряды", "📦 Склад", "📊 Отчёты"]:
            self.menu_list.addItem(item)

        self.menu_list.setCurrentRow(0)
        self.menu_list.currentRowChanged.connect(self.switch_module)

        # Страницы
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

        # Статус-бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            f"👤 {self.current_user['full_name']} | "
            f"👔 {self.current_user['role']} | "
            f"📅 {datetime.now().strftime('%d.%m.%Y')}"
        )

        # Меню
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

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Проверка БД
    try:
        Database.get_connection()
        print("✓ База данных подключена")
    except Error as e:
        QMessageBox.critical(None, "Ошибка",
                             f"Нет подключения к БД!\n\n{e}\n\n"
                             "Проверьте:\n"
                             "1. Запущен ли MySQL\n"
                             "2. Выполнен ли database.sql\n"
                             "3. Правильный ли пароль в DB_PASSWORD")
        sys.exit(1)

    # Окно входа
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