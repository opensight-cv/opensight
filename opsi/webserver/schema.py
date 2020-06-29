from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator

from opsi.util.enum import Enum

# N = NodeTree = often save
# F = Function = initial load


class LinkN(BaseModel):
    id: str
    name: str


class InputN(BaseModel):
    link: Optional[LinkN] = None
    value: Optional[Any] = None


class NodeN(BaseModel):
    type: str
    id: str
    settings: Dict[str, Any] = {}
    inputs: Dict[str, InputN] = {}
    extras: Any = {}


class NodeTreeN(BaseModel):
    nodes: List[NodeN] = []
    extras: Any = {}


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
    modules: List[ModuleF] = []


# --------------------------------


class Network(BaseModel):
    @Enum("Network.Mode")
    class Mode:
        mDNS: ...
        Static: ...
        Localhost: ...

    team: str = 9999
    mode: Mode = Mode.mDNS
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
        assert len(team_str) == 4

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


class FrontendSettings(BaseModel):
    class Status(BaseModel):
        network_mode: List[str]
        daemon: bool
        nt: bool
        netconf: bool
        version: str

    preferences: Preferences
    status: Status
