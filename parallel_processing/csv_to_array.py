# csv_to_array.py
import csv
import os
from dotenv import load_dotenv

load_dotenv()


def convert_csv_to_array(input_csv_path, output_python_path):
    data = []
    try:
        with open(input_csv_path, "r", encoding="utf-8") as input_file:
            csv_reader = csv.reader(input_file)
            for row in csv_reader:
                if row:
                    data.append(row[0])
    except UnicodeDecodeError as e:
        print(f"Error reading CSV file: {e}. Trying with ISO-8859-1 encoding...")
        try:
            with open(input_csv_path, "r", encoding="ISO-8859-1") as input_file:
                csv_reader = csv.reader(input_file)
                for row in csv_reader:
                    if row:
                        data.append(row[0])
        except Exception as e:
            print(f"Error reading CSV file with ISO-8859-1 encoding: {e}")
            return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    try:
        with open(output_python_path, "w") as data_file:
            data_file.write(f"data = {data}")
        print(f"Data successfully written to {output_python_path}")
    except Exception as e:
        print(f"Error writing data to Python file: {e}")


if __name__ == "__main__":
    input_csv_path = os.getenv("INPUT_FILE_PATH", "input.csv")
    output_python_path = os.getenv("DATA_PYTHON_PATH", "data.py")
    convert_csv_to_array(input_csv_path, output_python_path)
