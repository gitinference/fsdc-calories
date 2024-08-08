import os
import platform
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

"""
This file scrapes the government website and downloads import and export data.
Method returns a tuple of Pandas DataFrames.
"""


def get_hts_dataframe() -> (pd.DataFrame, pd.DataFrame):

    # Set up temporary directory for HTS data
    tmp_dir = TemporaryDirectory()

    # Set up ChromeOptions
    download_dir = tmp_dir.name
    chrome_options = webdriver.ChromeOptions()
    prefs = {'download.default_directory': download_dir}
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_argument('--headless=new')

    # Set up chromedriver depending on platform
    current_dir = Path(__file__).parent.absolute()
    current_system = platform.system()

    if current_system == 'Linux':
        driver = webdriver.Chrome(options=chrome_options)
    elif current_system == 'Windows':
        chromedriver_binary_path = str(current_dir / "chromedriver" / "chromedriver-win64" / "chromedriver.exe")
        driver = webdriver.Chrome(options=chrome_options, service=Service(chromedriver_binary_path))
    else:
        raise OSError(f"Unsupported OS: {current_system}")

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

    # Select option "Importaciones"
    print("Setting mode to import...")
    import_option_id = 'dnn_ctr244936_import_export_htmltables_rbl_IE_1'  # ID CAN CHANGE DEPENDING ON SITE UPDATES
    import_select = wait.until(ec.presence_of_element_located((By.ID, import_option_id)))
    import_select.click()

    # Trigger the download
    print("Downloading import data...")
    download_button_id = 'dnn_ctr244936_import_export_htmltables_btn_BajarDatos'
    download_button = wait.until(ec.element_to_be_clickable((By.ID, download_button_id)))
    download_button.click()

    # Select option "Exportaciones"
    print("Setting mode to export...")
    export_option_id = 'dnn_ctr244936_import_export_htmltables_rbl_IE_0'  # ID CAN CHANGE DEPENDING SITE UPDATES
    export_select = wait.until(ec.presence_of_element_located((By.ID, export_option_id)))
    export_select.click()

    # Trigger the download
    print("Downloading export data...")
    download_button_id = 'dnn_ctr244936_import_export_htmltables_btn_BajarDatos'
    download_button = wait.until(ec.element_to_be_clickable((By.ID, download_button_id)))
    download_button.click()

    # Function to wait for the download to complete
    def wait_for_download(directory, timeout=120):
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
    downloaded_files = []
    if wait_for_download(download_dir):

        files = sorted(
            [f for f in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, f))],
            reverse=True
        )
        print(f"Download completed: {files}")
        downloaded_files = files
    else:
        print(f"Download did not complete in the expected time")

    # Close the browser
    driver.quit()

    if downloaded_files:
        # Open HTS import/export data as DataFrames
        import_data = pd.read_csv(os.path.join(tmp_dir.name, downloaded_files[0]))
        export_data = pd.read_csv(os.path.join(tmp_dir.name, downloaded_files[1]))
    else:
        tmp_dir.cleanup()
        raise Exception("No downloaded files")

    tmp_dir.cleanup()
    return import_data, export_data


if __name__ == '__main__':
    print(get_hts_dataframe())
