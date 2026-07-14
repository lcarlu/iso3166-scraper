from src.utils import none_if, to_snake_case


def test_none_if_returns_none_when_equal():
    assert none_if("", "") is None


def test_none_if_returns_first_expression_when_different():
    assert none_if("Andorra", "") == "Andorra"


def test_to_snake_case_converts_field_labels():
    assert to_snake_case("Alpha-2 code") == "alpha_2_code"
    assert to_snake_case("Short name lower case") == "short_name_lower_case"
    assert to_snake_case("Full name") == "full_name"
