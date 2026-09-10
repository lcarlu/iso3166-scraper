from bs4.element import Tag, ResultSet
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from src.utils import measure_execution_time, none_if
from src.classes import Country, CodeElement, CodeElementStatus, Subdivision, Change, AdditionalInformation
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
        td_class = None # status

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

def extract_page_code(html: str) -> Optional[str]:
    """
    Lightweight, language-agnostic extraction of the summary table's first
    field. For current countries this is the alpha-2 code, but withdrawn
    ISO 3166-3 entries render a 4-letter code there instead (e.g. "DDDE").
    Either way it's the identifier that page is for, which is what callers
    actually need: verifying a fetched page rendered the requested entry
    before trusting it, since the summary element can be present in the DOM
    before the SPA has finished rendering that entry's data.
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
    summary: dict[str, Optional[str]] = {}

    alpha_2_code = short_name = short_name_lower_case = full_name = alpha_3_code = numeric_code = remarks = \
            independent = territory_name = status = status_remark = remark_part_1 = remark_part_2 = \
                 remark_part_3 = alpha_4_code = None

    try:
        core_view_lines = soup.find('div', 'core-view-summary').find_all('div', 'core-view-line')

        for line in core_view_lines:
            core_view_field_name_div = line.find('div', 'core-view-field-name')
            core_view_field_value_div = line.find('div', 'core-view-field-value') 
            field_name = None if core_view_field_name_div is None else core_view_field_name_div.get_text()
            field_value = None if core_view_field_value_div is None else core_view_field_value_div.get_text()

            if field_name is not None and field_value is not None and field_value != "":
                field_value = field_value.replace("*", "")
                match field_name:
                    case "Alpha-2 code" | "Code alpha-2":
                        alpha_2_code = none_if(field_value, '')  
                    case "Short name" | "Nom court":
                        short_name = none_if(field_value, '')
                    case "Short name lower case" | "Forme courte du nom écrite en minuscule":
                        short_name_lower_case = none_if(field_value, '')
                    case "Full name" | "Nom complet":
                        full_name = none_if(field_value, '')
                    case "Alpha-3 code" | "Code alpha-3":
                        alpha_3_code = none_if(field_value, '')
                    case "Numeric code" | "Code numérique":
                        numeric_code = none_if(field_value, '')
                    case "Remarks" | "Remarques":
                        remarks = none_if(field_value, '')
                    case "Independent" | "Indépendant":
                        independent = none_if(field_value, '')
                    case "Territory name" | "Nom du territoire":
                        territory_name = none_if(field_value, '')
                    case "Status" | "Statut":
                        status = none_if(field_value, '')
                    case "Status remark" | "Remarque concernant le statut":
                        status_remark = none_if(field_value, '')
                    case "Remark part 1" | "Remarque, partie 1":
                        remark_part_1 = none_if(field_value, '')
                    case "Remark part 2" | "Remarque, partie 2":
                        remark_part_2 = none_if(field_value, '')
                    case "Remark part 3" | "Remarque, partie 3":
                        remark_part_3 = none_if(field_value, '')
                    case "Alpha-4 code" | "Code alpha-4":
                        alpha_4_code = none_if(field_value, '')

        summary: dict[str, Optional[str]]  = {
            "alpha_2_code": alpha_2_code,
            "short_name": short_name,
            "short_name_lower_case": short_name_lower_case,
            "full_name": full_name,
            "alpha_3_code": alpha_3_code,
            "numeric_code": numeric_code,
            "remarks": remarks,
            "independent": independent,
            "territory_name": territory_name,
            "status": status,
            "status_remark": status_remark,
            "remark_part_1": remark_part_1,
            "remark_part_2": remark_part_2,
            "remark_part_3": remark_part_3,
            "alpha_4_code": alpha_4_code
        }

    except Exception as e:
        logger.error(f"[{alpha_2_code}] failed to parse country summary: {e}", exc_info=True)

    return summary

ADDITIONAL_INFORMATION_COLUMN_COUNT = 3

def parse_country_additional_information(html: str, alpha_2_code: Optional[str] = None) -> list[AdditionalInformation]:
    administrative_language_alpha_2_position = administrative_language_alpha_3_position = local_short_name_position = None

    soup = BeautifulSoup(html, "html.parser")
    additional_information_table: Optional[Tag] = soup.find('div', id='country-additional-info')
    additional_information_table_headers: ResultSet[Tag] = additional_information_table.find("thead").find_all("th")

    i = 0
    for header in additional_information_table_headers:
        match header.text:
            case "Administrative language(s) alpha-2" | "Code(s) langue(s) administrative(s) alpha-2":
                administrative_language_alpha_2_position = i
            case "Administrative language(s) alpha-3" | "Code(s) langue(s) administrative(s) alpha-3":
                administrative_language_alpha_3_position = i
            case "Local short name" | "Forme courte locale":
                local_short_name_position = i
        i += 1

    additional_information_table_body_rows = additional_information_table.find("tbody").find_all("tr")

    additional_information: List[AdditionalInformation] = []

    for row in additional_information_table_body_rows:
        data = row.find_all("td")

        if len(data) < ADDITIONAL_INFORMATION_COLUMN_COUNT:
            logger.warning(
                f"[{alpha_2_code}] skipping malformed additional information row: "
                f"expected {ADDITIONAL_INFORMATION_COLUMN_COUNT} columns, got {len(data)} "
                f"({row.get_text(strip=True)!r})"
            )
            continue

        additional_information.append(
            AdditionalInformation(administrative_language_alpha_2_code=data[administrative_language_alpha_2_position].get_text(),
                                  administrative_language_alpha_3_code=data[administrative_language_alpha_3_position].get_text(),
                                  local_short_name=data[local_short_name_position].get_text()))

    return additional_information

SUBDIVISION_COLUMN_COUNT = 7

@measure_execution_time
def parse_country_subdivisions(html: str, alpha_2_code: Optional[str] = None) -> List[Subdivision]:

    soup = BeautifulSoup(html, "html.parser")
    subdivisions: List[Subdivision] = []

    subdivision_category_position = subdivision_code_position = subdivision_name_position = local_variant_position = language_code_position = \
        romanization_system_position = parent_subdivision_code_position = None

    subdivisions_table: Optional[Tag] = soup.find('table', id='subdivision')
    subdivisions_table_headers: Optional[ResultSet[Tag]] = subdivisions_table.find("thead").find_all("th")

    i = 0
    for header in subdivisions_table_headers:
        match header.text:
            case "Subdivision category" | "Type de subdivision":
                subdivision_category_position = i
            case "3166-2 code" | "code ISO 3166-2":
                subdivision_code_position = i
            case "Subdivision name" | "Nom de subdivision":
                subdivision_name_position = i
            case "Local variant" | "Variante locale":
                local_variant_position = i
            case "Language code" | "Code langue":
                language_code_position = i
            case "Romanization system" | "Système de romanisation":
                romanization_system_position = i
            case "Parent subdivision" | "Subdivision-mère":
                parent_subdivision_code_position = i
        i += 1

    subdivisions_table_body_rows = subdivisions_table.find('tbody').find_all("tr")
    
    for subdivision_row in subdivisions_table_body_rows:
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
                subdivision_category= none_if(subdivision_values[subdivision_category_position].get_text(),''),
                subdivision_code= none_if(subdivision_values[subdivision_code_position].get_text().replace("*", ""),''),
                subdivision_name= none_if(subdivision_values[subdivision_name_position].get_text(),''),
                local_variant= none_if(subdivision_values[local_variant_position].get_text(),''),
                language_code= none_if(subdivision_values[language_code_position].get_text(),''),
                romanization_system= none_if(subdivision_values[romanization_system_position].get_text(),''),
                parent_subdivision_code= none_if(subdivision_values[parent_subdivision_code_position].get_text(),'')
            )
        )

    return subdivisions

CHANGE_COLUMN_COUNT = 3

@measure_execution_time
def parse_country_changes(html: str, alpha_2_code: Optional[str] = None) -> List[Change]:

    soup = BeautifulSoup(html, "html.parser")
    changes: List[Change] = []

    # The changes table has no id/class of its own to select on, unlike the
    # subdivisions and additional-information tables, so identify it by
    # elimination instead of assuming it's positionally last: that assumption
    # would silently parse the wrong table if the page ever grew another
    # section after it.
    other_table_ids = {id(soup.find('table', id='subdivision'))}
    additional_information_div = soup.find('div', id='country-additional-info')
    if additional_information_div is not None:
        other_table_ids.add(id(additional_information_div.find('table')))

    candidate_tables = [table for table in soup.find_all('table') if id(table) not in other_table_ids]

    if len(candidate_tables) != 1:
        logger.warning(
            f"[{alpha_2_code}] expected exactly 1 candidate table for changes, "
            f"found {len(candidate_tables)}, using the last one"
        )

    changes_table = candidate_tables[-1]
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

    alpha_2_code = extract_page_code(html)

    summary: Dict[str, str] = parse_country_summary(html, language, alpha_2_code)
    subdivisions: List[Subdivision] = parse_country_subdivisions(html, alpha_2_code)
    changes: List[Change] = parse_country_changes(html, alpha_2_code)
    additional_information: List[AdditionalInformation] = parse_country_additional_information(html, alpha_2_code)

    logger.debug(f"[{alpha_2_code}] {summary=} {subdivisions=} {changes=} {additional_information=}")

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
        subdivisions= subdivisions,
        changes= changes,
        additional_information= additional_information
    )

    logger.info(
        f"[{alpha_2_code}] parsed country: {len(subdivisions)} subdivisions, "
        f"{len(changes)} changes, {len(additional_information)} additional information"
    )

    return country