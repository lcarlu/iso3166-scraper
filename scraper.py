from bs4 import BeautifulSoup
from requests_html import AsyncHTMLSession
import asyncio
import re
import pandas as pd
from datetime import date, datetime
import time
import logging
from unidecode import unidecode

RENDER_SLEEP = 5
BASE_URL = "https://www.iso.org/obp/ui/"
COUNTRY_CODES_COLLECTION_PAGE_ID = "#iso:pub:PUB500001:en"

COUNTRY_CODES_EXPECTED_COLUMNS = [
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

CODE_ELEMENTS_STATUSES_EXPECTED_COLUMNS = ["status_code", "status_text", "status"]
COUNTRY_CODES_COLLECTION_EXCEPTED_COLUMNS = [
    "alpha_2_code",
    "short_name_lower_case",
    "status_code",
    "page_id"
]

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
    style="%",
    datefmt="%Y-%m-%d %H:%M:%S", 
    level = logging.INFO
)

logger = logging.getLogger(__name__)

def none_if(expression_1: str, expression_2: str) -> (None | str):
    """
    The none_if() function returns None if two expressions are equal, otherwise it returns the first expression.
    """
    return None if expression_1 == expression_2 else expression_1

def async_measure_execution_time(async_func) :
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        res = await async_func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"{async_func.__name__} - elapsed time: {elapsed_time:.3f}s")
        return res

    return wrapper

def measure_execution_time(func) :
    def wrapper(*args, **kwargs):
        start_time = time.time()
        res = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"{func.__name__} - elapsed time: {elapsed_time:.3f}s")
        return res

    return wrapper

semaphore = asyncio.Semaphore(8)
async def fetch(session, url: str):

    async with semaphore:
        response = await session.get(url)
        await response.html.arender(sleep = RENDER_SLEEP, retries=8)

        logger.info(f"fetch: {url} response status code: {response.status_code}")
        logger.info(f"response text: {response.text}")

        return response

def to_snake_case(s: str) -> str:
  
  s = unidecode(s) # remove accents
  s = s.replace(',', '')

  return '_'.join(
    re.sub('([A-Z][a-z]+)', r' \1',
    re.sub('([A-Z]+)', r' \1',
    s.replace('-', ' '))).split()).lower()

@measure_execution_time
def parse_code_elements_statuses(html :str) -> list[dict[str, str]]:

    code_elements_statuses = []
    soup = BeautifulSoup(html, "html.parser")

    """
    Exemple in HTML
    <tr>
        <td class="grs-status2" width="5%"></td>
        <td align="left" width="95%">User-assigned code elements</td>
    </tr>
    <tr>
        <td class="grs-status2" width="5%"></td>
        <td align="left" width="95%">Exceptionally reserved code elements</td>
    </tr>
    """

    grs_grid_legend_table_rows = soup.find('table', class_ = 'grs-grid-legend').find_all('tr')

    for table_row in grs_grid_legend_table_rows:
        table_data = table_row.find_all('td')

        if len(table_data) == 2:
            status_code = table_data[0].get('class')[0]
            status_text = table_data[1].get_text()
            status = status_text.lower().strip().replace(' ', '-').replace('-code-elements', '')
            
            code_elements_statuses.append(
                {
                    'status_code' : status_code,
                    'status_text' : status_text,
                    'status' : status
                }
            )
    #logger.info(f"parsed_code_elements_statuses : {code_elements_statuses}")

    return code_elements_statuses

@measure_execution_time
def parse_country_codes_collection(html :str) -> list[dict[str, str]]:

    countries = []
    soup = BeautifulSoup(html, "html.parser")

    grs_grid_table_data = soup.find('table', class_ = 'grs-grid').find_all('td', class_ = re.compile("grs-status[0-9]"))

    for td in grs_grid_table_data:
        """
        <td class="grs-status1" title="United States of America (the)">
            <a href="#iso:code:3166:US" target="_blank">US</a>
        </td>
        """
        td_class = td.get('class')[0] # status
        td_title = td.get('title') # short_name_lower_case
        td_anchor = td.find('a')
        td_anchor_href = None # page_id
        td_anchor_text = None # alpha_2_code
        td_text = td.get_text() # alpha_2_code

        if td_anchor is not None:
            td_anchor_href = td_anchor.get('href')
            td_anchor_text = td_anchor.get_text()

        #logger.info(f"""class: {td_class}, title: {td_title}, td_anchor: {td_anchor}, anchor_href: {td_anchor_href}, anchor_text: {td_anchor_text}, td_text: {td_text}""")
        
        countries.append(
            {
                'alpha_2_code' : none_if(td_text,''),
                'short_name_lower_case': none_if(td_title.strip(),''),
                'status_code' : none_if(td_class,''),
                'page_id' : none_if(td_anchor_href,''),
            }
        )

    return countries

@measure_execution_time
def parse_core_view_summary(html :str, language :str ='en') -> dict[str,str]:

    if language not in ('en', 'fr'):
        raise Exception('Unexpected language')

    soup = BeautifulSoup(html, "html.parser")
    summary = {}
    
    fr_to_en = {
        "code_alpha_2" : "alpha_2_code",
        "nom_court" : "short_name",
        "forme_courte_du_nom_ecrite_en_minuscule" : "short_name_lower_case",
        "nom_complet" : "full_name",
        "code_alpha_3" : "alpha_3_code",
        "code_numerique": "numeric_code",
        "remarques" : "remarks",
        "independant" : "independent",
        "nom_de_territoire" : "territory_name",
        "statut" : "status",
        "remarque_concernant_le_statut" : "status_remark",
        "remarque_partie_1" : "remark_part_1",
        "remarque_partie_2" : "remark_part_2",
        "remarque_partie_3" : "remark_part_3",
        "code_alpha_4" : "alpha_4_code"
    }

    core_view_lines = soup.find('div', 'core-view-summary').find_all('div', 'core-view-line')

    for line in core_view_lines:
        core_view_field_name_div = line.find('div', 'core-view-field-name')
        core_view_field_value_div = line.find('div', 'core-view-field-value') 
        field_name = None if core_view_field_name_div is None else core_view_field_name_div.get_text()
        field_value = None if core_view_field_value_div is None else core_view_field_value_div.get_text()

        if field_name is not None:
            normalised_field_name = to_snake_case(field_name)

            if language == 'fr':
                normalised_field_name = fr_to_en[normalised_field_name]

            summary[normalised_field_name] = none_if(field_value,'')

    return summary

def generate_csv(input:list[dict[str, str]], filename:str, expected_columns:list[str]) -> None:

    today = date.today()
    df = pd.DataFrame.from_dict(input)
    df = df[*expected_columns]
    df.to_csv(f'./output/{today.strftime("%Y%m%d")}_{filename}.csv', sep='|', index=False, encoding='utf-8')

def generate_country_codes_collection(country_codes_collection :list[dict[str, str]]):
    generate_csv(country_codes_collection, 'country_codes_collection', COUNTRY_CODES_COLLECTION_EXCEPTED_COLUMNS)

def generate_code_elements_statuses(code_elements_statuses :list[dict[str, str]]):
    generate_csv(code_elements_statuses, 'code_elements_statuses', CODE_ELEMENTS_STATUSES_EXPECTED_COLUMNS)

def generate_country_codes(parsed_countries :list[dict[str, str]], language :str ='en'):
    generate_csv(parsed_countries, f'country-codes-{language}', COUNTRY_CODES_EXPECTED_COLUMNS)

@async_measure_execution_time
async def main() -> None:

    try:
        session = AsyncHTMLSession()

        response = await fetch(session, f"{BASE_URL}{COUNTRY_CODES_COLLECTION_PAGE_ID}")
        html = response.html.html
        #logger.info(f"html : {html}")
        
        code_elements_statuses = parse_code_elements_statuses(html)
        logger.info(f"{code_elements_statuses=}")

        country_codes_collection = parse_country_codes_collection(html)
        logger.info(f"{country_codes_collection[:5]=}")

        english_urls_tasks = []
        french_urls_tasks = []
        #spanish_urls_tasks = []
        #russian_urls_tasks = []

        for country in country_codes_collection[:20]:
            page_id = country.get("page_id")
            
            if page_id is not None:
                english_urls_tasks.append(fetch(session, f"{BASE_URL}{page_id}"))
                french_urls_tasks.append(fetch(session, f"{BASE_URL}fr/{page_id}"))
                #spanish_urls_tasks.append(fetch(session, f"{BASE_URL}es/{page_id}"))
                #russian_urls_tasks.append(fetch(session, f"{BASE_URL}ru/{page_id}"))

        logger.info(f"{len(english_urls_tasks)} countries to parse")

        english_urls_responses = await asyncio.gather(*english_urls_tasks)
        parsed_english_summaries = [parse_core_view_summary(r.html.html) for r in english_urls_responses]
        logger.info(f"{parsed_english_summaries[:5]=}")

        french_urls_responses = await asyncio.gather(*french_urls_tasks)
        parsed_french_summaries = [parse_core_view_summary(r.html.html, 'fr') for r in french_urls_responses]
        logger.info(f"{parsed_french_summaries[:5]=}")

        generate_code_elements_statuses(code_elements_statuses)
        generate_country_codes_collection(country_codes_collection)
        generate_country_codes(parsed_english_summaries, 'en')
        generate_country_codes(parsed_french_summaries, 'fr')

    except Exception as e:
        logger.error(e)

    finally:
        await session.close()

if __name__ == '__main__':

    asyncio.run(main())

    
    # Additional information
    # Expected fields : Administrative language(s) alpha-2 | Administrative language(s) alpha-3 | Local short name
    # Subdivisions
    # Excepted fields : Subdivision category | 3166-2 code | Subdivision name | Local variant | Language code | Romanization system | Parent subdivision
    # Change history of country code
    # Excepted fields : Effective date of change | Short description of change (en) | Short description of change (fr)
