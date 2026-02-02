from bs4 import BeautifulSoup
from classes import Country, CodeElement, CodeElementStatus, Subdivision, Change, Language
from typing import List, Dict
from utils import measure_execution_time, none_if, to_snake_case
import re
from pathlib import Path
import pandas as pd
from config.logger import get_logger

logger = get_logger(__name__)

@measure_execution_time
def parse_code_elements_statuses(html :str) -> List[CodeElementStatus]:

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
            class_name = table_data[0].get('class')[0]
            text = table_data[1].get_text()
            #status = status_text.lower().strip().replace(' ', '-').replace('-code-elements', '')
            
            code_elements_statuses.append(CodeElementStatus(class_name, text))
    #logger.info(f"parsed_code_elements_statuses : {code_elements_statuses}")

    return code_elements_statuses

@measure_execution_time
def parse_country_codes_collection(html :str, code_elements_statuses :List[CodeElementStatus]) -> List[CodeElement]:

    country_codes_collection :List[CodeElement] = []
    soup = BeautifulSoup(html, "html.parser")

    grs_grid_table_data = soup.find('table', class_ = 'grs-grid').find_all('td', class_ = re.compile("grs-status[0-9]"))

    for td in grs_grid_table_data:
        """
        <td class="grs-status1" title="United States of America (the)">
            <a href="#iso:code:3166:US" target="_blank">US</a>
        </td>
        """
        td_class_name = td.get('class')[0] # status code
        td_title = td.get('title') # short_name_lower_case
        td_anchor = td.find('a')
        td_anchor_href = None # page_id
        td_anchor_text = None # alpha_2_code
        td_text = td.get_text() # alpha_2_code

        if td_anchor is not None:
            td_anchor_href = td_anchor.get('href')
            #td_anchor_text = td_anchor.get_text()

        #logger.info(f"""class: {td_class_name}, title: {td_title}, td_anchor: {td_anchor}, anchor_href: {td_anchor_href}, anchor_text: {td_anchor_text}, td_text: {td_text}""")
        
        for code_element_status in code_elements_statuses:
            if code_element_status.class_name == td_class_name:
                td_class = code_element_status.text

        country_codes_collection.append(
            CodeElement(
                alpha_2_code = none_if(td_text,''),
                short_name_lower_case = none_if(td_title.strip(),''),
                status = none_if(td_class,''),
                page_id = none_if(td_anchor_href,'')

            )
        )

    return country_codes_collection

@measure_execution_time
def parse_country_summary(html :str, language :str ='en') -> Dict[str, str]:

    if language not in ['en', 'fr']:
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

    try:
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
        
    except Exception as e:
        logger.error(e)

    return summary

@measure_execution_time
def parse_country_subdivisions(html: str) -> List[Subdivision]:

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all('table')
    subdivisions: List[Subdivision] = []

    subdivisions_table = tables[-2]
    #subdivisions_table = soup.find('table', {"id": "subdivision"})
    #logger.info(f"{subdivisions_table=}")
    
    subdivisions_rows = subdivisions_table.find('tbody').find_all('tr')
    #logger.info(f"{subdivisions_rows=}")

    for subdivision_row in subdivisions_rows:
        subdivision_values = subdivision_row.find_all('td')
        #logger.info(f"{subdivision_values=}")

        subdivision = Subdivision(
            subdivision_category= none_if(subdivision_values[0].get_text(),''),
            subdivision_code= none_if(subdivision_values[1].get_text(),''),
            subdivision_name= none_if(subdivision_values[2].get_text(),''),
            local_variant= none_if(subdivision_values[3].get_text(),''),
            language_code= none_if(subdivision_values[4].get_text(),''),
            romanization_system= none_if(subdivision_values[5].get_text(),''),
            parent_subdivision_code= none_if(subdivision_values[6].get_text(),'')
        )

        #logger.info(f"{subdivision=}")
        subdivisions.append(subdivision)

    return subdivisions

@measure_execution_time
def parse_country_languages(html: str) -> List[Language]:

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all('table')
    languages: List[Language] = []

    languages_table = tables[-3]
    #logger.info(f"{languages_table=}")
    
    languages_rows = languages_table.find('tbody').find_all('tr')
    
    for language_row in languages_rows:
        language_values = language_row.find_all('td')
        #logger.info(f"{language_values=}")

        language = Language(
            administrative_language_alpha_2_code= none_if(language_values[0].get_text(),''),
            administrative_language_alpha_3_code= none_if(language_values[1].get_text(),''),
            local_short_name= none_if(language_values[2].get_text(),'')
        )

        #logger.info(f"{language=}")
        languages.append(language)

    return languages

@measure_execution_time
def parse_country_changes(html: str) -> List[Change]:
    
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all('table')
    changes: List[Change] = []

    # Last table of the country page
    changes_table = tables[-1]
    #logger.info(f"{changes_table=}")

    changes_rows = changes_table.find('tbody').find_all('tr')
    
    for change_row in changes_rows:
        change_values = change_row.find_all('td')
        #logger.info(f"{change_values=}")

        change = Change(
            effective_date= none_if(change_values[0].get_text(),''),
            short_description_en= none_if(change_values[1].get_text(),''),
            short_description_fr= none_if(change_values[2].get_text(),''),
        )

        #logger.info(f"{change=}")
        changes.append(change)

    return changes

@measure_execution_time
def parse_country(html: str, language :str ='en') -> Country:

    if language not in ['en', 'fr']:
        raise Exception('Unexpected language')
    
    summary: Dict[str, str] = parse_country_summary(html, language)
    languages: List[Language] = parse_country_languages(html)
    subdivisions: List[Subdivision] = parse_country_subdivisions(html)
    changes: List[Change] = parse_country_changes(html)

    logger.info(f"{summary=}")
    logger.info(f"{languages=}")
    logger.info(f"{subdivisions=}")
    logger.info(f"{changes=}")

    country = Country(
        alpha_2_code= summary.get('alpha_2_code'),
        alpha_3_code= summary.get('alpha_3_code'),
        alpha_4_code= summary.get('alpha_4_code'),
        numeric_code= summary.get('numeric_code'),
        short_name= summary.get('short_name'),
        short_name_lower_case= summary.get('short_name_lower_case'),
        full_name= summary.get('full_name'),
        independent= summary.get('independent'),
        territory_name= summary.get('territory_name'),
        status= summary.get('status'),
        status_remark= summary.get('status_remark'),
        remarks= summary.get('remarks'),
        remark_part_1= summary.get('remark_part_1'),
        remark_part_2= summary.get('remark_part_2'),
        remark_part_3= summary.get('remark_part_3'),
        languages= languages,
        subdivisions= subdivisions,
        changes= changes
    )
    
    logger.info(f"{country=}")
    
    return country

if __name__ == '__main__':

    cwd = Path.cwd()
    data_dir = cwd / "iso3166_scraper" / "data"

    html_files_path = list(data_dir.glob('*_fr.html'))
    logger.info(f"{html_files_path=}")

    countries = []
    for file_path in html_files_path[:2]:

        with open(file_path, 'r') as file:
            html = file.read()
            country: Country = parse_country(html, 'fr')
            countries.append(country.to_dict())
     
    df = pd.DataFrame(countries).to_csv(data_dir / 'countries.csv', index=False, sep='|')