from seleniumbase.core.sb_driver import DriverMethods
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from seleniumbase import Driver
import pandas as pd
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import argparse
import itertools
import time

from src.utils import measure_execution_time, save_file
from src.classes import Country, CodeElement, CodeElementStatus
from src.parser import parse_code_elements_statuses, parse_country_codes_collection, parse_country, extract_page_code
from src.config.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

def get_arguments():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--language", type=str, default='en', choices=['en', 'fr'], help="choose the language for the content of all files. Choice between fr and en (default = en)")
    parser.add_argument("--download", action=argparse.BooleanOptionalAction, default=True, help="Download all html file before parsing (default = True, use --no-download to disable)")
    parser.add_argument("--workers", type=int, default=3, help="number of parallel browser workers used to download country pages (default = 3)")
    parser.add_argument("--retries", type=int, default=3, help="number of attempts per country page before giving up (default = 3)")

    return parser.parse_args()

def get_uc_driver():
    return Driver(uc=True, headless=True)

COUNTRY_CODES_COLLECTION_EXCEPTED_COLUMNS: list[str] = [
    "alpha_2_code",
    "short_name_lower_case",
    "status",
    "page_id"
]

COUNTRIES_EXPECTED_COLUMNS: list[str] = [
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

SUBDIVISIONS_EXCEPTED_COLUMNS: list[str] = [
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

ADDITIONAL_INFORMATION_EXPECTED_COLUMNS: list[str] = [
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

    # wait for the element to load
    wait: WebDriverWait = WebDriverWait(driver, timeout=10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "grs-grid")))

    # Get the html from the page
    return driver.page_source

def get_country_html(driver, url: str, expected_alpha_2_code: str) -> str:

    driver.get(url)
    driver.refresh() # refresh the driver in order to change correctly the page source
    logger.debug(f"{driver.current_url=}")
    wait: WebDriverWait = WebDriverWait(driver, timeout=20)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "core-view-summary")))

    # The summary element can be present in the DOM before the Angular app
    # has finished rendering the requested country (it can briefly still show
    # the previous view), so wait until the rendered alpha-2 code actually
    # matches what was requested before trusting the page source.
    wait.until(lambda d: extract_page_code(d.page_source) == expected_alpha_2_code)

    return driver.page_source

def fetch_country_codes_collection_html(url: str, downloaded_files_dir: Path, download: bool) -> str:
    """
    Resolve the country codes collection page, reusing a previously
    downloaded file (checkpoint) when present so a crashed/retried run
    does not re-fetch it.
    """
    file_path: Path = downloaded_files_dir / "country_codes_collection.html"

    if download and file_path.exists():
        logger.info(f"{file_path} already downloaded, skipping fetch")
        return file_path.read_text(encoding="utf-8")

    driver: DriverMethods = get_uc_driver()
    try:
        html: str = get_country_codes_collection_html(driver, url)
    finally:
        driver.quit()

    if download:
        save_file(file_path, html)

    return html

def get_country_html_with_retries(url: str, expected_alpha_2_code: str, retries: int) -> str:

    last_error = WebDriverException(f"no attempt made for {url=}, retries={retries}")

    for attempt in range(1, retries + 1):
        driver = get_uc_driver()
        try:
            return get_country_html(driver, url, expected_alpha_2_code)
        except (TimeoutException, WebDriverException) as e:
            last_error = e
            logger.warning(f"[{expected_alpha_2_code}] attempt {attempt}/{retries} failed for {url=}: {e}")
            time.sleep(2 * attempt)
        finally:
            driver.quit()

    raise last_error

def fetch_country_html(
    code_element: CodeElement,
    base_url: str,
    downloaded_files_dir: Path,
    download: bool,
    retries: int
) -> Optional[str]:
    """
    Resolve a single country's HTML, reusing a previously downloaded file
    (checkpoint) when present so a crashed/retried run does not re-fetch it.
    Each retry attempt creates and disposes its own driver, so this can be
    called from worker threads.
    """
    page_id = code_element.page_id
    if page_id is None:
        return None

    # A handful of rows in the country codes collection table are withdrawn
    # ISO 3166-3 entries identified by a 4-letter code (e.g. "DDDE" for the
    # former East Germany) rather than a 2-letter alpha-2 code. That's still
    # fine here: get_country_html_with_retries only compares this value
    # against the fetched page's own first summary field (see
    # extract_page_code), whatever code length that field holds.
    alpha_2_code = code_element.alpha_2_code
    if alpha_2_code is not None and len(alpha_2_code) != 2:
        logger.debug(f"[{alpha_2_code}] code is not a 2-letter alpha-2 code, likely a withdrawn ISO 3166-3 entry")
    file_name = f"{alpha_2_code}.html"
    file_path = downloaded_files_dir / file_name

    if download and file_path.exists():
        logger.info(f"[{alpha_2_code}] already downloaded, skipping fetch")
        return file_path.read_text(encoding="utf-8")

    url: str = f"{base_url}{page_id}"
    logger.debug(f"[{alpha_2_code}] fetching {url=}")

    html: str = get_country_html_with_retries(url, alpha_2_code, retries)
    logger.info(f"[{alpha_2_code}] fetched")

    if download:
        save_file(file_path, html)

    return html

def get_all_countries_html(
    country_codes_collection: List[CodeElement],
    base_url: str,
    downloaded_files_dir: Path,
    download: bool,
    workers: int,
    retries: int
) -> List[str]:

    countries_html: List[str] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_country_html, code_element, base_url, downloaded_files_dir, download, retries): code_element
            for code_element in country_codes_collection
        }

        for future in as_completed(futures):
            code_element = futures[future]
            try:
                html = future.result()
                if html is not None:
                    countries_html.append(html)
            except Exception:
                logger.exception(f"[{code_element.alpha_2_code}] giving up after retries")

    return countries_html

def get_all_countries_subdivisions(countries: List[Country]) -> List[Dict[str, Any]]:
    subdivisions = [country.get_subdivisions() for country in countries]
    flattened_subdivisions = list(itertools.chain(*subdivisions))

    return flattened_subdivisions

def get_all_countries_additional_information(countries: List[Country]) -> List[Dict[str, Any]]:
    additional_information = [country.get_additional_information() for country in countries]
    flattened_additional_information = list(itertools.chain(*additional_information))
    return flattened_additional_information


def generate_csv(input: List[Dict[str, str]], file_path: Path, expected_columns: List[str]) -> None:

    df = pd.DataFrame.from_dict(input, dtype=str)
    df = df[expected_columns]

    file_path.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(file_path, sep='|', index=False, encoding='utf-8')
    logger.info(f"wrote {len(df)} rows to {file_path}")

@measure_execution_time
def main() -> None:

    BASE_URL = "https://www.iso.org/obp/ui/"
    COUNTRY_CODES_COLLECTION_PAGE_ID = "#iso:pub:PUB500001:en"
    DATA_DIR: Path = PROJECT_ROOT / "data"
    
    # Read input arguments
    arguments = get_arguments()
    logger.info(f"{arguments=}")

    country_codes_collection_url = f"{BASE_URL}{COUNTRY_CODES_COLLECTION_PAGE_ID}"

    start_date: date = date.today()
    formatted_start_date: str = start_date.strftime("%Y%m%d")
    downloaded_files_dir: Path = DATA_DIR / formatted_start_date / "downloaded_files" / arguments.language
    output_files_dir: Path = DATA_DIR / formatted_start_date / "output_files" / arguments.language

    try:
        country_codes_collection_html = fetch_country_codes_collection_html(
            country_codes_collection_url,
            downloaded_files_dir,
            arguments.download
        )

        # Parse the decoding table
        code_elements_statuses: List[CodeElementStatus] = parse_code_elements_statuses(country_codes_collection_html)
        logger.debug(f"{code_elements_statuses=}")

        # Parse the country codes collection
        country_codes_collection: List[CodeElement] = parse_country_codes_collection(country_codes_collection_html, code_elements_statuses)
        logger.info(f"{len(country_codes_collection)} country codes found")
        logger.debug(f"{country_codes_collection=}")

        countries: List[Country] = []
        failed_countries: List[str] = []

        # Change only the base url for the countries pages
        # The main page is not translated
        if arguments.language == "fr":
            BASE_URL: str = f"{BASE_URL}fr/"

        countries_html: List[str] = get_all_countries_html(
            country_codes_collection,
            BASE_URL,
            downloaded_files_dir,
            arguments.download,
            arguments.workers,
            arguments.retries
        )

        for html in countries_html:
            alpha_2_code = extract_page_code(html) or "UNKNOWN"
            try:
                countries.append(parse_country(html, arguments.language))
            except Exception:
                failed_countries.append(alpha_2_code)
                logger.exception(f"[{alpha_2_code}] failed to parse country page, skipping")

        if failed_countries:
            logger.warning(f"failed to parse {len(failed_countries)} countries: {failed_countries}")

        logger.info(f"parsed {len(countries)}/{len(countries_html)} countries")
        logger.debug(f"{countries=}")

        countries_subdivisions = get_all_countries_subdivisions(countries)
        countries_additional_information = get_all_countries_additional_information(countries)
        logger.debug(f"{countries_subdivisions=}")
        logger.debug(f"{countries_additional_information=}")

        # Generate csv files

        countries_file_path = output_files_dir / "countries.csv"
        country_codes_collection_file_path = output_files_dir / "country_codes_collection.csv"
        subdivisions_file_path = output_files_dir / "subdivisions.csv"
        additional_information_file_path = output_files_dir / "additional_information.csv"

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
            countries_additional_information,
            additional_information_file_path,
            ADDITIONAL_INFORMATION_EXPECTED_COLUMNS
        )

    except Exception:
        logger.exception("scraping run failed")
        raise

if __name__ == '__main__':
    main()