#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desktop-приложение АИС автосервиса
PyQt6 + MySQL
"""

import sys
import os
from datetime import datetime

# Отключаем предупреждения Qt
os.environ["QT_LOGGING_RULES"] = "*.debug=false;*.warning=false"

import mysql.connector
from mysql.connector import Error
import bcrypt

# Проверяем, что PyQt6 установлен
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget,
        QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
        QFormLayout, QTextEdit, QStackedWidget, QListWidget,
        QSpinBox, QDoubleSpinBox, QTabWidget, QFileDialog,
        QStatusBar, QGroupBox, QToolBar, QInputDialog, QDialogButtonBox
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QAction

    print("✓ PyQt6 загружен успешно")
except ImportError as e:
    print(f"✗ Ошибка импорта PyQt6: {e}")
    print("Установите PyQt6: pip install PyQt6")
    sys.exit(1)

# ============================================
# Настройки подключения к MySQL
# ============================================
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "12543hRGB2001"  # ЗАМЕНИТЕ НА СВОЙ ПАРОЛЬ
DB_NAME = "autoservice"


# ============================================
# Класс для работы с базой данных
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
                    collation='utf8mb4_unicode_ci',
                    use_pure=True  # Используем чистый Python-драйвер
                )
                print("✓ Новое подключение к БД установлено")
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
            print(f"  Запрос: {query}")
            print(f"  Параметры: {params}")
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
# Функции аутентификации
# ============================================
def authenticate_user(username, password):
    """Проверка логина и пароля."""
    try:
        users = Database.execute_query(
            "SELECT * FROM users WHERE username = %s AND is_active = TRUE",
            (username,)
        )
        if not users:
            print(f"✗ Пользователь '{username}' не найден")
            return None

        user = users[0]
        stored_hash = user['password_hash']

        # Проверяем и преобразуем хеш
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
        elif isinstance(stored_hash, bytearray):
            stored_hash = bytes(stored_hash)

        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            print(f"✓ Пользователь '{username}' авторизован")
            return user

        print(f"✗ Неверный пароль для '{username}'")
        return None
    except Error as e:
        print(f"✗ Ошибка аутентификации: {e}")
        return None


def log_audit(user_id, action, table_name, record_id, old_data=None, new_data=None):
    """Запись действия в журнал аудита."""
    try:
        Database.execute_query(
            """INSERT INTO audit_log 
               (user_id, action, table_name, record_id, old_data, new_data) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (user_id, action, table_name, record_id,
             str(old_data) if old_data else None,
             str(new_data) if new_data else None),
            fetch=False
        )
    except Error as e:
        print(f"✗ Ошибка аудита: {e}")


# ============================================
# Диалог входа в систему
# ============================================
class LoginDialog(QDialog):
    """Окно аутентификации."""

    def __init__(self):
        super().__init__()
        self.current_user = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Вход в систему «Автосервис»")
        self.setFixedSize(380, 220)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Заголовок
        title = QLabel("Автосервис Pro")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        # Поля ввода
        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Введите логин")
        self.username_edit.setMinimumHeight(30)
        self.username_edit.setText("admin")  # Для удобства тестирования

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Введите пароль")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setMinimumHeight(30)
        self.password_edit.setText("admin")  # Для удобства тестирования

        form.addRow("Логин:", self.username_edit)
        form.addRow("Пароль:", self.password_edit)
        layout.addLayout(form)

        # Кнопки
        btn_layout = QHBoxLayout()

        login_btn = QPushButton("Войти")
        login_btn.clicked.connect(self.try_login)
        login_btn.setMinimumHeight(35)
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)

        btn_layout.addWidget(login_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Привязка Enter
        self.password_edit.returnPressed.connect(self.try_login)
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)

    def try_login(self):
        """Попытка входа."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        try:
            user = authenticate_user(username, password)
            if user:
                self.current_user = user
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль!")
                self.password_edit.clear()
                self.password_edit.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка входа:\n{e}")


# ============================================
# Простой виджет-заглушка для тестирования
# ============================================
class SimpleWidget(QWidget):
    """Простой виджет для проверки работы GUI."""

    def __init__(self, title, user):
        super().__init__()
        self.user = user
        layout = QVBoxLayout()

        label = QLabel(title)
        label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        info = QLabel(f"Пользователь: {user['full_name']}\nРоль: {user['role']}")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        self.setLayout(layout)


# ============================================
# Модуль "Клиенты"
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

        # Заголовок
        title = QLabel("👥 Управление клиентами")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Таблица клиентов
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Тип", "ФИО/Компания", "Телефон", "Email"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Добавить")
        add_btn.clicked.connect(self.add_client)
        add_btn.setMinimumHeight(35)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { opacity: 0.9; }
        """)

        edit_btn = QPushButton("✏️ Редактировать")
        edit_btn.clicked.connect(self.edit_client)
        edit_btn.setMinimumHeight(35)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { opacity: 0.9; }
        """)

        delete_btn = QPushButton("🗑️ Удалить")
        delete_btn.clicked.connect(self.delete_client)
        delete_btn.setMinimumHeight(35)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { opacity: 0.9; }
        """)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_data(self):
        """Загрузка списка клиентов."""
        try:
            rows = Database.execute_query(
                """SELECT id, type, full_name_or_company, phone, email 
                   FROM clients ORDER BY id DESC"""
            )
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                type_text = "Физ.лицо" if row['type'] == 'individual' else "Юр.лицо"
                self.table.setItem(i, 1, QTableWidgetItem(type_text))
                self.table.setItem(i, 2, QTableWidgetItem(row['full_name_or_company']))
                self.table.setItem(i, 3, QTableWidgetItem(row['phone'] or ""))
                self.table.setItem(i, 4, QTableWidgetItem(row['email'] or ""))
            print(f"✓ Загружено {len(rows)} клиентов")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить клиентов:\n{e}")

    def add_client(self):
        """Добавление нового клиента."""
        dialog = ClientDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_client(self):
        """Редактирование клиента."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите клиента для редактирования")
            return
        client_id = int(self.table.item(row, 0).text())
        dialog = ClientDialog(self.user, client_id=client_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_client(self):
        """Удаление клиента."""
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
                Database.execute_query(
                    "DELETE FROM clients WHERE id = %s",
                    (client_id,), fetch=False
                )
                log_audit(self.user['id'], 'DELETE', 'clients', client_id,
                          new_data=f"Удалён клиент: {name}")
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
        self.setMinimumWidth(450)

        layout = QFormLayout()
        layout.setSpacing(10)

        # Тип клиента
        self.type_combo = QComboBox()
        self.type_combo.addItem("Физическое лицо", "individual")
        self.type_combo.addItem("Юридическое лицо", "legal")

        # Поля ввода
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Иванов Иван Иванович или ООО 'Ромашка'")

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+7 (999) 123-45-67")

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("example@mail.ru")

        self.address_edit = QTextEdit()
        self.address_edit.setPlaceholderText("Город, улица, дом")
        self.address_edit.setMaximumHeight(70)

        self.inn_edit = QLineEdit()
        self.inn_edit.setPlaceholderText("ИНН (для юридических лиц)")

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Дополнительная информация")
        self.notes_edit.setMaximumHeight(70)

        # Добавление полей
        layout.addRow("Тип клиента:", self.type_combo)
        layout.addRow("ФИО / Компания *:", self.name_edit)
        layout.addRow("Телефон:", self.phone_edit)
        layout.addRow("Email:", self.email_edit)
        layout.addRow("Адрес:", self.address_edit)
        layout.addRow("ИНН:", self.inn_edit)
        layout.addRow("Заметки:", self.notes_edit)

        # Кнопки
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
        """Загрузка данных клиента."""
        try:
            data = Database.execute_query(
                "SELECT * FROM clients WHERE id = %s",
                (self.client_id,)
            )
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
        """Сохранение клиента."""
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
# Модуль "Автомобили"
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

        title = QLabel("🚗 Управление автомобилями")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
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
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        for text, handler, color in [
            ("➕ Добавить", self.add_vehicle, "#27ae60"),
            ("✏️ Редактировать", self.edit_vehicle, "#2980b9"),
            ("🗑️ Удалить", self.delete_vehicle, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 15px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        """Загрузка списка автомобилей."""
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
                self.table.setItem(i, 2, QTableWidgetItem(row['plate_number'] or ""))
                self.table.setItem(i, 3, QTableWidgetItem(row['brand'] or ""))
                self.table.setItem(i, 4, QTableWidgetItem(row['model'] or ""))
                self.table.setItem(i, 5, QTableWidgetItem(str(row['year']) if row['year'] else ""))
                self.table.setItem(i, 6, QTableWidgetItem(f"{row['mileage']:,} км" if row['mileage'] else ""))
            print(f"✓ Загружено {len(rows)} автомобилей")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить автомобили:\n{e}")

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
        self.setMinimumWidth(400)

        layout = QFormLayout()

        self.client_combo = QComboBox()
        self.load_clients()

        self.plate_edit = QLineEdit()
        self.plate_edit.setPlaceholderText("А123БВ 177")

        self.vin_edit = QLineEdit()
        self.vin_edit.setPlaceholderText("17 символов VIN-кода")

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
        """Загрузка списка клиентов."""
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
        """Загрузка данных автомобиля."""
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
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{e}")

    def save_vehicle(self):
        """Сохранение автомобиля."""
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
# Модуль "Заказ-наряды" (упрощённый)
# ============================================
class OrderWidget(QWidget):
    """Виджет управления заказ-нарядами."""

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout()

        title = QLabel("🔧 Заказ-наряды")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
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
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        for text, handler, color in [
            ("➕ Новый заказ", self.add_order, "#27ae60"),
            ("✏️ Редактировать", self.edit_order, "#2980b9"),
            ("🔄 Сменить статус", self.change_status, "#e67e22"),
            ("🗑️ Удалить", self.delete_order, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 15px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        """Загрузка списка заказов."""
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
                'new': 'Новый',
                'in_progress': 'В работе',
                'completed': 'Выполнен',
                'closed': 'Закрыт',
                'cancelled': 'Отменён'
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
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить заказы:\n{e}")

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
        """Изменение статуса заказа."""
        row = self.table.currentRow()
        if row < 0:
            return

        order_id = int(self.table.item(row, 0).text())
        statuses = ['new', 'in_progress', 'completed', 'closed', 'cancelled']
        status_names = ['Новый', 'В работе', 'Выполнен', 'Закрыт', 'Отменён']

        status, ok = QInputDialog.getItem(
            self, "Сменить статус", "Выберите новый статус:",
            status_names, editable=False
        )

        if ok:
            new_status = statuses[status_names.index(status)]
            try:
                if new_status == 'closed':
                    self.close_order(order_id)

                Database.execute_query(
                    """UPDATE repair_orders 
                       SET status = %s, 
                           completed_at = %s 
                       WHERE id = %s""",
                    (new_status,
                     datetime.now() if new_status in ('completed', 'closed') else None,
                     order_id),
                    fetch=False
                )
                log_audit(self.user['id'], 'STATUS_CHANGE', 'repair_orders',
                          order_id, new_data=status)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сменить статус:\n{e}")

    def close_order(self, order_id):
        """Закрытие заказа."""
        try:
            # Подсчёт сумм
            labor = Database.execute_query(
                "SELECT COALESCE(SUM(total), 0) AS s FROM order_services WHERE order_id = %s",
                (order_id,)
            )[0]['s']
            parts = Database.execute_query(
                "SELECT COALESCE(SUM(total), 0) AS s FROM order_parts WHERE order_id = %s",
                (order_id,)
            )[0]['s']

            total = float(labor) + float(parts)

            # Списание запчастей
            order_parts = Database.execute_query(
                "SELECT part_id, quantity FROM order_parts WHERE order_id = %s",
                (order_id,)
            )
            for op in order_parts:
                Database.execute_query(
                    """UPDATE parts_catalog 
                       SET stock_quantity = stock_quantity - %s 
                       WHERE id = %s AND stock_quantity >= %s""",
                    (op['quantity'], op['part_id'], op['quantity']),
                    fetch=False
                )

            # Обновление заказа
            Database.execute_query(
                """UPDATE repair_orders 
                   SET total_labor = %s, total_parts = %s, final_total = %s, 
                       status = 'closed', completed_at = NOW() 
                   WHERE id = %s""",
                (labor, parts, total, order_id),
                fetch=False
            )

            QMessageBox.information(self, "Успех", f"Заказ #{order_id} закрыт!\nИтого: {total:.2f} руб.")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось закрыть заказ:\n{e}")

    def delete_order(self):
        row = self.table.currentRow()
        if row < 0:
            return
        order_id = int(self.table.item(row, 0).text())

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить заказ-наряд #{order_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM repair_orders WHERE id = %s", (order_id,), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить:\n{e}")


class OrderDialog(QDialog):
    """Диалог создания/редактирования заказ-наряда."""

    def __init__(self, user, order_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.order_id = order_id
        self.setWindowTitle("Заказ-наряд" if not order_id else f"Заказ-наряд #{order_id}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Основная информация
        form = QFormLayout()

        self.client_combo = QComboBox()
        self.load_clients()
        self.client_combo.currentIndexChanged.connect(self.load_vehicles)

        self.vehicle_combo = QComboBox()

        self.mechanic_combo = QComboBox()
        self.load_mechanics()

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Опишите проблему или необходимые работы...")
        self.desc_edit.setMaximumHeight(80)

        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, 100)
        self.discount_spin.setDecimals(1)
        self.discount_spin.setSuffix(" %")

        form.addRow("Клиент *:", self.client_combo)
        form.addRow("Автомобиль *:", self.vehicle_combo)
        form.addRow("Механик:", self.mechanic_combo)
        form.addRow("Описание:", self.desc_edit)
        form.addRow("Скидка:", self.discount_spin)

        layout.addLayout(form)

        # Таблицы услуг и запчастей (упрощённые)
        tabs = QTabWidget()

        # Услуги
        services_widget = QWidget()
        services_layout = QVBoxLayout()
        self.services_table = QTableWidget()
        self.services_table.setColumnCount(3)
        self.services_table.setHorizontalHeaderLabels(["Услуга", "Часы", "Ставка (руб/ч)"])
        self.services_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        services_layout.addWidget(self.services_table)

        add_service_btn = QPushButton("➕ Добавить услугу")
        add_service_btn.clicked.connect(self.add_service_row)
        services_layout.addWidget(add_service_btn)
        services_widget.setLayout(services_layout)
        tabs.addTab(services_widget, "🔧 Услуги")

        # Запчасти
        parts_widget = QWidget()
        parts_layout = QVBoxLayout()
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(3)
        self.parts_table.setHorizontalHeaderLabels(["Запчасть", "Кол-во", "Цена (руб)"])
        self.parts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        parts_layout.addWidget(self.parts_table)

        add_part_btn = QPushButton("➕ Добавить запчасть")
        add_part_btn.clicked.connect(self.add_part_row)
        parts_layout.addWidget(add_part_btn)
        parts_widget.setLayout(parts_layout)
        tabs.addTab(parts_widget, "📦 Запчасти")

        layout.addWidget(tabs)

        # Кнопки
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
            self.client_combo.addItem("-- Выберите клиента --", None)
            for c in clients:
                self.client_combo.addItem(c['full_name_or_company'], c['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить клиентов:\n{e}")

    def load_vehicles(self):
        self.vehicle_combo.clear()
        client_id = self.client_combo.currentData()
        if not client_id:
            return
        try:
            vehicles = Database.execute_query(
                """SELECT id, CONCAT(brand, ' ', model, ' (', plate_number, ')') AS info 
                   FROM vehicles WHERE client_id = %s""",
                (client_id,)
            )
            self.vehicle_combo.addItem("-- Выберите автомобиль --", None)
            for v in vehicles:
                self.vehicle_combo.addItem(v['info'], v['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить автомобили:\n{e}")

    def load_mechanics(self):
        try:
            mechanics = Database.execute_query(
                "SELECT id, full_name FROM employees WHERE position = 'механик' ORDER BY full_name"
            )
            self.mechanic_combo.clear()
            self.mechanic_combo.addItem("-- Не назначен --", None)
            for m in mechanics:
                self.mechanic_combo.addItem(m['full_name'], m['id'])
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить механиков:\n{e}")

    def add_service_row(self):
        row = self.services_table.rowCount()
        self.services_table.insertRow(row)
        self.services_table.setItem(row, 0, QTableWidgetItem("Новая услуга"))
        self.services_table.setItem(row, 1, QTableWidgetItem("1.0"))
        self.services_table.setItem(row, 2, QTableWidgetItem("1000"))

    def add_part_row(self):
        row = self.parts_table.rowCount()
        self.parts_table.insertRow(row)
        self.parts_table.setItem(row, 0, QTableWidgetItem("Новая запчасть"))
        self.parts_table.setItem(row, 1, QTableWidgetItem("1"))
        self.parts_table.setItem(row, 2, QTableWidgetItem("500"))

    def load_order_data(self):
        try:
            data = Database.execute_query("SELECT * FROM repair_orders WHERE id = %s", (self.order_id,))
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
            self.discount_spin.setValue(float(d['discount_percent']))

            # Загрузка услуг
            services = Database.execute_query(
                "SELECT * FROM order_services WHERE order_id = %s",
                (self.order_id,)
            )
            self.services_table.setRowCount(len(services))
            for i, s in enumerate(services):
                name = s['custom_name'] or f"Услуга #{s['service_id']}"
                self.services_table.setItem(i, 0, QTableWidgetItem(name))
                self.services_table.setItem(i, 1, QTableWidgetItem(str(s['hours'])))
                self.services_table.setItem(i, 2, QTableWidgetItem(str(s['rate'])))

            # Загрузка запчастей
            parts = Database.execute_query(
                """SELECT op.*, pc.name AS part_name 
                   FROM order_parts op 
                   JOIN parts_catalog pc ON op.part_id = pc.id 
                   WHERE op.order_id = %s""",
                (self.order_id,)
            )
            self.parts_table.setRowCount(len(parts))
            for i, p in enumerate(parts):
                self.parts_table.setItem(i, 0, QTableWidgetItem(p['part_name']))
                self.parts_table.setItem(i, 1, QTableWidgetItem(str(p['quantity'])))
                self.parts_table.setItem(i, 2, QTableWidgetItem(str(p['unit_price'])))
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить заказ:\n{e}")

    def save_order(self):
        client_id = self.client_combo.currentData()
        vehicle_id = self.vehicle_combo.currentData()

        if not client_id or not vehicle_id:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента и автомобиль!")
            return

        mechanic_id = self.mechanic_combo.currentData()
        desc = self.desc_edit.toPlainText()
        discount = self.discount_spin.value()

        try:
            if self.order_id:
                Database.execute_query("DELETE FROM order_services WHERE order_id = %s", (self.order_id,), fetch=False)
                Database.execute_query("DELETE FROM order_parts WHERE order_id = %s", (self.order_id,), fetch=False)
                Database.execute_query(
                    """UPDATE repair_orders 
                       SET client_id=%s, vehicle_id=%s, mechanic_id=%s, 
                           description=%s, discount_percent=%s 
                       WHERE id=%s""",
                    (client_id, vehicle_id, mechanic_id, desc, discount, self.order_id),
                    fetch=False
                )
                order_id = self.order_id
            else:
                cursor = Database.get_connection().cursor()
                cursor.execute(
                    """INSERT INTO repair_orders 
                       (client_id, vehicle_id, mechanic_id, description, discount_percent, status) 
                       VALUES (%s, %s, %s, %s, %s, 'new')""",
                    (client_id, vehicle_id, mechanic_id, desc, discount)
                )
                order_id = cursor.lastrowid
                Database.get_connection().commit()
                cursor.close()

            # Сохранение услуг
            for row in range(self.services_table.rowCount()):
                name = self.services_table.item(row, 0)
                hours = self.services_table.item(row, 1)
                rate = self.services_table.item(row, 2)
                if name and hours and rate and name.text().strip():
                    Database.execute_query(
                        """INSERT INTO order_services (order_id, custom_name, hours, rate) 
                           VALUES (%s, %s, %s, %s)""",
                        (order_id, name.text(), float(hours.text()), float(rate.text())),
                        fetch=False
                    )

            # Сохранение запчастей
            for row in range(self.parts_table.rowCount()):
                name = self.parts_table.item(row, 0)
                qty = self.parts_table.item(row, 1)
                price = self.parts_table.item(row, 2)
                if name and qty and price and name.text().strip():
                    parts = Database.execute_query(
                        "SELECT id FROM parts_catalog WHERE name = %s LIMIT 1",
                        (name.text(),)
                    )
                    if parts:
                        part_id = parts[0]['id']
                        Database.execute_query(
                            """INSERT INTO order_parts (order_id, part_id, quantity, unit_price) 
                               VALUES (%s, %s, %s, %s)""",
                            (order_id, part_id, int(qty.text()), float(price.text())),
                            fetch=False
                        )

            self.accept()
            QMessageBox.information(self, "Успех", f"Заказ #{order_id} сохранён!")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить заказ:\n{e}")


# ============================================
# Модуль "Склад запчастей"
# ============================================
class InventoryWidget(QWidget):
    """Виджет управления складом."""

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout()

        title = QLabel("📦 Склад запчастей и материалов")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Наименование", "Артикул", "Цена розн.", "Остаток", "Мин.остаток"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        for text, handler, color in [
            ("➕ Добавить", self.add_part, "#27ae60"),
            ("✏️ Редактировать", self.edit_part, "#2980b9"),
            ("📥 Приход", self.receive_part, "#8e44ad"),
            ("🗑️ Удалить", self.delete_part, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 15px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        try:
            rows = Database.execute_query(
                """SELECT id, name, article, retail_price, stock_quantity, min_stock 
                   FROM parts_catalog ORDER BY name"""
            )
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['name']))
                self.table.setItem(i, 2, QTableWidgetItem(row['article'] or ""))
                self.table.setItem(i, 3, QTableWidgetItem(f"{row['retail_price']:.2f}"))

                qty = row['stock_quantity']
                min_qty = row['min_stock']
                qty_item = QTableWidgetItem(f"{qty} шт.")
                if qty <= min_qty:
                    qty_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(i, 4, qty_item)
                self.table.setItem(i, 5, QTableWidgetItem(str(min_qty)))
            print(f"✓ Загружено {len(rows)} запчастей")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить склад:\n{e}")

    def add_part(self):
        dialog = PartDialog(self.user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_part(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите запчасть")
            return
        part_id = int(self.table.item(row, 0).text())
        dialog = PartDialog(self.user, part_id=part_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def receive_part(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите запчасть для прихода")
            return
        part_id = int(self.table.item(row, 0).text())
        part_name = self.table.item(row, 1).text()

        qty, ok = QInputDialog.getInt(
            self, "Приход запчасти",
            f"Количество для прихода '{part_name}':",
            minValue=1, value=1
        )
        if ok:
            try:
                Database.execute_query(
                    "UPDATE parts_catalog SET stock_quantity = stock_quantity + %s WHERE id = %s",
                    (qty, part_id), fetch=False
                )
                self.load_data()
                QMessageBox.information(self, "Успех", f"Приход {qty} шт. выполнен!")
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить приход:\n{e}")

    def delete_part(self):
        row = self.table.currentRow()
        if row < 0:
            return
        part_id = int(self.table.item(row, 0).text())
        part_name = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить запчасть '{part_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM parts_catalog WHERE id = %s", (part_id,), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить:\n{e}")


class PartDialog(QDialog):
    """Диалог запчасти."""

    def __init__(self, user, part_id=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.part_id = part_id
        self.setWindowTitle("Редактирование запчасти" if part_id else "Новая запчасть")
        self.setMinimumWidth(400)

        layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Масло моторное 5W-40")

        self.article_edit = QLineEdit()
        self.article_edit.setPlaceholderText("Артикул производителя")

        self.manufact_edit = QLineEdit()
        self.manufact_edit.setPlaceholderText("Shell, Bosch, Brembo...")

        self.unit_edit = QLineEdit("шт.")

        self.purchase_spin = QDoubleSpinBox()
        self.purchase_spin.setRange(0, 9999999)
        self.purchase_spin.setDecimals(2)
        self.purchase_spin.setPrefix("₽ ")

        self.retail_spin = QDoubleSpinBox()
        self.retail_spin.setRange(0, 9999999)
        self.retail_spin.setDecimals(2)
        self.retail_spin.setPrefix("₽ ")

        self.stock_spin = QSpinBox()
        self.stock_spin.setRange(0, 99999)

        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 99999)
        self.min_spin.setValue(5)

        layout.addRow("Наименование *:", self.name_edit)
        layout.addRow("Артикул:", self.article_edit)
        layout.addRow("Производитель:", self.manufact_edit)
        layout.addRow("Ед. измерения:", self.unit_edit)
        layout.addRow("Цена закупочная:", self.purchase_spin)
        layout.addRow("Цена розничная:", self.retail_spin)
        layout.addRow("Остаток:", self.stock_spin)
        layout.addRow("Мин. остаток:", self.min_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_part)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        if part_id:
            self.load_part_data()

    def load_part_data(self):
        try:
            data = Database.execute_query("SELECT * FROM parts_catalog WHERE id = %s", (self.part_id,))
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
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{e}")

    def save_part(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите наименование!")
            return

        try:
            if self.part_id:
                Database.execute_query(
                    """UPDATE parts_catalog 
                       SET name=%s, article=%s, manufacturer=%s, unit=%s, 
                           purchase_price=%s, retail_price=%s, 
                           stock_quantity=%s, min_stock=%s 
                       WHERE id=%s""",
                    (name, self.article_edit.text().strip(),
                     self.manufact_edit.text().strip(), self.unit_edit.text().strip(),
                     self.purchase_spin.value(), self.retail_spin.value(),
                     self.stock_spin.value(), self.min_spin.value(),
                     self.part_id),
                    fetch=False
                )
            else:
                Database.execute_query(
                    """INSERT INTO parts_catalog 
                       (name, article, manufacturer, unit, purchase_price, 
                        retail_price, stock_quantity, min_stock) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (name, self.article_edit.text().strip(),
                     self.manufact_edit.text().strip(), self.unit_edit.text().strip(),
                     self.purchase_spin.value(), self.retail_spin.value(),
                     self.stock_spin.value(), self.min_spin.value()),
                    fetch=False
                )
            self.accept()
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")


# ============================================
# Модуль "Отчёты"
# ============================================
class ReportWidget(QWidget):
    """Виджет отчётов."""

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        title = QLabel("📊 Отчёты и аналитика")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        reports_group = QGroupBox("Доступные отчёты")
        reports_layout = QVBoxLayout()

        for text, handler in [
            ("Выручка за текущий месяц", self.revenue_report),
            ("Загруженность механиков", self.mechanics_report),
            ("Движение запчастей", self.parts_movement),
            ("Должники по счетам", self.debt_report),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(35)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 10px;
                    border: none;
                    border-radius: 4px;
                    text-align: left;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            reports_layout.addWidget(btn)

        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        layout.addWidget(self.report_text)

        export_btn = QPushButton("📊 Экспорт в файл")
        export_btn.clicked.connect(self.export_report)
        export_btn.setMinimumHeight(35)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        layout.addWidget(export_btn)

        self.setLayout(layout)

    def revenue_report(self):
        try:
            data = Database.execute_query("""
                SELECT COALESCE(SUM(final_total), 0) AS total, COUNT(*) AS count
                FROM repair_orders 
                WHERE status = 'closed' 
                  AND MONTH(completed_at) = MONTH(CURDATE()) 
                  AND YEAR(completed_at) = YEAR(CURDATE())
            """)
            total = data[0]['total']
            count = data[0]['count']
            text = f"""
╔══════════════════════════════════╗
║  ВЫРУЧКА ЗА ТЕКУЩИЙ МЕСЯЦ        ║
╠══════════════════════════════════╣
║  Закрытых заказов: {count:<4}           ║
║  Общая выручка: {total:>10.2f} руб. ║
╚══════════════════════════════════╝
"""
            self.report_text.setText(text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def mechanics_report(self):
        try:
            data = Database.execute_query("""
                SELECT e.full_name, COUNT(ro.id) AS order_count,
                       COALESCE(SUM(ro.final_total), 0) AS total_revenue
                FROM employees e
                LEFT JOIN repair_orders ro ON e.id = ro.mechanic_id 
                    AND ro.status IN ('completed', 'closed')
                    AND MONTH(ro.completed_at) = MONTH(CURDATE())
                WHERE e.position = 'механик'
                GROUP BY e.id, e.full_name
            """)
            text = "ЗАГРУЖЕННОСТЬ МЕХАНИКОВ\n" + "=" * 40 + "\n"
            for d in data:
                text += f"{d['full_name']}: {d['order_count']} заказов, {d['total_revenue']:.2f} руб.\n"
            self.report_text.setText(text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def parts_movement(self):
        try:
            sold = Database.execute_query("""
                SELECT pc.name, SUM(op.quantity) AS total_qty,
                       SUM(op.total) AS total_amount
                FROM order_parts op
                JOIN parts_catalog pc ON op.part_id = pc.id
                JOIN repair_orders ro ON op.order_id = ro.id
                WHERE ro.status = 'closed' 
                  AND MONTH(ro.completed_at) = MONTH(CURDATE())
                GROUP BY pc.id, pc.name
                ORDER BY total_amount DESC
            """)
            text = "ПРОДАННЫЕ ЗАПЧАСТИ (месяц)\n" + "=" * 40 + "\n"
            for s in sold:
                text += f"{s['name']}: {s['total_qty']} шт., {s['total_amount']:.2f} руб.\n"
            if not sold:
                text += "Нет продаж за месяц.\n"
            self.report_text.setText(text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def debt_report(self):
        try:
            data = Database.execute_query("""
                SELECT i.id, c.full_name_or_company AS client, 
                       i.total_amount, i.issue_date, i.status
                FROM invoices i 
                JOIN clients c ON i.client_id = c.id
                WHERE i.status IN ('unpaid', 'partially_paid')
                ORDER BY i.issue_date DESC
            """)
            text = "ДОЛЖНИКИ ПО СЧЕТАМ\n" + "=" * 40 + "\n"
            for d in data:
                status_text = "Не оплачен" if d['status'] == 'unpaid' else "Частично"
                date_str = d['issue_date'].strftime('%d.%m.%Y') if d['issue_date'] else ""
                text += f"Счёт #{d['id']} от {date_str}: {d['client']} - {d['total_amount']:.2f} руб. ({status_text})\n"
            if not data:
                text += "Нет неоплаченных счетов.\n"
            self.report_text.setText(text)
        except Error as e:
            self.report_text.setText(f"Ошибка: {e}")

    def export_report(self):
        text = self.report_text.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "Информация", "Нет данных для экспорта")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", "report.txt",
            "Text files (*.txt);;All files (*.*)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                QMessageBox.information(self, "Успех", f"Отчёт сохранён в {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")


# ============================================
# Управление пользователями (для admin)
# ============================================
class UserManagementWidget(QWidget):
    """Виджет управления пользователями."""

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout()

        title = QLabel("👤 Управление пользователями")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Логин", "ФИО", "Роль", "Активен"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        for text, handler, color in [
            ("➕ Добавить", self.add_user, "#27ae60"),
            ("🔒 Сбросить пароль", self.reset_password, "#e67e22"),
            ("🚫 Блок/Разблок", self.toggle_active, "#8e44ad"),
            ("🗑️ Удалить", self.delete_user, "#c0392b")
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn.setMinimumHeight(35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 15px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_data(self):
        try:
            rows = Database.execute_query(
                "SELECT id, username, full_name, role, is_active FROM users ORDER BY id"
            )
            self.table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(r['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(r['username']))
                self.table.setItem(i, 2, QTableWidgetItem(r['full_name']))

                role_names = {
                    'admin': 'Администратор',
                    'manager': 'Менеджер',
                    'mechanic': 'Механик',
                    'accountant': 'Бухгалтер'
                }
                self.table.setItem(i, 3, QTableWidgetItem(role_names.get(r['role'], r['role'])))

                active_item = QTableWidgetItem("✅ Да" if r['is_active'] else "❌ Нет")
                if not r['is_active']:
                    active_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(i, 4, active_item)
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить пользователей:\n{e}")

    def add_user(self):
        username, ok1 = QInputDialog.getText(self, "Новый пользователь", "Логин:")
        if not ok1 or not username.strip():
            return

        password, ok2 = QInputDialog.getText(
            self, "Пароль", "Пароль:", echo=QLineEdit.EchoMode.Password
        )
        if not ok2 or not password:
            return

        full_name, ok3 = QInputDialog.getText(self, "ФИО", "Полное имя:")
        if not ok3:
            return

        roles = ["admin", "manager", "mechanic", "accountant"]
        role, ok4 = QInputDialog.getItem(self, "Роль", "Выберите роль:", roles, editable=False)
        if not ok4:
            return

        try:
            pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            Database.execute_query(
                """INSERT INTO users (username, password_hash, full_name, role) 
                   VALUES (%s, %s, %s, %s)""",
                (username.strip(), pw_hash, full_name.strip(), role),
                fetch=False
            )
            self.load_data()
            QMessageBox.information(self, "Успех", f"Пользователь '{username}' создан!")
        except Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать пользователя:\n{e}")

    def reset_password(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите пользователя")
            return
        user_id = int(self.table.item(row, 0).text())
        username = self.table.item(row, 1).text()

        new_password, ok = QInputDialog.getText(
            self, "Сброс пароля",
            f"Новый пароль для '{username}':",
            echo=QLineEdit.EchoMode.Password
        )
        if ok and new_password:
            try:
                pw_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                Database.execute_query(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (pw_hash, user_id), fetch=False
                )
                QMessageBox.information(self, "Успех", "Пароль изменён!")
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сменить пароль:\n{e}")

    def toggle_active(self):
        row = self.table.currentRow()
        if row < 0:
            return
        user_id = int(self.table.item(row, 0).text())
        username = self.table.item(row, 1).text()
        is_active = "✅ Да" in self.table.item(row, 4).text()

        action = "заблокировать" if is_active else "разблокировать"
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите {action} пользователя '{username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query(
                    "UPDATE users SET is_active = %s WHERE id = %s",
                    (not is_active, user_id), fetch=False
                )
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось изменить статус:\n{e}")

    def delete_user(self):
        row = self.table.currentRow()
        if row < 0:
            return
        user_id = int(self.table.item(row, 0).text())
        username = self.table.item(row, 1).text()

        if user_id == self.user['id']:
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить самого себя!")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить пользователя '{username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Database.execute_query("DELETE FROM users WHERE id = %s", (user_id,), fetch=False)
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить:\n{e}")


# ============================================
# Главное окно приложения
# ============================================
class MainWindow(QMainWindow):
    """Основное окно программы."""

    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.setWindowTitle(f"Автосервис Pro — {user['full_name']} ({user['role']})")
        self.setMinimumSize(1100, 700)

        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)

        # Стек для переключения модулей
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
                padding: 5px;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-radius: 5px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #3498db;
            }
            QListWidget::item:hover {
                background-color: #34495e;
            }
        """)

        # Пункты меню
        menu_items = [
            "👥 Клиенты",
            "🚗 Автомобили",
            "🔧 Заказ-наряды",
            "📦 Склад запчастей",
            "📊 Отчёты"
        ]
        if user['role'] == 'admin':
            menu_items.append("👤 Пользователи")

        for item in menu_items:
            self.menu_list.addItem(item)

        self.menu_list.setCurrentRow(0)
        self.menu_list.currentRowChanged.connect(self.switch_module)

        # Создание страниц
        self.pages = {
            'clients': ClientWidget(self.current_user),
            'vehicles': VehicleWidget(self.current_user),
            'orders': OrderWidget(self.current_user),
            'inventory': InventoryWidget(self.current_user),
            'reports': ReportWidget(self.current_user)
        }
        if user['role'] == 'admin':
            self.pages['users'] = UserManagementWidget(self.current_user)

        for page in self.pages.values():
            self.stack.addWidget(page)

        # Компоновка
        layout = QHBoxLayout()
        layout.addWidget(self.menu_list)
        layout.addWidget(self.stack)
        central.setLayout(layout)

        # Строка состояния
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            f"Пользователь: {self.current_user['full_name']} | "
            f"Роль: {self.current_user['role']} | "
            f"Дата: {datetime.now().strftime('%d.%m.%Y')}"
        )

        # Меню
        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")

        logout_action = QAction("Выйти из системы", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)

        file_menu.addSeparator()

        exit_action = QAction("Закрыть программу", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Помощь")
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def switch_module(self, index):
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if hasattr(page, 'load_data'):
            page.load_data()

    def logout(self):
        reply = QMessageBox.question(
            self, "Выход", "Вы действительно хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()

    def show_about(self):
        QMessageBox.about(
            self, "О программе",
            "Автосервис Pro v1.0\n\n"
            "АИС для управления автосервисом.\n"
            "© 2024"
        )


# ============================================
# Главная функция запуска
# ============================================
def main():
    """Точка входа в приложение."""
    print("=" * 50)
    print("Запуск АИС Автосервис Pro...")
    print("=" * 50)

    # Создание приложения Qt
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Проверка подключения к БД
    try:
        Database.get_connection()
        print("✓ Подключение к базе данных успешно")
    except Error as e:
        QMessageBox.critical(
            None, "Ошибка подключения",
            f"Не удалось подключиться к базе данных:\n{e}\n\n"
            "Проверьте:\n"
            "1. Запущен ли сервер MySQL\n"
            "2. Правильно ли указаны настройки подключения\n"
            "3. Выполнен ли SQL-скрипт для создания БД"
        )
        sys.exit(1)

    # Диалог входа
    login = LoginDialog()
    if login.exec() == QDialog.DialogCode.Accepted:
        user = login.current_user
        print(f"✓ Пользователь '{user['username']}' вошёл в систему")

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
        print(f"✗ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)