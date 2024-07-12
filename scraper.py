from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.service import Service
import os
import time
from datetime import datetime

"""
This file scrapes the government website and downloads import and export data. 
Both methods are nearly identical, dogshit duplicate code. But I'm never using it
again, so it's fine.
"""


def download_latest_hts_imports():
    print("Downloading latest HTS import data...")

    # Set up ChromeDriver and options
    download_dir = os.path.join(os.getcwd(), "data\\raw_hts\\imports")
    chrome_options = webdriver.ChromeOptions()
    chromedriver_binary_path = "chromedriver-win64/chromedriver.exe"
    prefs = {'download.default_directory': download_dir}
    chrome_options.add_experimental_option('prefs', prefs)
    # chrome_options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=chrome_options, service=Service(chromedriver_binary_path))
    print("Web driver ready, opening...")

    # URL of the target website
    url = "http://www.estadisticas.gobierno.pr/iepr/Publicaciones/Proyectosespeciales/ComercioExterno/Detalle.aspx"
    driver.get(url)
    print("Driver opened")

    # Wait until the necessary elements are present
    print("Waiting for page to load...")
    wait = WebDriverWait(driver, timeout=10)
    print("Page loaded")

    # Select option "All Products"
    print("Selecting 'All Products'...")
    all_options_id = 'dnn_ctr244936_import_export_htmltables_tv_codesn0CheckBox'
    dropdown = wait.until(ec.presence_of_element_located((By.ID, all_options_id)))
    dropdown.click()
    print("Done.")

    # Select option "Importaciones"
    print("Setting mode to import...")
    import_option_id = 'dnn_ctr244936_import_export_htmltables_rbl_IE_1'  # ID CAN CHANGE DEPENDING ON SITE UPDATES
    import_select = wait.until(ec.presence_of_element_located((By.ID, import_option_id)))
    import_select.click()
    print("Done.")

    # Trigger the download
    print("Downloading...")
    download_button_id = 'dnn_ctr244936_import_export_htmltables_btn_BajarDatos'
    download_button = wait.until(ec.element_to_be_clickable((By.ID, download_button_id)))
    download_button.click()

    # Function to wait for the download to complete
    def wait_for_download(directory, timeout=60):
        seconds = 0
        dl_wait = True
        while dl_wait and seconds < timeout:
            time.sleep(1)
            dl_wait = False
            for file_name in os.listdir(directory):
                if file_name.endswith('.crdownload'):
                    dl_wait = True
            seconds += 1
        return not dl_wait

    # Wait for the download to complete
    downloaded_filename = ''
    if wait_for_download(download_dir):

        files = sorted(
            [f for f in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, f))],
            key=lambda x: os.path.getmtime(os.path.join(download_dir, x)),
            reverse=True
        )
        print(f"Download completed: {files[0]}")
        downloaded_filename = files[0]
    else:
        print(f"Download did not complete in the expected time")

    # Close the browser
    driver.quit()

    if downloaded_filename:
        # Check if latest_hts exists
        if os.path.exists(os.path.join(download_dir, "latest_hts_imports.csv")):
            print(f"Newer HTS file downloaded, moving current to backup folder")

            # Move latest to back-up folder and append current date
            old_filename = os.path.join(download_dir, "latest_hts_imports.csv")

            # If backup does not exist, create it
            if os.path.exists(os.path.join(download_dir, "backups")):
                os.mkdir(os.path.join(download_dir, "backups"))

            new_filename = os.path.join(download_dir, "backups", f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv")
            os.rename(old_filename, new_filename)

        # Rename downloaded file to "latest_hts.csv"
        os.rename(os.path.join(download_dir, downloaded_filename), os.path.join(download_dir, 'latest_hts_imports.csv'))


def download_latest_hts_exports():
    print("Downloading latest HTS export data...")

    # Set up ChromeDriver and options
    download_dir = os.path.join(os.getcwd(), "data\\raw_hts\\exports")
    chrome_options = webdriver.ChromeOptions()
    chromedriver_binary_path = "chromedriver-win64/chromedriver.exe"
    prefs = {'download.default_directory': download_dir}
    chrome_options.add_experimental_option('prefs', prefs)
    # chrome_options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=chrome_options, service=Service(chromedriver_binary_path))
    print("Web driver ready, opening...")

    # URL of the target website
    url = "http://www.estadisticas.gobierno.pr/iepr/Publicaciones/Proyectosespeciales/ComercioExterno/Detalle.aspx"
    driver.get(url)
    print("Driver opened")

    # Wait until the necessary elements are present
    print("Waiting for page to load...")
    wait = WebDriverWait(driver, timeout=10)
    print("Page loaded")

    # Select option "All Products"
    print("Selecting 'All Products'...")
    all_options_id = 'dnn_ctr244936_import_export_htmltables_tv_codesn0CheckBox'
    dropdown = wait.until(ec.presence_of_element_located((By.ID, all_options_id)))
    dropdown.click()
    print("Done.")

    # Select option "Exportaciones"
    print("Setting mode to export...")
    import_option_id = 'dnn_ctr244936_import_export_htmltables_rbl_IE_0'  # ID CAN CHANGE DEPENDING SITE UPDATES
    import_select = wait.until(ec.presence_of_element_located((By.ID, import_option_id)))
    import_select.click()
    print("Done.")

    # Trigger the download
    print("Downloading...")
    download_button_id = 'dnn_ctr244936_import_export_htmltables_btn_BajarDatos'
    download_button = wait.until(ec.element_to_be_clickable((By.ID, download_button_id)))
    download_button.click()

    # Function to wait for the download to complete
    def wait_for_download(directory, timeout=60):
        seconds = 0
        dl_wait = True
        while dl_wait and seconds < timeout:
            time.sleep(1)
            dl_wait = False
            for file_name in os.listdir(directory):
                if file_name.endswith('.crdownload'):
                    dl_wait = True
            seconds += 1
        return not dl_wait

    # Wait for the download to complete
    downloaded_filename = ''
    if wait_for_download(download_dir):

        files = sorted(
            [f for f in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, f))],
            key=lambda x: os.path.getmtime(os.path.join(download_dir, x)),
            reverse=True
        )
        print(f"Download completed: {files[0]}")
        downloaded_filename = files[0]
    else:
        print(f"Download did not complete in the expected time")

    # Close the browser
    driver.quit()

    if downloaded_filename:
        # Check if latest_hts exists
        if os.path.exists(os.path.join(download_dir, "latest_hts_exports.csv")):
            print(f"Newer HTS file downloaded, moving current to backup folder")

            # Move latest to back-up folder and append current date
            old_filename = os.path.join(download_dir, "latest_hts_exports.csv")
            new_filename = os.path.join(download_dir, "backups",
                                        f"{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv")
            os.rename(old_filename, new_filename)

        # Rename downloaded file to "latest_hts.csv"
        os.rename(os.path.join(download_dir, downloaded_filename), os.path.join(download_dir, 'latest_hts_exports.csv'))
