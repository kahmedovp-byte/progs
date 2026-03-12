import logging
import re
import tkinter as tk
import unittest
from datetime import date
from tkinter import ttk


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class InvalidDataError(Exception):

    pass


class MeterReading:


    def __init__(self, resource_type: str, reading_date: date, value: float):
        self.resource_type = resource_type
        self.reading_date = reading_date
        self.value = value
class MeterModel:

    def __init__(self):
        self.readings = []

    def parse_line(self, line: str) -> MeterReading:
        try:
            strings = re.findall(r'"([^"]+)"', line)
            if not strings:
                raise InvalidDataError("Тип ресурса должен быть в кавычках")

            resource = strings[0]

            date_match = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", line)
            if not date_match:
                raise InvalidDataError("Неверный формат даты (нужен ГГГГ.ММ.ДД)")

            year_value, month_value, day_value = map(int, date_match.groups())
            reading_date = date(year_value, month_value, day_value)

            after_date_part = line[date_match.end():].strip()
            value_match = re.search(r"(\d+\.\d+|\d+)", after_date_part)
            if not value_match:
                raise InvalidDataError("Числовое значение не найдено")

            value = float(value_match.group(1))

            return MeterReading(resource, reading_date, value)

        except InvalidDataError:
            raise
        except Exception as error:
            raise InvalidDataError(f"Ошибка парсинга: {error}") from error

    def load_from_file(self, filename: str):

        self.readings = []

        try:
            with open(filename, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        reading = self.parse_line(line)
                        self.readings.append(reading)
                    except InvalidDataError as error:
                        logging.error(
                            "[Файл: %s, Строка: %s] %s",
                            filename,
                            line_num,
                            error,
                        )
        except FileNotFoundError:
            logging.warning("Файл %s не найден.", filename)


class MeterView:

    def __init__(self, window, meter_model: MeterModel):
        self.root = window
        self.model = meter_model
        self.root.title("Учет ресурсов")
        self._init_ui()
        self.refresh_table()

    def _init_ui(self):
        self.tree = ttk.Treeview(
            self.root,
            columns=("res", "dat", "val"),
            show="headings",
        )
        self.tree.heading("res", text="Ресурс")
        self.tree.heading("dat", text="Дата")
        self.tree.heading("val", text="Значение")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        tk.Button(
            button_frame,
            text="Добавить запись",
            command=self.add_item_dialog,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_frame,
            text="Удалить выбранное",
            command=self.delete_item,
        ).pack(side=tk.LEFT, padx=5)

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for reading in self.model.readings:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    reading.resource_type,
                    reading.reading_date,
                    reading.value,
                ),
            )

    def add_item_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Новая запись")
        dialog.grab_set()

        tk.Label(dialog, text="Ресурс:").grid(row=0, column=0, padx=5, pady=5)
        res_entry = tk.Entry(dialog)
        res_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(dialog, text="Дата (ГГГГ.ММ.ДД):").grid(
            row=1,
            column=0,
            padx=5,
            pady=5,
        )
        date_entry = tk.Entry(dialog)
        date_entry.insert(0, date.today().strftime("%Y.%m.%d"))
        date_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(dialog, text="Значение:").grid(row=2, column=0, padx=5, pady=5)
        value_entry = tk.Entry(dialog)
        value_entry.grid(row=2, column=1, padx=5, pady=5)

        def save():
            try:
                raw_line = (
                    f'"{res_entry.get()}" '
                    f"{date_entry.get()} "
                    f"{value_entry.get()}"
                )
                new_reading = self.model.parse_line(raw_line)
                self.model.readings.append(new_reading)
                self.refresh_table()
                dialog.destroy()
            except InvalidDataError as error:
                logging.error("[Ошибка ввода] %s", error)

        tk.Button(dialog, text="Сохранить", command=save).grid(
            row=3,
            columnspan=2,
            pady=10,
        )

    def delete_item(self):
        selected = self.tree.selection()
        if selected:
            index_value = self.tree.index(selected[0])
            del self.model.readings[index_value]
            self.refresh_table()


class TestModel(unittest.TestCase):

    def setUp(self):
        self.model = MeterModel()

    def test_1_valid_line(self):
        """Проверка корректной строки."""
        line = '"Вода" 2024.01.10 45.5'
        result_reading = self.model.parse_line(line)
        self.assertEqual(result_reading.resource_type, "Вода")
        self.assertEqual(result_reading.value, 45.5)

    def test_2_broken_date(self):
        """Проверка строки с несуществующей датой."""
        line = '"Газ" 2024.13.01 10.0'
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_3_missing_quotes(self):
        """Проверка строки без кавычек у типа ресурса."""
        line = "Свет 2024.01.01 100.0"
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_4_missing_value(self):
        """Проверка строки без числового значения."""
        line = '"Электричество" 2024.01.01 текст_вместо_числа'
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_5_empty_line(self):
        """Проверка пустой строки."""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("")

    def test_6_wrong_date_format(self):
        """Проверка строки с неверным разделителем даты."""
        line = '"Вода" 2024-01-01 50.0'
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)


if __name__ == "__main__":
    print("\n" + "=" * 40)
    print("ВЫПОЛНЕНИЕ ПРОВЕРОЧНЫХ ТЕСТОВ")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestModel)
    test_result = unittest.TextTestRunner(verbosity=1).run(suite)
    print("=" * 40 + "\n")

    if test_result.wasSuccessful():
        app_root = tk.Tk()
        app_model = MeterModel()
        app_model.load_from_file("data3.txt")
        app = MeterView(app_root, app_model)
        app_root.mainloop()
    else:
        print("ОШИБКА: Тесты не пройдены. Исправьте модель перед запуском интерфейса.")