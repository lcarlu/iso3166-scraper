from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from src.utils import measure_execution_time, none_if, to_snake_case
from src.classes import Country, CodeElement, CodeElementStatus, Subdivision, Change, Language
from src.config.logger import get_logger

logger = get_logger(__name__)

@measure_execution_time
def parse_code_elements_statuses(html :str) -> List[CodeElementStatus]:

    code_elements_statuses: list[CodeElementStatus] = []
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
            code_elements_statuses.append(CodeElementStatus(class_name, text))

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
        td_text = td.get_text() # alpha_2_code

        if td_anchor is not None:
            td_anchor_href = td_anchor.get('href')

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

def extract_alpha_2_code(html: str) -> Optional[str]:
    """
    Lightweight, language-agnostic extraction of the alpha-2 code, which is
    always the summary table's first field. Used to verify a fetched country
    page actually rendered the requested country before trusting it, since
    the summary element can be present in the DOM before the SPA has
    finished rendering that country's data.
    """
    soup = BeautifulSoup(html, "html.parser")
    core_view_summary = soup.find('div', 'core-view-summary')
    if core_view_summary is None:
        return None

    first_line = core_view_summary.find('div', 'core-view-line')
    if first_line is None:
        return None

    value_div = first_line.find('div', 'core-view-field-value')
    return None if value_div is None else value_div.get_text().strip().upper()

@measure_execution_time
def parse_country_summary(html :str, language :str ='en', alpha_2_code: Optional[str] = None) -> Dict[str, str]:

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
        logger.error(f"[{alpha_2_code}] failed to parse country summary: {e}", exc_info=True)

    return summary

SUBDIVISION_COLUMN_COUNT = 7

@measure_execution_time
def parse_country_subdivisions(html: str, alpha_2_code: Optional[str] = None) -> List[Subdivision]:

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all('table')
    subdivisions: List[Subdivision] = []

    subdivisions_table = tables[-2]
    subdivisions_rows = subdivisions_table.find('tbody').find_all('tr')

    for subdivision_row in subdivisions_rows:
        subdivision_values = subdivision_row.find_all('td')

        if len(subdivision_values) < SUBDIVISION_COLUMN_COUNT:
            logger.warning(
                f"[{alpha_2_code}] skipping malformed subdivision row: "
                f"expected {SUBDIVISION_COLUMN_COUNT} columns, got {len(subdivision_values)} "
                f"({subdivision_row.get_text(strip=True)!r})"
            )
            continue

        subdivisions.append(
            Subdivision(
                subdivision_category= none_if(subdivision_values[0].get_text(),''),
                subdivision_code= none_if(subdivision_values[1].get_text(),''),
                subdivision_name= none_if(subdivision_values[2].get_text(),''),
                local_variant= none_if(subdivision_values[3].get_text(),''),
                language_code= none_if(subdivision_values[4].get_text(),''),
                romanization_system= none_if(subdivision_values[5].get_text(),''),
                parent_subdivision_code= none_if(subdivision_values[6].get_text(),'')
            )
        )

    return subdivisions

LANGUAGE_COLUMN_COUNT = 3

@measure_execution_time
def parse_country_languages(html: str, alpha_2_code: Optional[str] = None) -> List[Language]:

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all('table')
    languages: List[Language] = []

    languages_table = tables[-3]
    languages_rows = languages_table.find('tbody').find_all('tr')

    for language_row in languages_rows:
        language_values = language_row.find_all('td')

        if len(language_values) < LANGUAGE_COLUMN_COUNT:
            logger.warning(
                f"[{alpha_2_code}] skipping malformed language row: "
                f"expected {LANGUAGE_COLUMN_COUNT} columns, got {len(language_values)} "
                f"({language_row.get_text(strip=True)!r})"
            )
            continue

        languages.append(
            Language(
                administrative_language_alpha_2_code= none_if(language_values[0].get_text(),''),
                administrative_language_alpha_3_code= none_if(language_values[1].get_text(),''),
                local_short_name= none_if(language_values[2].get_text(),'')
            )
        )

    return languages

CHANGE_COLUMN_COUNT = 3

@measure_execution_time
def parse_country_changes(html: str, alpha_2_code: Optional[str] = None) -> List[Change]:

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all('table')
    changes: List[Change] = []

    # Last table of the country page
    changes_table = tables[-1]
    changes_rows = changes_table.find('tbody').find_all('tr')

    for change_row in changes_rows:
        change_values = change_row.find_all('td')

        if len(change_values) < CHANGE_COLUMN_COUNT:
            logger.warning(
                f"[{alpha_2_code}] skipping malformed change row: "
                f"expected {CHANGE_COLUMN_COUNT} columns, got {len(change_values)} "
                f"({change_row.get_text(strip=True)!r})"
            )
            continue

        changes.append(
            Change(
                effective_date= none_if(change_values[0].get_text(),''),
                short_description_en= none_if(change_values[1].get_text(),''),
                short_description_fr= none_if(change_values[2].get_text(),''),
            )
        )

    return changes

@measure_execution_time
def parse_country(html: str, language :str ='en') -> Country:

    if language not in ['en', 'fr']:
        raise Exception('Unexpected language')

    alpha_2_code = extract_alpha_2_code(html)

    summary: Dict[str, str] = parse_country_summary(html, language, alpha_2_code)
    languages: List[Language] = parse_country_languages(html, alpha_2_code)
    subdivisions: List[Subdivision] = parse_country_subdivisions(html, alpha_2_code)
    changes: List[Change] = parse_country_changes(html, alpha_2_code)

    logger.debug(f"[{alpha_2_code}] {summary=} {languages=} {subdivisions=} {changes=}")

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

    logger.info(
        f"[{alpha_2_code}] parsed country: {len(languages)} languages, "
        f"{len(subdivisions)} subdivisions, {len(changes)} changes"
    )

    return country