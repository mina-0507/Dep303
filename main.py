import sqlite3
import datetime
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QTextEdit, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class FinanceError(Exception):
    pass


class InvalidAmountError(FinanceError):
    pass


class EmptyDescriptionError(FinanceError):
    pass


class DatabaseError(FinanceError):
    pass


class Database:
    def __init__(self, db_name="finance.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        amount REAL NOT NULL,
                        description TEXT NOT NULL,
                        category TEXT NOT NULL,
                        date TEXT NOT NULL
                    )
                """)
        except sqlite3.Error as e:
            raise DatabaseError(f"Ошибка создания БД: {e}")

    def add_expense(self, amount, description, category, date):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO expenses (amount, description, category, date)
                    VALUES (?, ?, ?, ?)
                """, (amount, description, category, date))
        except sqlite3.Error as e:
            raise DatabaseError(f"Не удалось добавить запись: {e}")

    def get_all_expenses(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
                return cursor.fetchall()
        except sqlite3.Error as e:
            raise DatabaseError(f"Ошибка чтения данных: {e}")

    def delete_expense(self, expense_id):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        except sqlite3.Error as e:
            raise DatabaseError(f"Ошибка удаления: {e}")

    def get_statistics(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(amount) FROM expenses")
                total = cursor.fetchone()[0] or 0
                cursor.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
                by_category = cursor.fetchall()
                return total, by_category
        except sqlite3.Error as e:
            raise DatabaseError(f"Ошибка статистики: {e}")


class FinanceTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.categories = ["Еда", "Транспорт", "Жильё", "Развлечения", "Здоровье", "Другое"]
        self.init_ui()
        self.refresh_table()
        self.update_statistics()

    def init_ui(self):
        self.setWindowTitle("Финансовый трекер расходов")
        self.setGeometry(100, 100, 900, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel = QGroupBox("Добавить расход")
        left_layout = QVBoxLayout(left_panel)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Сумма (руб)")
        left_layout.addWidget(QLabel("Сумма:"))
        left_layout.addWidget(self.amount_input)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Например: Обед в кафе")
        left_layout.addWidget(QLabel("Описание:"))
        left_layout.addWidget(self.desc_input)

        left_layout.addWidget(QLabel("Категория:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.categories)
        left_layout.addWidget(self.category_combo)

        left_layout.addWidget(QLabel("Дата (ГГГГ-ММ-ДД):"))
        self.date_input = QLineEdit()
        self.date_input.setText(datetime.date.today().isoformat())
        left_layout.addWidget(self.date_input)

        self.add_btn = QPushButton("Добавить расход")
        self.add_btn.clicked.connect(self.add_expense)
        left_layout.addWidget(self.add_btn)
        left_layout.addStretch()

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        stats_group = QGroupBox("Статистика")
        stats_layout = QVBoxLayout(stats_group)
        self.total_label = QLabel("Общая сумма: 0 руб")
        self.total_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_layout.addWidget(self.total_label)

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(120)
        stats_layout.addWidget(self.stats_text)
        right_layout.addWidget(stats_group)

        table_group = QGroupBox("История расходов")
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Сумма", "Описание", "Категория", "Дата"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Удалить выбранное")
        self.delete_btn.clicked.connect(self.delete_expense)
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.refresh_all)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        table_layout.addLayout(btn_layout)

        right_layout.addWidget(table_group)
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=2)

    def add_expense(self):
        try:
            amount_str = self.amount_input.text().strip()
            if not amount_str:
                raise InvalidAmountError("Введите сумму")
            try:
                amount = float(amount_str)
                if amount <= 0:
                    raise InvalidAmountError("Сумма должна быть больше 0")
            except ValueError:
                raise InvalidAmountError("Сумма должна быть числом")

            description = self.desc_input.text().strip()
            if not description:
                raise EmptyDescriptionError("Описание не может быть пустым")

            category = self.category_combo.currentText()
            date = self.date_input.text().strip()

            try:
                datetime.datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise InvalidAmountError("Неверный формат даты. Используйте ГГГГ-ММ-ДД")

            self.db.add_expense(amount, description, category, date)
            QMessageBox.information(self, "Успех", "Расход добавлен")
            self.clear_inputs()
            self.refresh_all()

        except FinanceError as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def delete_expense(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите запись для удаления")
            return
        expense_id = int(self.table.item(current_row, 0).text())
        reply = QMessageBox.question(self, "Удаление", "Удалить выбранный расход?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.delete_expense(expense_id)
            self.refresh_all()

    def refresh_table(self):
        expenses = self.db.get_all_expenses()
        self.table.setRowCount(len(expenses))
        for i, exp in enumerate(expenses):
            for j, value in enumerate(exp):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

    def update_statistics(self):
        total, by_cat = self.db.get_statistics()
        self.total_label.setText(f"Общая сумма расходов: {total:.2f} руб")
        self.stats_text.clear()
        if by_cat:
            self.stats_text.append("По категориям:\n")
            for cat, summ in by_cat:
                self.stats_text.append(f"  - {cat}: {summ:.2f} руб")
        else:
            self.stats_text.append("Нет данных")

    def refresh_all(self):
        self.refresh_table()
        self.update_statistics()

    def clear_inputs(self):
        self.amount_input.clear()
        self.desc_input.clear()
        self.date_input.setText(datetime.date.today().isoformat())
        self.category_combo.setCurrentIndex(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FinanceTracker()
    window.show()
    sys.exit(app.exec())