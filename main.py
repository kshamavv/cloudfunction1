import requests
from bs4 import BeautifulSoup
import re
import zipfile
import io
from google.cloud import storage
import logging


def create_folder(bucket_name, folder_name):
    """Creates a folder in the specified GCS bucket if it doesn't exist.

    Args:
        bucket_name (str): Name of the GCS bucket.
        folder_name (str): Name of the folder to create.
    """

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Check if folder already exists
    if not bucket.exists():
        logging.error(f"Bucket '{bucket_name}' does not exist.")
        raise ValueError(f"Bucket '{bucket_name}' does not exist.")

    blobs = list(client.list_blobs(bucket, prefix=folder_name + "/"))
    if not blobs:
        logging.info(f"Folder '{folder_name}' does not exist. Creating...")
        print(f"Folder '{folder_name}' does not exist. Creating...")  # For printing to console
        # Create the folder if it doesn't exist
        bucket.blob(folder_name + "/").upload_from_string("", content_type="application/octet-stream")


def fetch_and_upload_data(bucket_name, url):
    """Fetches data from the provided URL, extracts and uploads CSV files to GCS.

    Args:
        bucket_name (str): Name of the GCS bucket to upload files to.
        url (str): URL of the webpage containing data links.
    """

    logging.info("Fetching data from URL...")
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    links = soup.find_all('a', href=re.compile(r'/downloads/(t20s|tests|odis)_male_csv2.zip'))

    if links:
        logging.info("Data links found.")
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        for link in links:
            csv_url = 'https://cricsheet.org' + link['href']
            match_type = re.search(r'(t20s|tests|odis)', link['href']).group(0).capitalize()

            csv_response = requests.get(csv_url)
            zip_data = csv_response.content

            # Create folder in GCS if it doesn't exist
            create_folder(bucket_name, match_type)

            with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
                file_count = 0
                for file_name in zip_ref.namelist():
                    if file_name.endswith('.csv') and not file_name.endswith('_info.csv'):
                        dest_path = f"{match_type}/{file_name}"

                        # Upload the file to GCS
                        with io.BytesIO() as buffer:
                            buffer.write(zip_ref.read(file_name))
                            buffer.seek(0)
                            destination_blob = bucket.blob(dest_path)
                            destination_blob.upload_from_file(buffer)

                        logging.info(f"Uploaded {file_name} to folder {match_type}.")
                        print(f"Uploaded {file_name} to folder {match_type}.")  # For printing to console

                        file_count += 1

                        # Check and exit if 250 files are downloaded for the current match type
                        if file_count >= 250:
                            logging.info(f"250 files downloaded for {match_type}. Exiting.")
                            print(f"250 files downloaded for {match_type}. Exiting.")  # For printing to console
                            break

                    elif not file_name.endswith('.txt'):  # Exclude text files
                        logging.warning(f"Skipped {file_name} as it is not a CSV file.")
                        print(f"Skipped {file_name} as it is not a CSV file.")  # For printing to console

    else:
        logging.warning("No links found on the webpage.")
        print("No links found on the webpage.")


# Setup logging to capture errors only
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Replace with your GCS bucket name and desired URL
bucket_name = "test_surya_usecase"
url = 'https://cricsheet.org/downloads/#experimental'

# Fetch and upload data
fetch_and_upload_data(bucket_name, url)
