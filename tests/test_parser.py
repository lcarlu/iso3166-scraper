from pathlib import Path

import pytest

from src.parser import (
    parse_country,
    parse_country_codes_collection,
    parse_code_elements_statuses,
    parse_country_subdivisions,
    extract_alpha_2_code,
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

    assert len(country.languages) == 1
    assert len(country.subdivisions) == 7
    assert len(country.changes) == 2


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


def test_extract_alpha_2_code_matches_the_rendered_country():
    html = (FIXTURES_DIR / "country_page_ad.html").read_text()
    assert extract_alpha_2_code(html) == "AD"


def test_extract_alpha_2_code_returns_none_when_summary_missing():
    assert extract_alpha_2_code("<html><body>no summary here</body></html>") is None


def test_parse_country_subdivisions_skips_malformed_rows_instead_of_crashing():
    # Regression test: a subdivision row with fewer than 7 <td> cells (e.g. a
    # merged/empty cell) used to raise an uncaught IndexError and abort the
    # whole scraping run instead of just that one row.
    html = """
    <html><body>
        <table><tbody><tr><td>languages table placeholder</td></tr></tbody></table>
        <table><tbody>
            <tr>
                <td>Category</td><td>AA-01</td><td>Name One</td>
                <td></td><td></td><td></td><td></td>
            </tr>
            <tr><td>Category</td><td>AA-02</td></tr>
        </tbody></table>
        <table><tbody><tr><td>changes table placeholder</td></tr></tbody></table>
    </body></html>
    """

    subdivisions = parse_country_subdivisions(html, alpha_2_code="ZZ")

    assert len(subdivisions) == 1
    assert subdivisions[0].subdivision_code == "AA-01"
