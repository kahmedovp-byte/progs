import logging
import os
import re
import tempfile
import tkinter as tk
import unittest
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk


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
        line = line.strip()
        if not line:
            raise InvalidDataError("Пустая строка")

        match = re.fullmatch(
            r'"([^"]+)"\s+(\d{4})\.(\d{2})\.(\d{2})\s+(-?\d+(?:\.\d+)?)',
            line
        )
        if not match:
            raise InvalidDataError(
                'Строка должна быть в формате: "Ресурс" ГГГГ.ММ.ДД значение'
            )

        resource_type, year_text, month_text, day_text, value_text = match.groups()

        try:
            reading_date = date(
                int(year_text),
                int(month_text),
                int(day_text)
            )
        except ValueError as error:
            raise InvalidDataError(f"Некорректная дата: {error}") from error

        try:
            value = float(value_text)
        except ValueError as error:
            raise InvalidDataError("Некорректное числовое значение") from error

        return MeterReading(resource_type, reading_date, value)

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

    def save_to_file(self, filename: str):
        with open(filename, "w", encoding="utf-8") as file:
            for reading in self.readings:
                line = (
                    f'"{reading.resource_type}" '
                    f'{reading.reading_date.strftime("%Y.%m.%d")} '
                    f'{reading.value}\n'
                )
                file.write(line)

    def add_from_csv(self, csv_data: str):
        parts = [part.strip() for part in csv_data.split(";")]
        if len(parts) != 3:
            raise InvalidDataError(
                "ADD: нужно 3 поля: ресурс; дата; значение"
            )

        resource_type, date_text, value_text = parts
        raw_line = f'"{resource_type}" {date_text} {value_text}'
        reading = self.parse_line(raw_line)
        self.readings.append(reading)

    def remove_by_condition(self, condition: str):
        condition = condition.strip()

        match = re.fullmatch(
            r'(resource_type|reading_date|value)\s*(==|!=|<=|>=|<|>|contains)\s*(.+)',
            condition
        )
        if not match:
            raise InvalidDataError(
                "REM: неверное условие. Пример: value < 1000"
            )

        field_name, operator, raw_value = match.groups()
        raw_value = raw_value.strip()

        def check(reading: MeterReading) -> bool:
            if field_name == "value":
                try:
                    left = reading.value
                    right = float(raw_value)
                except ValueError as error:
                    raise InvalidDataError(
                        "REM: значение для поля value должно быть числом"
                    ) from error

                if operator == "==":
                    return left == right
                if operator == "!=":
                    return left != right
                if operator == "<":
                    return left < right
                if operator == ">":
                    return left > right
                if operator == "<=":
                    return left <= right
                if operator == ">=":
                    return left >= right
                raise InvalidDataError("REM: неподдерживаемый оператор для value")

            if field_name == "reading_date":
                try:
                    left = reading.reading_date
                    right = datetime.strptime(raw_value, "%Y.%m.%d").date()
                except ValueError as error:
                    raise InvalidDataError(
                        "REM: дата должна быть в формате ГГГГ.ММ.ДД"
                    ) from error

                if operator == "==":
                    return left == right
                if operator == "!=":
                    return left != right
                if operator == "<":
                    return left < right
                if operator == ">":
                    return left > right
                if operator == "<=":
                    return left <= right
                if operator == ">=":
                    return left >= right
                raise InvalidDataError(
                    "REM: неподдерживаемый оператор для reading_date"
                )

            if field_name == "resource_type":
                left = reading.resource_type
                right = raw_value

                if operator == "==":
                    return left == right
                if operator == "!=":
                    return left != right
                if operator == "contains":
                    return right.lower() in left.lower()

                raise InvalidDataError(
                    "REM: для resource_type поддерживаются только ==, !=, contains"
                )

            return False

        self.readings = [reading for reading in self.readings if not check(reading)]

    def execute_command(self, command_line: str):
        command_line = command_line.strip()
        if not command_line:
            return

        parts = command_line.split(maxsplit=1)
        command = parts[0].upper()
        argument = parts[1].strip() if len(parts) > 1 else ""

        if command == "ADD":
            self.add_from_csv(argument)
        elif command == "REM":
            self.remove_by_condition(argument)
        elif command == "SAVE":
            if not argument:
                raise InvalidDataError("SAVE: не указано имя файла")
            self.save_to_file(argument)
        else:
            raise InvalidDataError(f"Неизвестная команда: {command}")

    def apply_commands_file(self, filename: str):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        self.execute_command(line)
                    except InvalidDataError as error:
                        logging.error(
                            "[Файл команд: %s, Строка: %s] %s",
                            filename,
                            line_num,
                            error,
                        )
        except FileNotFoundError:
            logging.warning("Файл команд %s не найден.", filename)


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

        tk.Button(
            button_frame,
            text="Открыть данные",
            command=self.open_data_file,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_frame,
            text="Открыть команды",
            command=self.open_commands_file,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_frame,
            text="Сохранить данные",
            command=self.save_data_file,
        ).pack(side=tk.LEFT, padx=5)

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for reading in self.model.readings:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    reading.resource_type,
                    reading.reading_date.strftime("%Y.%m.%d"),
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
                    f'"{res_entry.get().strip()}" '
                    f'{date_entry.get().strip()} '
                    f'{value_entry.get().strip()}'
                )
                new_reading = self.model.parse_line(raw_line)
                self.model.readings.append(new_reading)
                self.refresh_table()
                dialog.destroy()
            except InvalidDataError as error:
                logging.error("[Ошибка ввода] %s", error)
                messagebox.showerror("Ошибка", str(error), parent=dialog)

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

    def open_data_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл данных",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return

        self.model.load_from_file(filename)
        self.refresh_table()

    def open_commands_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл команд",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return

        self.model.apply_commands_file(filename)
        self.refresh_table()
        messagebox.showinfo("Готово", "Команды применены")

    def save_data_file(self):
        filename = filedialog.asksaveasfilename(
            title="Сохранить данные",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return

        self.model.save_to_file(filename)
        messagebox.showinfo("Готово", "Данные сохранены")


class TestModel(unittest.TestCase):
    def setUp(self):
        self.model = MeterModel()

    def test_1_valid_line(self):
        line = '"Вода" 2024.01.10 45.5'
        result_reading = self.model.parse_line(line)
        self.assertEqual(result_reading.resource_type, "Вода")
        self.assertEqual(result_reading.reading_date, date(2024, 1, 10))
        self.assertEqual(result_reading.value, 45.5)

    def test_2_broken_date(self):
        line = '"Газ" 2024.13.01 10.0'
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_3_missing_quotes(self):
        line = "Свет 2024.01.01 100.0"
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_4_missing_value(self):
        line = '"Электричество" 2024.01.01 текст'
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_5_empty_line(self):
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("")

    def test_6_wrong_date_format(self):
        line = '"Вода" 2024-01-01 50.0'
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_7_add_command(self):
        self.model.execute_command("ADD Вода; 2024.03.28; 1200")
        self.assertEqual(len(self.model.readings), 1)
        self.assertEqual(self.model.readings[0].resource_type, "Вода")
        self.assertEqual(self.model.readings[0].value, 1200.0)

    def test_8_rem_command_for_value(self):
        self.model.execute_command("ADD Вода; 2024.03.28; 1200")
        self.model.execute_command("ADD Газ; 2024.03.28; 500")
        self.model.execute_command("REM value < 1000")

        self.assertEqual(len(self.model.readings), 1)
        self.assertEqual(self.model.readings[0].resource_type, "Вода")

    def test_9_rem_command_for_resource_type(self):
        self.model.execute_command("ADD Вода холодная; 2024.03.28; 1200")
        self.model.execute_command("ADD Газ; 2024.03.28; 500")
        self.model.execute_command("REM resource_type contains вода")

        self.assertEqual(len(self.model.readings), 1)
        self.assertEqual(self.model.readings[0].resource_type, "Газ")

    def test_10_save_to_file(self):
        self.model.execute_command("ADD Вода; 2024.03.28; 1200")

        with tempfile.TemporaryDirectory() as temp_dir:
            filename = os.path.join(temp_dir, "result.txt")
            self.model.save_to_file(filename)

            with open(filename, "r", encoding="utf-8") as file:
                content = file.read()

        self.assertIn('"Вода" 2024.03.28 1200.0', content)

    def test_11_apply_commands_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            commands_filename = os.path.join(temp_dir, "commands.txt")
            result_filename = os.path.join(temp_dir, "saved.txt")

            with open(commands_filename, "w", encoding="utf-8") as file:
                file.write("ADD Вода; 2024.03.28; 1200\n")
                file.write("ADD Газ; 2024.03.28; 500\n")
                file.write("REM value < 1000\n")
                file.write(f"SAVE {result_filename}\n")

            self.model.apply_commands_file(commands_filename)

            self.assertEqual(len(self.model.readings), 1)
            self.assertEqual(self.model.readings[0].resource_type, "Вода")
            self.assertTrue(os.path.exists(result_filename))


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