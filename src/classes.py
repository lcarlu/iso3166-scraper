from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class CodeElementStatus:
    class_name: Optional[str] = None
    text: Optional[str] = None

@dataclass
class CodeElement:
    alpha_2_code: Optional[str] = None
    short_name_lower_case: Optional[str] = None
    status: Optional[str] = None
    page_id: Optional[str] = None

@dataclass
class Language:
    administrative_language_alpha_2_code: Optional[str] = None
    administrative_language_alpha_3_code: Optional[str] = None
    local_short_name: Optional[str] = None

@dataclass
class Subdivision:
    subdivision_category: Optional[str] = None
    subdivision_code: Optional[str] = None
    subdivision_name: Optional[str] = None
    local_variant: Optional[str] = None
    language_code: Optional[str] = None
    romanization_system: Optional[str] = None
    parent_subdivision_code: Optional[str] = None

@dataclass
class Change:
    effective_date: Optional[str] = None
    short_description_en: Optional[str] = None
    short_description_fr: Optional[str] = None

@dataclass
class Country:
    alpha_2_code: Optional[str] = None
    alpha_3_code: Optional[str] = None
    alpha_4_code: Optional[str] = None
    numeric_code: Optional[str] = None
    short_name: Optional[str] = None
    short_name_lower_case: Optional[str] = None
    full_name: Optional[str] = None
    independent: Optional[str] = None
    territory_name: Optional[str] = None
    status: Optional[str] = None
    status_remark: Optional[str] = None
    remarks: Optional[str] = None
    remark_part_1: Optional[str] = None
    remark_part_2: Optional[str] = None
    remark_part_3: Optional[str] = None
    languages: Optional[List[Language]] = None
    subdivisions: Optional[List[Subdivision]] = None
    changes: Optional[List[Change]] = None

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



