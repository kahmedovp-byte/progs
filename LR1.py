import re
from datetime import date

class MeterReading:
    def __init__(self, resource_type: str, reading_date: date, value: float):
        self.resource_type = resource_type
        self.reading_date = reading_date
        self.value = value

    def __str__(self):
        return (
            f"Тип ресурса: {self.resource_type}\n"
            f"Дата: {self.reading_date}\n"
            f"Значение: {self.value}"
        )


def parse_meter_reading(input_string: str) -> MeterReading:
    resource_match = re.search(r'"([^"]+)"', input_string)
    resource_type = resource_match.group(1)

    date_match = re.search(r'(\d{4})\.(\d{2})\.(\d{2})', input_string)
    year, month, day = map(int, date_match.groups())
    reading_date = date(year, month, day)

    value_matches = re.findall(r'\d+\.\d+', input_string)
    value = float(value_matches[1])

    return MeterReading(resource_type, reading_date, value)


if __name__ == "__main__":
    print("Введите строку с показаниями счетчиков:")
    print('Пример: ПоказанияСчетчиков "Электроэнергия" 2026.02.07 1234.56')

    input_line = input()

    reading = parse_meter_reading(input_line)
    print("\nРезультат обработки:\n")
    print(reading)
