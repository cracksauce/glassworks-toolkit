import csv
import os
import tempfile

def convert_data_to_temp_file(data):
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.csv')
    try:
        csv_writer = csv.writer(temp_file)
        for item in data:
            csv_writer.writerow([item])
        temp_file.close()
        return temp_file.name  # Return the path of the temporary file
    except Exception as e:
        print(f"Error writing data to temporary file: {e}")
        return None

if __name__ == "__main__":
    data = ['MCQ1', 'MCQ2', 'MCQ3']  # Example data
    temp_file_path = convert_data_to_temp_file(data)
    if temp_file_path:
        print(f"Data successfully written to temporary file: {temp_file_path}")
