from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CodeElementStatus:
    class_name: str | None = None
    text: str | None = None

@dataclass
class CodeElement:
    alpha_2_code: str | None = None
    short_name_lower_case: str | None = None
    status: str | None = None
    page_id: str | None = None

@dataclass
class AdditionalInformation:
    administrative_language_alpha_2_code: str | None = None
    administrative_language_alpha_3_code: str | None = None
    local_short_name: str | None = None

@dataclass
class Subdivision:
    subdivision_category: str | None = None
    subdivision_code: str | None = None
    subdivision_name: str | None = None
    local_variant: str | None = None
    language_code: str | None = None
    romanization_system: str | None = None
    parent_subdivision_code: str | None = None

@dataclass
class Change:
    effective_date: str | None = None
    short_description_en: str | None = None
    short_description_fr: str | None = None

@dataclass
class Country:
    alpha_2_code: str | None = None
    alpha_3_code: str | None = None
    alpha_4_code: str | None = None
    numeric_code: str | None = None
    short_name: str | None = None
    short_name_lower_case: str | None = None
    full_name: str | None = None
    independent: str | None = None
    territory_name: str | None = None
    status: str | None = None
    status_remark: str | None = None
    remarks: str | None = None
    remark_part_1: str | None = None
    remark_part_2: str | None = None
    remark_part_3: str | None = None
    subdivisions: list[Subdivision] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    additional_information: list[AdditionalInformation] = field(default_factory=list)

    def get_subdivisions(self) -> list[dict[str, Any]]:
        return [
            asdict(subdivision) | {
                'alpha_2_code': self.alpha_2_code,
                'alpha_3_code': self.alpha_3_code,
                'numeric_code': self.numeric_code
            }
            for subdivision in self.subdivisions
        ]

    def get_additional_information(self) -> list[dict[str, Any]]:
        return [
            asdict(additional_information) | {
                'alpha_2_code': self.alpha_2_code,
                'alpha_3_code': self.alpha_3_code,
                'numeric_code': self.numeric_code
            }
            for additional_information in self.additional_information
        ]

