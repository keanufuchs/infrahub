from typing import Optional, Any, List

from infrahub_sync.adapters.netbox import NetboxModel


class Rack(NetboxModel):
    _modelname = "rack"
    _identifiers = ("name",)
    _attributes = ("location", "description")
    _children = {"tag": "tags"}

    name: str
    description: Optional[str]
    location: str
    tags: List[str] = []

    local_id: Optional[str]
    local_data: Optional[Any]


class Location(NetboxModel):
    _modelname = "location"
    _identifiers = ("name",)
    _attributes = ("description", "type")

    name: str
    description: Optional[str]
    type: str

    local_id: Optional[str]
    local_data: Optional[Any]


class Role(NetboxModel):
    _modelname = "role"
    _identifiers = ("name",)
    _attributes = ("description",)

    name: str
    description: Optional[str]

    local_id: Optional[str]
    local_data: Optional[Any]


class Tag(NetboxModel):
    _modelname = "tag"
    _identifiers = ("name",)
    _attributes = ("description",)

    name: str
    description: Optional[str]

    local_id: Optional[str]
    local_data: Optional[Any]
