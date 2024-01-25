import os
import glob
import tempfile

def cleanup_temp_files():
    # Define the directory containing the temporary files.
    # This uses the standard temporary file directory for the current OS.
    temp_dir = tempfile.gettempdir()

    # Define the list of file suffixes to clean up.
    # Add or remove file suffixes based on your requirements.
    file_suffixes = ['.py', '.jsonl', '.csv']

    # Iterate through each file suffix and remove those files.
    for suffix in file_suffixes:
        # Construct the pattern to match the files.
        pattern = os.path.join(temp_dir, '*' + suffix)
        
        # Use glob to get all files matching the pattern.
        files = glob.glob(pattern)

        # Iterate over the list of filepaths & remove each file.
        for file in files:
            try:
                os.remove(file)
                print(f"Removed: {file}")
            except OSError as e:
                print(f"Error: {file} : {e.strerror}")

if __name__ == "__main__":
    cleanup_temp_files()
