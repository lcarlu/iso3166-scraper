from pathlib import Path

import pytest

from src.parser import (
    parse_country,
    parse_country_codes_collection,
    parse_code_elements_statuses,
    parse_country_subdivisions,
    parse_country_additional_information,
    parse_country_changes,
    extract_page_code,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_country_summary_fields():
    html = (FIXTURES_DIR / "country_page_ad.html").read_text()
    country = parse_country(html, "en")

    assert country.alpha_2_code == "AD"
    assert country.alpha_3_code == "AND"
    assert country.numeric_code == "020"
    assert country.short_name == "ANDORRA"
    assert country.short_name_lower_case == "Andorra"
    assert country.full_name == "the Principality of Andorra"
    assert country.independent == "Yes"
    assert country.status == "Officially assigned"


def test_parse_country_nested_collections():
    html = (FIXTURES_DIR / "country_page_ad.html").read_text()
    country = parse_country(html, "en")

    assert len(country.additional_information) == 1
    assert len(country.subdivisions) == 7
    assert len(country.changes) == 2


def test_parse_country_summary_fields_with_remark_parts():
    # country_page_fr_en.html (France) has fields AD lacks, notably
    # remark_part_1/2/3 and a populated additional-information table.
    html = (FIXTURES_DIR / "country_page_fr_en.html").read_text()
    country = parse_country(html, "en")

    assert country.alpha_2_code == "FR"
    assert country.alpha_3_code == "FRA"
    assert country.numeric_code == "250"
    assert country.short_name == "FRANCE"
    assert country.full_name == "the French Republic"
    assert country.remark_part_1.startswith("Comprises: Metropolitan France")
    assert country.remark_part_2 is not None
    assert country.remark_part_3 is not None

    assert len(country.additional_information) == 1
    assert country.additional_information[0].administrative_language_alpha_2_code == "fr"
    assert country.additional_information[0].local_short_name == "France (la)"


def test_parse_country_rejects_unsupported_language():
    html = (FIXTURES_DIR / "country_page_ad.html").read_text()

    with pytest.raises(Exception, match="Unexpected language"):
        parse_country(html, "de")


def test_parse_country_codes_collection():
    html = (FIXTURES_DIR / "country_codes_collection.html").read_text()
    statuses = parse_code_elements_statuses(html)
    collection = parse_country_codes_collection(html, statuses)

    ae = next(c for c in collection if c.alpha_2_code == "AE")
    assert ae.short_name_lower_case == "United Arab Emirates (the)"
    assert ae.status == "Officially assigned code elements"
    assert ae.page_id == "#iso:code:3166:AE"


def test_parse_country_codes_collection_does_not_leak_status_across_rows():
    # Regression test: td_class used to only be reassigned on a legend match
    # and was never reset between rows, so a row whose status class isn't in
    # the legend used to silently inherit the previous row's status instead
    # of being None.
    html = """
    <html><body>
        <table class="grs-grid-legend">
            <tr><td class="grs-status1" width="5%"></td><td>Officially assigned code elements</td></tr>
        </table>
        <table class="grs-grid"><tbody><tr>
            <td class="grs-status1" title="Andorra"><a href="#iso:code:3166:AD">AD</a></td>
            <td class="grs-status9" title="Unknown"><a href="#iso:code:3166:ZZ">ZZ</a></td>
        </tr></tbody></table>
    </body></html>
    """

    statuses = parse_code_elements_statuses(html)
    collection = parse_country_codes_collection(html, statuses)

    ad, zz = collection
    assert ad.status == "Officially assigned code elements"
    assert zz.status is None


def test_extract_page_code_matches_the_rendered_country():
    html = (FIXTURES_DIR / "country_page_ad.html").read_text()
    assert extract_page_code(html) == "AD"


def test_extract_page_code_returns_none_when_summary_missing():
    assert extract_page_code("<html><body>no summary here</body></html>") is None


WITHDRAWN_ENTRY_HTML = """
<html><body>
    <div class="core-view-summary">
        <div class="core-view-line">
            <div class="core-view-field-name">Alpha-4 code</div>
            <div class="core-view-field-value">DDDE</div>
        </div>
        <div class="core-view-line">
            <div class="core-view-field-name">Short name</div>
            <div class="core-view-field-value">GERMAN DEMOCRATIC REPUBLIC</div>
        </div>
    </div>
    <table id="subdivision"><thead></thead><tbody></tbody></table>
    <div id="country-additional-info">
        <table><thead></thead><tbody></tbody></table>
    </div>
    <table><tbody></tbody></table>
</body></html>
"""


def test_extract_page_code_returns_the_four_letter_code_for_withdrawn_entries():
    # Regression test: withdrawn ISO 3166-3 entries (e.g. "DDDE" for the
    # former East Germany) render a 4-letter code as the summary's first
    # field instead of a 2-letter alpha-2 code. get_country_html_with_retries
    # relies on this matching the code stored on the CodeElement for that
    # row, so the retry/verification logic must return it as-is rather than
    # assuming a 2-letter value.
    assert extract_page_code(WITHDRAWN_ENTRY_HTML) == "DDDE"


def test_parse_country_summary_for_withdrawn_entry_has_no_alpha_2_code():
    # The "Alpha-2 code" field is simply absent for withdrawn entries, so it
    # should stay None rather than being back-filled with the 4-letter code.
    country = parse_country(WITHDRAWN_ENTRY_HTML, "en")

    assert country.alpha_2_code is None
    assert country.alpha_4_code == "DDDE"
    assert country.short_name == "GERMAN DEMOCRATIC REPUBLIC"


def test_parse_country_changes_ignores_table_order():
    # Regression test: parse_country_changes used to grab tables[-1] ("the
    # last table on the page"), which breaks if the changes table isn't
    # positioned last. It's now identified by excluding the subdivisions and
    # additional-information tables instead, so put the changes table first
    # here to prove position no longer matters.
    html = """
    <html><body>
        <table><tbody>
            <tr><td>2020-01-01</td><td>Some change</td><td>Un changement</td></tr>
        </tbody></table>
        <table id="subdivision"><thead></thead><tbody></tbody></table>
        <div id="country-additional-info">
            <table><thead></thead><tbody></tbody></table>
        </div>
    </body></html>
    """

    changes = parse_country_changes(html, alpha_2_code="ZZ")

    assert len(changes) == 1
    assert changes[0].effective_date == "2020-01-01"
    assert changes[0].short_description_en == "Some change"
    assert changes[0].short_description_fr == "Un changement"


def test_parse_country_subdivisions_skips_malformed_rows_instead_of_crashing():
    # Regression test: a subdivision row with fewer than 7 <td> cells (e.g. a
    # merged/empty cell) used to raise an uncaught IndexError and abort the
    # whole scraping run instead of just that one row.
    html = """
    <html><body>
        <table id="subdivision">
            <thead>
                <tr>
                    <th>Subdivision category</th>
                    <th>3166-2 code</th>
                    <th>Subdivision name</th>
                    <th>Local variant</th>
                    <th>Language code</th>
                    <th>Romanization system</th>
                    <th>Parent subdivision</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Category</td><td>AA-01</td><td>Name One</td>
                    <td></td><td></td><td></td><td></td>
                </tr>
                <tr><td>Category</td><td>AA-02</td></tr>
            </tbody>
        </table>
    </body></html>
    """

    subdivisions = parse_country_subdivisions(html, alpha_2_code="ZZ")

    assert len(subdivisions) == 1
    assert subdivisions[0].subdivision_code == "AA-01"


def test_parse_country_additional_information_finds_table_nested_in_div():
    # Regression test: the "country-additional-info" id lives on the <div>
    # wrapping the table, not on the <table> itself. Looking it up as
    # soup.find('table', id=...) always returns None and crashes.
    html = """
    <html><body>
        <div id="country-additional-info">
            <h3>Additional information</h3>
            <table>
                <thead>
                    <tr>
                        <th>Administrative language(s) alpha-2</th>
                        <th>Administrative language(s) alpha-3</th>
                        <th>Local short name</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>ca</td><td>cat</td><td>Andorra</td></tr>
                </tbody>
            </table>
        </div>
    </body></html>
    """

    additional_information = parse_country_additional_information(html, alpha_2_code="ZZ")

    assert len(additional_information) == 1
    assert additional_information[0].administrative_language_alpha_2_code == "ca"
