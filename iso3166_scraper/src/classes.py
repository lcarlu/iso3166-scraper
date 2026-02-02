from dataclasses import dataclass
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha_2_code": self.alpha_2_code,
            "short_name_lower_case": self.short_name_lower_case,
            "status": self.status,
            "page_id": self.page_id
        }

@dataclass
class Language:
    administrative_language_alpha_2_code: str
    administrative_language_alpha_3_code: str
    local_short_name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "administrative_language_alpha_2_code": self.administrative_language_alpha_2_code,
            "administrative_language_alpha_3_code": self.administrative_language_alpha_3_code,
            "local_short_name": self.local_short_name
        }

@dataclass
class Subdivision:
    subdivision_category: str
    subdivision_code: str
    subdivision_name: str
    local_variant: str
    language_code: str
    romanization_system: str
    parent_subdivision_code: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subdivision_category": self.subdivision_category,
            "subdivision_code": self.subdivision_code,
            "subdivision_name": self.subdivision_name,
            "local_variant": self.local_variant,
            "language_code": self.language_code,
            "romanization_system": self.romanization_system,
            "parent_subdivision_code": self.parent_subdivision_code
        }

@dataclass
class Change:
    effective_date: str
    short_description_en: str
    short_description_fr: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effective_date": self.effective_date,
            "short_description_en": self.short_description_en,
            "short_description_fr": self.short_description_fr
        }

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

    def get_subdivisions(self) -> List[Dict[str, str]]:
        
        subdivisions_list: List[Dict[str, str]] = []

        for subdivision in self.subdivisions:
            subdivision_dict = subdivision.to_dict()
            subdivision_dict['alpha_2_code'] = self.alpha_2_code
            subdivision_dict['alpha_3_code'] = self.alpha_3_code
            subdivision_dict['numeric_code'] = self.numeric_code

            subdivisions_list.append(subdivision_dict)

        return subdivisions_list
    
    def get_languages(self) -> List[Dict[str, str]]:
        
        languages_list: List[Dict[str, str]] = []

        for language in self.languages:
            language_dict = language.to_dict()
            language_dict['alpha_2_code'] = self.alpha_2_code
            language_dict['alpha_3_code'] = self.alpha_3_code
            language_dict['numeric_code'] = self.numeric_code

            languages_list.append(language_dict)

        return languages_list

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha_2_code": self.alpha_2_code,
            "alpha_3_code": self.alpha_3_code,
            "alpha_4_code": self.alpha_4_code,
            "numeric_code": self.numeric_code,
            "short_name": self.short_name,
            "short_name_lower_case": self.short_name_lower_case,
            "full_name": self.full_name,
            "independent": self.independent,
            "territory_name": self.territory_name,
            "status": self.status,
            "status_remark": self.status_remark,
            "remarks": self.remarks,
            "remark_part_1": self.remark_part_1,
            "remark_part_2": self.remark_part_2,
            "remark_part_3": self.remark_part_3,
            "languages": [x.to_dict() for x in self.languages],
            "subdivisions": [x.to_dict() for x in self.subdivisions],
            "changes": [x.to_dict() for x in self.changes]
        }



