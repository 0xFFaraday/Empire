from typing import Dict, List, Optional

from pydantic import BaseModel

from empire.server.api.v2.shared_dto import Author, CustomOptionSchema, to_value_type
from empire.server.core.module_models import EmpireModule, LanguageEnum


def domain_to_dto_module(module: EmpireModule, uid: str):
    options = {x.name: x for x in module.options}
    options = dict(
        map(
            lambda x: (
                x[0],
                {
                    "description": x[1].description,
                    "required": x[1].required,
                    "value": x[1].value,
                    "strict": x[1].strict,
                    "suggested_values": x[1].suggested_values,
                    # todo expand to listener, stager, etc
                    "value_type": to_value_type(x[1].value, x[1].type),
                },
            ),
            options.items(),
        )
    )

    return Module(
        id=uid,
        name=module.name,
        enabled=module.enabled,
        authors=module.authors,
        description=module.description,
        background=module.background,
        language=module.language,
        min_language_version=module.min_language_version,
        needs_admin=module.needs_admin,
        opsec_safe=module.opsec_safe,
        techniques=module.techniques,
        software=module.software,
        tactics=module.tactics,
        comments=module.comments,
        options=options,
    )


class Module(BaseModel):
    id: str
    name: str
    enabled: bool
    authors: List[Author]
    description: str
    background: bool
    language: LanguageEnum
    min_language_version: Optional[str]
    needs_admin: bool
    opsec_safe: bool
    techniques: List[str]
    tactics: List[str]
    software: Optional[str]
    comments: List[str]
    options: Dict[str, CustomOptionSchema]


class Modules(BaseModel):
    records: List[Module]


class ModuleScript(BaseModel):
    module_id: str
    script: str


class ModuleUpdateRequest(BaseModel):
    enabled: bool


class ModuleBulkUpdateRequest(BaseModel):
    modules: List[str]
    enabled: bool
