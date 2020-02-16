from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, validator

# N = NodeTree = often save
# F = Function = initial load


# Constant flags, to be False eventually
FUNC_INSTEAD_OF_MODS = True
LINKS_INSTEAD_OF_INPUTS = True


class LinkN(BaseModel):
    id: UUID
    name: str


class InputN(BaseModel):
    link: Optional[LinkN] = None
    value: Optional[Any] = None


class NodeN(BaseModel):
    type: str
    id: UUID
    settings: Dict[str, Any] = {}
    if LINKS_INSTEAD_OF_INPUTS:
        inputs: Dict[str, Optional[LinkN]] = {}
    else:
        inputs: Dict[str, InputN] = {}
    pos: list = []


class NodeTreeN(BaseModel):
    nodes: List[NodeN] = []


# --------------------------------


class InputOutputF(BaseModel):
    type: str
    params: Dict[str, Any] = {}


class FunctionF(BaseModel):
    name: str
    type: str
    settings: Dict[str, InputOutputF] = {}
    inputs: Dict[str, InputOutputF] = {}
    outputs: Dict[str, InputOutputF] = {}


class ModuleF(BaseModel):
    package: str
    version: str
    funcs: List[FunctionF] = []


class SchemaF(BaseModel):
    if FUNC_INSTEAD_OF_MODS:
        funcs: List[FunctionF] = []
    else:
        modules: List[ModuleF] = []


# --------------------------------


class Network(BaseModel):
    team: str = 9999
    mDNS: bool = True
    dhcp: bool = True
    static_ext: str = 100
    nt_enabled: bool = True
    nt_client: bool = True

    @validator("team", always=True)
    def team_formatter(cls, team):
        team = int(team)

        if not 1 <= team <= 9999:
            raise ValueError("Team number must be between 1 and 9999")

        return team

    @property
    def team_str(self):
        team_str = f"{self.team:04d}"
        assert 1 <= len(team_str) <= 4

        return team_str

    @validator("static_ext", always=True)
    def static_ext_str_formatter(cls, static_ext):
        static_ext = int(static_ext)

        if not 2 <= static_ext <= 255:
            raise ValueError("Static extension number must be between 1 and 255")

        return static_ext


class Preferences(BaseModel):
    profile: int = 0
    network: Network = Network()
