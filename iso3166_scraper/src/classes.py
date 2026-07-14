from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class CodeElementStatus:
    class_name: str
    text: str

@dataclass
class CodeElement:
    alpha_2_code: str
    short_name_lower_case: str
    status: str
    page_id: str

@dataclass
class Language:
    administrative_language_alpha_2_code: str
    administrative_language_alpha_3_code: str
    local_short_name: str

@dataclass
class Subdivision:
    subdivision_category: str
    subdivision_code: str
    subdivision_name: str
    local_variant: str
    language_code: str
    romanization_system: str
    parent_subdivision_code: str

@dataclass
class Change:
    effective_date: str
    short_description_en: str
    short_description_fr: str

@dataclass
class Country:
    alpha_2_code: str
    alpha_3_code: str
    alpha_4_code: str
    numeric_code: str
    short_name: str
    short_name_lower_case: str
    full_name: str
    independent: str
    territory_name: str
    status: str
    status_remark: str
    remarks: str
    remark_part_1: str
    remark_part_2: str
    remark_part_3: str
    languages: List[Language] = None
    subdivisions: List[Subdivision] = None
    changes: List[Change] = None

    def get_subdivisions(self) -> List[Dict[str, Any]]:
        return [
            asdict(subdivision) | {
                'alpha_2_code': self.alpha_2_code,
                'alpha_3_code': self.alpha_3_code,
                'numeric_code': self.numeric_code
            }
            for subdivision in self.subdivisions
        ]

    def get_languages(self) -> List[Dict[str, Any]]:
        return [
            asdict(language) | {
                'alpha_2_code': self.alpha_2_code,
                'alpha_3_code': self.alpha_3_code,
                'numeric_code': self.numeric_code
            }
            for language in self.languages
        ]

