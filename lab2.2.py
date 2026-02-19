import re
from datetime import date
import tkinter as tk
from tkinter import ttk


class MeterReading:
    def __init__(self, resource_type: str, color: str, reading_date: date, value: float):
        self.resource_type = resource_type
        self.color = color
        self.reading_date = reading_date
        self.value = value



def parse_meter_reading(line: str) -> MeterReading:
        strings = re.findall(r'"([^"]+)"', line)

        resource = strings[0]
        color = strings[1]

        y, m, d = map(int, re.search(r"(\d{4})\.(\d{2})\.(\d{2})", line).groups())
        reading_date = date(y, m, d)

        value = float(re.findall(r"\d+\.\d+", line)[-1])

        return MeterReading(resource, color, reading_date, value)


def load_from_file(filename: str):
    readings = []

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line != "":
                reading = parse_meter_reading(line)
                readings.append(reading)

    return readings


class MeterApp:

    def __init__(self, root, filename):
        self.root = root
        self.filename = filename
        self.readings = load_from_file(filename)

        self.root.title("Показания счетчиков")

        self.create_table()
        self.create_buttons()
        self.refresh_table()

    def create_table(self):
        self.tree = ttk.Treeview(
            self.root,
            columns=("resource","color", "date", "value"),
            show="headings"
        )

        self.tree.heading("resource", text="Тип ресурса")
        self.tree.heading("color", text="Цвет")
        self.tree.heading("date", text="Дата")
        self.tree.heading("value", text="Значение")

        self.tree.pack(fill=tk.BOTH, expand=True)

    def create_buttons(self):
        frame = tk.Frame(self.root)
        frame.pack()

        tk.Button(frame, text="Добавить",
                  command=self.add_reading).pack(side=tk.LEFT, padx=5)

        tk.Button(frame, text="Удалить",
                  command=self.delete_reading).pack(side=tk.LEFT, padx=5)

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for reading in self.readings:
            self.tree.insert(
                "",
                tk.END,
                values=(reading.resource_type,
                        reading.color,
                        reading.reading_date,
                        reading.value)
            )

    def add_reading(self):
        form = tk.Toplevel(self.root)
        form.title("Добавить")

        tk.Label(form, text="Тип ресурса:").grid(row=0, column=0)
        resource_entry = tk.Entry(form)
        resource_entry.grid(row=0, column=1)

        tk.Label(form, text="Цвет:").grid(row=1, column=0)
        color_entry = tk.Entry(form)
        color_entry.grid(row=1, column=1)

        tk.Label(form, text="Дата (гггг-мм-дд):").grid(row=2, column=0)
        date_entry = tk.Entry(form)
        date_entry.grid(row=2, column=1)

        tk.Label(form, text="Значение:").grid(row=3, column=0)
        value_entry = tk.Entry(form)
        value_entry.grid(row=3, column=1)

        def save():
            y, m, d = map(int, date_entry.get().split("-"))
            reading_date = date(y, m, d)
            value = float(value_entry.get())

            new_reading = MeterReading(
                resource_entry.get(),
                color_entry.get(),
                reading_date,
                value
            )

            self.readings.append(new_reading)
            self.refresh_table()
            form.destroy()

        tk.Button(form, text="Сохранить",
                  command=save).grid(row=4, column=0, columnspan=2)

    def delete_reading(self):
        selected = self.tree.selection()

        if selected:
            index = self.tree.index(selected[0])
            del self.readings[index]
            self.refresh_table()


if __name__ == "__main__":
    root = tk.Tk()
    app = MeterApp(root, "data.txt")
    root.mainloop()
