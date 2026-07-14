
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import Driver
import pandas as pd
from datetime import date
from pathlib import Path
from utils import measure_execution_time, save_file
from dataclasses import asdict
from classes import Country, CodeElement, CodeElementStatus
from typing import List, Dict, Any
from parser import parse_code_elements_statuses, parse_country_codes_collection, parse_country
from config.logger import get_logger
import argparse
import itertools

def get_arguments():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--language", type=str, default='en', choices=['en', 'fr'], help="choose the language for the content of all files. Choice between fr and en (default = en)")
    parser.add_argument("--download", action="store_true", help="Download all html file before parsing")

    return parser.parse_args()


logger = get_logger(__name__)

COUNTRIES_EXPECTED_COLUMNS = [
    "alpha_2_code",
    "alpha_3_code",
    "alpha_4_code",
    "numeric_code",
    "short_name",
    "short_name_lower_case",
    "full_name",
    "independent",
    "territory_name",
    "status",
    "status_remark",
    "remarks",
    "remark_part_1",
    "remark_part_2",
    "remark_part_3"
    ]

COUNTRY_CODES_COLLECTION_EXCEPTED_COLUMNS = [
    "alpha_2_code",
    "short_name_lower_case",
    "status",
    "page_id"
]

SUBDIVISIONS_EXCEPTED_COLUMNS = [
    "alpha_2_code",
    "alpha_3_code",
    "numeric_code",
    "subdivision_category",
    "subdivision_code",
    "subdivision_name",
    "local_variant",
    "language_code",
    "romanization_system",
    "parent_subdivision_code"
]

LANGUAGES_EXPECTED_COLUMNS = [
    "alpha_2_code",
    "alpha_3_code",
    "numeric_code",
    "administrative_language_alpha_2_code",
    "administrative_language_alpha_3_code",
    "local_short_name"
]

def get_country_codes_collection_html(driver, url: str) -> str:

    # open URL using UC mode with 6 second reconnect time to bypass initial detection
    # Pass the cloudfare challenge
    driver.uc_open_with_reconnect(url, reconnect_time=6)

    # attempt to click the CAPTCHA checkbox if present
    driver.uc_gui_click_captcha()
    #driver.save_screenshot("cloudflare-challenge.png")

    try:
        # Accept cookies
        wait = WebDriverWait(driver, 20)
        wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()

    except TimeoutException:
        # Cookie banner did not appear (e.g. already accepted) - safe to continue
        logger.debug("No cookie banner found within timeout, continuing")

    # take a screenshot of the current page and save it
    #driver.save_screenshot("cloudflare-challenge2.png")

    # wait for the element to load
    wait = WebDriverWait(driver, timeout=10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "grs-grid")))

    # Get the html from the page
    return driver.page_source

def get_country_html(driver, url: str) -> str:

    driver.get(url)
    driver.refresh() # refresh the driver in order to change correctly the page source
    logger.debug(f"{driver.current_url=}")
    wait = WebDriverWait(driver, timeout=20)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "core-view-summary")))
    return driver.page_source

def get_all_countries_subdivisions(countries: List[Country]) -> List[Dict[str, Any]]:
    subdivisions = [country.get_subdivisions() for country in countries]
    flattened_subdivisions = list(itertools.chain(*subdivisions))

    return flattened_subdivisions

def get_all_countries_languages(countries: List[Country]) -> List[Dict[str, Any]]:
    languages = [country.get_languages() for country in countries]
    flattened_languages = list(itertools.chain(*languages))
    return flattened_languages


def generate_csv(input: List[Dict[str, str]], file_path: Path, expected_columns: List[str]) -> None:

    df = pd.DataFrame.from_dict(input, dtype=str)
    logger.info(df.head(10))
    logger.info(df.shape)
    logger.info(f'{expected_columns=}')
    df = df[expected_columns]

    file_path.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(file_path, sep='|', index=False, encoding='utf-8')

@measure_execution_time
def main() -> None:

    BASE_URL = "https://www.iso.org/obp/ui/"
    COUNTRY_CODES_COLLECTION_PAGE_ID = "#iso:pub:PUB500001:en"
    DATA_DIR: Path = Path.cwd() / "iso3166_scraper" / "data"
    
    # Read input arguments
    arguments = get_arguments()
    logger.info(f"{arguments=}")

    country_codes_collection_url = f"{BASE_URL}{COUNTRY_CODES_COLLECTION_PAGE_ID}"

    start_date: date = date.today()
    formatted_start_date: str = start_date.strftime("%Y%m%d")
    downloaded_files_dir: Path = DATA_DIR / formatted_start_date / "downloaded_files" / arguments.language
    output_files_dir: Path = DATA_DIR / formatted_start_date / "output_files" / arguments.language

    driver = Driver(uc=True, headless=True)

    try:
        country_codes_collection_html = get_country_codes_collection_html(driver, country_codes_collection_url)

        # Save html content
        if arguments.download:
            save_file(downloaded_files_dir / f"country_codes_collection.html", country_codes_collection_html)

        # Parse the decoding table
        code_elements_statuses: List[CodeElementStatus] = parse_code_elements_statuses(country_codes_collection_html)
        logger.info(f"{code_elements_statuses=}")

        # Parse the country codes collection
        country_codes_collection: List[CodeElement] = parse_country_codes_collection(country_codes_collection_html, code_elements_statuses)
        logger.info(f"{country_codes_collection[:10]=}")

        countries_html: List[str] = []
        countries: List[Country] = []

        # Change only the base url for the countries pages
        # The main page is not translated
        if arguments.language == "fr":
            BASE_URL: str = f"{BASE_URL}fr/"

        """
        TODO : Optimize downloading with parallel execution
        https://stackoverflow.com/questions/42732958/python-parallel-execution-with-selenium
        """

        for code_element in country_codes_collection:
            page_id = code_element.page_id
            file_name = f"{code_element.alpha_2_code}.html"

            if page_id is not None:
                url: str = f"{BASE_URL}{page_id}"
                logger.debug(f"{url=}")
                html: str = get_country_html(driver, url)
                countries_html.append(html)

                if arguments.download:
                    save_file(downloaded_files_dir / file_name, html)

        for html in countries_html:
            country = parse_country(html, arguments.language)
            countries.append(country)

        logger.info(f"{countries=}")

        countries_subdivisions = get_all_countries_subdivisions(countries)
        logger.info(f"{countries_subdivisions=}")

        countries_languages = get_all_countries_languages(countries)
        logger.info(f"{countries_languages=}")

        # Generate csv files

        countries_file_path = output_files_dir / "countries.csv"
        country_codes_collection_file_path = output_files_dir / "country_codes_collection.csv"
        subdivisions_file_path = output_files_dir / "subdivisions.csv"
        languages_file_path = output_files_dir / "languages.csv"

        generate_csv(
            [asdict(c) for c in countries],
            countries_file_path,
            COUNTRIES_EXPECTED_COLUMNS
        )

        generate_csv(
            [asdict(c) for c in country_codes_collection],
            country_codes_collection_file_path,
            COUNTRY_CODES_COLLECTION_EXCEPTED_COLUMNS
        )

        generate_csv(
            countries_subdivisions,
            subdivisions_file_path,
            SUBDIVISIONS_EXCEPTED_COLUMNS
        )

        generate_csv(
            countries_languages,
            languages_file_path,
            LANGUAGES_EXPECTED_COLUMNS
        )

    except Exception as e:
        raise e
    
    finally:
        # close the browser and end the session
        driver.quit()
                
if __name__ == '__main__':
    main()