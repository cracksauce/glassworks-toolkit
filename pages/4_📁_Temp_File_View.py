import streamlit as st
import os
from zipfile import ZipFile
import base64
from io import BytesIO


# Function to generate a link to download a file
def get_binary_file_downloader_html(bin_file, file_label="File"):
    with open(bin_file, "rb") as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href


# Function to zip files in a directory and return the zip file path
def zip_files(files, zip_name="tmp_files_backup.zip"):
    zip_path = os.path.join("/tmp", zip_name)
    with ZipFile(zip_path, "w") as zipf:
        for file in files:
            zipf.write(os.path.join("/tmp", file), file)
    return zip_path


# Streamlit interface
def main():
    st.title("Download Files from tmp Directory")

    # Path to the directory where files are stored
    tmp_dir = "/tmp"

    # List all files in the directory
    files = os.listdir(tmp_dir)

    # Filter out directories, leaving only files
    files = [f for f in files if os.path.isfile(os.path.join(tmp_dir, f))]

    # Display the list of files
    if files:
        st.write("Click on the file name to download it:")
        for file in files:
            # Display link for each file
            st.markdown(
                get_binary_file_downloader_html(os.path.join(tmp_dir, file), file),
                unsafe_allow_html=True,
            )

        # Zip and offer download for all files
        if st.button("Download All as Zip"):
            zip_path = zip_files(files)
            st.markdown(
                get_binary_file_downloader_html(zip_path, "All Files Zip"),
                unsafe_allow_html=True,
            )
    else:
        st.write("No files found in tmp directory.")


if __name__ == "__main__":
    main()
