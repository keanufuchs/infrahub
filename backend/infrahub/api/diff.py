import copy
import enum
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Request
from fastapi.logger import logger
from neo4j import AsyncSession
from pydantic import BaseModel, Extra, Field

from infrahub.api.dependencies import get_branch_dep, get_current_user, get_session
from infrahub.core import get_branch, registry
from infrahub.core.branch import Branch, Diff, ObjectConflict, RelationshipDiffElement
from infrahub.core.constants import DiffAction
from infrahub.core.manager import NodeManager
from infrahub.core.schema import RelationshipCardinality
from infrahub.core.schema_manager import INTERNAL_SCHEMA_NODE_KINDS

if TYPE_CHECKING:
    from infrahub.message_bus.rpc import InfrahubRpcClient

# pylint    : disable=too-many-branches

router = APIRouter(prefix="/diff")


class DiffElementType(str, enum.Enum):
    ATTRIBUTE = "Attribute"
    RELATIONSHIP_ONE = "RelationshipOne"
    RELATIONSHIP_MANY = "RelationshipMany"


class DiffSummary(BaseModel):
    added: int = 0
    removed: int = 0
    updated: int = 0

    def inc(self, name: str) -> int:
        """Increase one of the counter by 1.

        Return the new value of the counter.
        """
        try:
            cnt = getattr(self, name)
        except AttributeError as exc:
            raise ValueError(f"{name} is not a valid counter in DiffSummary.") from exc

        new_value = cnt + 1
        setattr(self, name, new_value)

        return new_value


class BranchDiffPropertyValue(BaseModel):
    new: Any
    previous: Any


class BranchDiffProperty(BaseModel):
    branch: str
    type: str
    changed_at: Optional[str]
    action: DiffAction
    value: BranchDiffPropertyValue


# class BranchDiffPropertyAttribute(BranchDiffProperty):
#     path: str


class BranchDiffPropertyCollection(BaseModel):
    path: str
    changes: List[BranchDiffProperty] = Field(default_factory=list)


class BranchDiffAttribute(BaseModel):
    type: DiffElementType = DiffElementType.ATTRIBUTE
    name: str
    id: str
    changed_at: Optional[str]
    summary: DiffSummary = DiffSummary()
    action: DiffAction
    value: Optional[BranchDiffProperty]
    properties: List[BranchDiffProperty] = Field(default_factory=list)


class BranchDiffRelationshipPeerNode(BaseModel):
    id: str
    kind: str
    display_label: Optional[str]


# OLD
class BranchDiffRelationshipOnePeerValue(BaseModel):
    new: Optional[BranchDiffRelationshipPeerNode] = None
    previous: Optional[BranchDiffRelationshipPeerNode] = None


# OLD
class BranchDiffRelationshipOne(BaseModel):
    type: DiffElementType = DiffElementType.RELATIONSHIP_ONE
    branch: str
    id: str
    identifier: str
    summary: DiffSummary = DiffSummary()
    name: str
    peer: BranchDiffRelationshipOnePeerValue
    properties: List[BranchDiffProperty] = Field(default_factory=list)
    changed_at: Optional[str]
    action: DiffAction


# OLD
class BranchDiffRelationshipManyElement(BaseModel):
    branch: str
    id: str
    identifier: str
    summary: DiffSummary = DiffSummary()
    peer: BranchDiffRelationshipPeerNode
    properties: List[BranchDiffProperty] = Field(default_factory=list)
    changed_at: Optional[str]
    action: DiffAction


# OLD
class BranchDiffRelationshipMany(BaseModel):
    type: DiffElementType = DiffElementType.RELATIONSHIP_MANY
    branch: str
    identifier: str
    summary: DiffSummary = DiffSummary()
    name: str
    peers: List[BranchDiffRelationshipManyElement] = Field(default_factory=list)

    @property
    def action(self) -> DiffAction:
        if self.summary.added and not self.summary.updated and not self.summary.removed:
            return DiffAction.ADDED
        if not self.summary.added and not self.summary.updated and self.summary.removed:
            return DiffAction.REMOVED
        return DiffAction.UPDATED


# NEW
class BranchDiffAction(BaseModel):
    branch: str
    action: DiffAction = DiffAction.UNCHANGED


# NEW
class BranchDiffElementAttribute(BaseModel):
    type: DiffElementType = DiffElementType.ATTRIBUTE
    branches: List[str] = Field(default_factory=list)
    id: str = ""
    summary: DiffSummary = DiffSummary()
    action: DiffAction = DiffAction.UNCHANGED
    value: Optional[BranchDiffPropertyCollection]
    properties: Dict[str, BranchDiffPropertyCollection] = Field(default_factory=dict)

    class Config:
        extra = Extra.forbid


# NEW
class BranchDiffRelationshipOnePeer(BaseModel):
    branch: str
    new: Optional[BranchDiffRelationshipPeerNode] = None
    previous: Optional[BranchDiffRelationshipPeerNode] = None


class BranchDiffRelationshipOnePeerCollection(BaseModel):
    path: str
    changes: List[BranchDiffRelationshipOnePeer] = Field(default_factory=list)


# NEW
class BranchDiffElementRelationshipOne(BaseModel):
    type: DiffElementType = DiffElementType.RELATIONSHIP_ONE
    id: str = ""
    identifier: str = ""
    branches: List[str] = Field(default_factory=list)
    summary: DiffSummary = DiffSummary()
    peer: Optional[BranchDiffRelationshipOnePeerCollection]
    properties: Dict[str, BranchDiffPropertyCollection] = Field(default_factory=dict)
    changed_at: Optional[str] = None
    action: List[BranchDiffAction] = Field(default_factory=list)

    class Config:
        extra = Extra.forbid


# NEW
class BranchDiffElementRelationshipMany(BaseModel):
    type: DiffElementType = DiffElementType.RELATIONSHIP_MANY
    identifier: str = ""
    branches: List[str] = Field(default_factory=list)
    summary: DiffSummary = DiffSummary()
    peers: List[BranchDiffRelationshipManyElement] = Field(default_factory=list)  # OLD

    class Config:
        extra = Extra.forbid

    @property
    def action(self) -> DiffAction:
        if self.summary.added and not self.summary.updated and not self.summary.removed:
            return DiffAction.ADDED
        if not self.summary.added and not self.summary.updated and self.summary.removed:
            return DiffAction.REMOVED
        return DiffAction.UPDATED


# NEW
class BranchDiffElement(BaseModel, smart_union=True):
    type: DiffElementType
    name: str
    path: str
    change: Union[BranchDiffElementAttribute, BranchDiffElementRelationshipOne, BranchDiffElementRelationshipMany]


# OLD
class BranchDiffNode(BaseModel):
    branch: str
    kind: str
    id: str
    summary: DiffSummary = DiffSummary()
    display_label: str
    changed_at: Optional[str] = None
    action: DiffAction
    elements: Dict[str, Union[BranchDiffRelationshipOne, BranchDiffRelationshipMany, BranchDiffAttribute]] = Field(
        default_factory=dict
    )


# NEW
class BranchDiffDisplayLabel(BaseModel):
    branch: str
    display_label: str


# NEW
class BranchDiffEntry(BaseModel):
    kind: str
    id: str
    path: str
    elements: Dict[str, BranchDiffElement] = Field(default_factory=dict)
    summary: DiffSummary = DiffSummary()
    action: List[BranchDiffAction] = Field(default_factory=list)
    display_label: List[BranchDiffDisplayLabel] = Field(default_factory=list)


#  NEW
class BranchDiff(BaseModel):
    diffs: List[BranchDiffEntry] = Field(default_factory=list)
    # conflicts: Dict[str, ObjectConflict] = Field(default_factory=dict)


class BranchDiffFile(BaseModel):
    branch: str
    location: str
    action: DiffAction


class BranchDiffRepository(BaseModel):
    branch: str
    id: str
    display_name: Optional[str] = None
    commit_from: str
    commit_to: str
    files: List[BranchDiffFile] = Field(default_factory=list)


class BranchDiffArtifactStorage(BaseModel):
    storage_id: str
    checksum: str


class BranchDiffArtifact(BaseModel):
    branch: str
    id: str
    display_label: Optional[str] = None
    action: DiffAction
    item_new: Optional[BranchDiffArtifactStorage] = None
    item_previous: Optional[BranchDiffArtifactStorage] = None


async def get_display_labels_per_kind(kind: str, ids: List[str], branch_name: str, session: AsyncSession):
    """Return the display_labels of a list of nodes of a specific kind."""
    branch = await get_branch(branch=branch_name, session=session)
    schema = registry.get_schema(name=kind, branch=branch)
    fields = schema.generate_fields_for_display_label()
    nodes = await NodeManager.get_many(ids=ids, fields=fields, session=session, branch=branch)
    return {node_id: await node.render_display_label(session=session) for node_id, node in nodes.items()}


async def get_display_labels(
    nodes: Dict[str, Dict[str, List[str]]], session: AsyncSession
) -> Dict[str, Dict[str, str]]:
    """Query the display_labels of a group of nodes organized per branch and per kind."""
    response: Dict[str, Dict[str, str]] = {}
    for branch_name, items in nodes.items():
        if branch_name not in response:
            response[branch_name] = {}
        for kind, ids in items.items():
            labels = await get_display_labels_per_kind(kind=kind, ids=ids, session=session, branch_name=branch_name)
            response[branch_name].update(labels)

    return response


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
def extract_diff_relationship_one(
    node_id: str, name: str, identifier: str, rels: List[RelationshipDiffElement], display_labels: Dict[str, str]
) -> Optional[BranchDiffRelationshipOne]:
    """Extract a BranchDiffRelationshipOne object from a list of RelationshipDiffElement."""

    changed_at = None

    if len(rels) == 1:
        rel = rels[0]

        if rel.changed_at:
            changed_at = rel.changed_at.to_string()

        peer_list = [rel_node for rel_node in rel.nodes.values() if rel_node.id != node_id]
        if not peer_list:
            logger.warning(
                f"extract_diff_relationship_one: unable to find the peer associated with the node {node_id}, Name: {name}"
            )
            return None

        peer = dict(peer_list[0])
        peer["display_label"] = display_labels.get(peer.get("id", None), "")

        if rel.action.value == "added":
            peer_value = {"new": peer}
        else:
            peer_value = {"previous": peer}

        return BranchDiffRelationshipOne(
            branch=rel.branch,
            id=rel.id,
            name=name,
            identifier=identifier,
            peer=peer_value,
            properties=[prop.to_graphql() for prop in rel.properties.values()],
            changed_at=changed_at,
            action=rel.action,
        )

    if len(rels) == 2:
        rel_added = [rel for rel in rels if rel.action.value == "added"][0]
        rel_removed = [rel for rel in rels if rel.action.value == "removed"][0]

        peer_added = dict([rel_node for rel_node in rel_added.nodes.values() if rel_node.id != node_id][0])
        peer_added["display_label"] = display_labels.get(peer_added.get("id", None), "")

        peer_removed = dict([rel_node for rel_node in rel_removed.nodes.values() if rel_node.id != node_id][0])
        peer_removed["display_label"] = display_labels.get(peer_removed.get("id", None), "")
        peer_value = {"new": dict(peer_added), "previous": dict(peer_removed)}

        return BranchDiffRelationshipOne(
            branch=rel_added.branch,
            id=rel_added.id,
            name=name,
            identifier=identifier,
            peer=peer_value,
            properties=[prop.to_graphql() for prop in rel_added.properties.values()],
            changed_at=changed_at,
            action="updated",
        )

    if len(rels) > 2:
        logger.warning(
            f"extract_diff_relationship_one: More than 2 relationships received, need to investigate. Node ID {node_id}, Name: {name}"
        )

    return None


def extract_diff_relationship_many(
    node_id: str, name: str, identifier: str, rels: List[RelationshipDiffElement], display_labels: Dict[str, str]
) -> Optional[BranchDiffRelationshipMany]:
    """Extract a BranchDiffRelationshipMany object from a list of RelationshipDiffElement."""

    if not rels:
        return None

    rel_diff = BranchDiffRelationshipMany(
        branch=rels[0].branch,
        name=name,
        identifier=identifier,
    )

    for rel in rels:
        changed_at = None
        if rel.changed_at:
            changed_at = rel.changed_at.to_string()

        peer = [rel_node for rel_node in rel.nodes.values() if rel_node.id != node_id][0].dict(
            exclude={"db_id", "labels"}
        )
        peer["display_label"] = display_labels.get(peer["id"], "")

        rel_diff.summary.inc(rel.action.value)

        rel_diff.peers.append(
            BranchDiffRelationshipManyElement(
                branch=rel.branch,
                id=rel.id,
                identifier=identifier,
                peer=peer,
                properties=[prop.to_graphql() for prop in rel.properties.values()],
                changed_at=changed_at,
                action=rel.action,
            )
        )

    return rel_diff


class DiffPayload:
    def __init__(self, session: AsyncSession, diff: Diff, kinds_to_include: List[str]):
        self.session = session
        self.diff = diff
        self.kinds_to_include = kinds_to_include
        self.conflicts: List[ObjectConflict] = []
        self.diffs: List[BranchDiffNode] = []
        self.entries: Dict[str, BranchDiffEntry] = {}
        self.rels_per_node: Dict[str, Dict[str, Dict[str, List[RelationshipDiffElement]]]] = {}
        self.display_labels: Dict[str, Dict[str, str]] = {}
        self.rels: Dict[str, Dict[str, Dict[str, RelationshipDiffElement]]] = {}

    @property
    def impacted_nodes(self) -> List[str]:
        return list(self.entries.keys())

    def _add_node_summary(self, node_id: str, action: DiffAction) -> None:
        self.entries[node_id].summary.inc(action.value)

    def _set_display_label(self, node_id: str, branch: str, display_label: str) -> None:
        if not display_label:
            return

        # Check if there is already a display label for this branch
        # NOTE Currently we ignore the update and we keep the existing value but we could also update
        existing_branches = {item.branch: idx for idx, item in enumerate(self.entries[node_id].display_label)}
        if branch in existing_branches.keys():
            return
        self.entries[node_id].display_label.append(BranchDiffDisplayLabel(branch=branch, display_label=display_label))

    def _set_node_action(self, node_id: str, branch: str, action: DiffAction) -> None:
        self.entries[node_id].action.append(BranchDiffAction(branch=branch, action=action))

    async def _prepare(self) -> None:
        self.rels_per_node = await self.diff.get_relationships_per_node(session=self.session)
        node_ids = await self.diff.get_node_id_per_kind(session=self.session)

        self.display_labels = await get_display_labels(nodes=node_ids, session=self.session)
        self.conflicts = await self.diff.get_conflicts(session=self.session)

    def _add_node_to_diff(self, node_id: str, kind: str):
        if node_id not in self.entries:
            self.entries[node_id] = BranchDiffEntry(id=node_id, kind=kind, path=f"data/{node_id}")

    def _add_node_element_attribute(
        self,
        node_id: str,
        branch: str,
        element: BranchDiffAttribute,
    ) -> None:
        if element.name not in self.entries[node_id].elements:
            self.entries[node_id].elements[element.name] = BranchDiffElement(
                type=element.type,
                name=element.name,
                path=f"data/{node_id}/{element.name}",
                change=BranchDiffElementAttribute(id=element.id, action=element.action),
            )

        diff_element = self.entries[node_id].elements[element.name]

        diff_element.change.branches.append(branch)
        if element.value:
            if not diff_element.change.value:
                diff_element.change.value = BranchDiffPropertyCollection(path=f"data/{node_id}/{element.name}/value")
            diff_element.change.value.changes.append(
                BranchDiffProperty(
                    branch=branch,
                    type=element.value.type,
                    changed_at=element.value.changed_at,
                    action=element.value.action,
                    value=element.value.value,
                )
            )
            diff_element.change.summary.inc(element.value.action.value)

        for prop in element.properties:
            if prop.type not in diff_element.change.properties:
                diff_element.change.properties[prop.type] = BranchDiffPropertyCollection(
                    path=f"data/{node_id}/{element.name}/property/{prop.type}"
                )
            diff_element.change.properties[prop.type].changes.append(prop)
            diff_element.change.summary.inc(prop.action.value)

    def _add_node_element_relationship(
        self,
        node_id: str,
        element_name: str,
        branch: str,
        relationship: Union[BranchDiffRelationshipOne, BranchDiffRelationshipMany],
    ) -> None:
        if isinstance(relationship, BranchDiffRelationshipOne):
            self._add_node_element_relationship_one(
                node_id=node_id, element_name=element_name, branch=branch, relationship=relationship
            )
            return

        self._add_node_element_relationship_many(
            node_id=node_id, element_name=element_name, branch=branch, relationship=relationship
        )

    def _add_node_element_relationship_one(
        self,
        node_id: str,
        element_name: str,
        branch: str,
        relationship: BranchDiffRelationshipOne,
    ) -> None:
        if element_name not in self.entries[node_id].elements:
            self.entries[node_id].elements[element_name] = BranchDiffElement(
                type=DiffElementType.RELATIONSHIP_ONE,
                name=element_name,
                path=f"data/{node_id}/{element_name}",
                change=BranchDiffElementRelationshipOne(id=relationship.id, identifier=relationship.identifier),
            )

        diff_element = self.entries[node_id].elements[element_name]

        if branch not in diff_element.change.branches:
            diff_element.change.branches.append(branch)

        diff_element.change.action.append(BranchDiffAction(branch=branch, action=relationship.action))

        if relationship.peer.new or relationship.peer.previous:
            if not diff_element.change.peer:
                diff_element.change.peer = BranchDiffRelationshipOnePeerCollection(
                    path=f"data/{node_id}/{element_name}/peer"
                )

            diff_element.change.peer.changes.append(
                BranchDiffRelationshipOnePeer(
                    branch=branch, new=relationship.peer.new, previous=relationship.peer.previous
                )
            )

        for prop in relationship.properties:
            if prop.type not in diff_element.change.properties:
                diff_element.change.properties[prop.type] = BranchDiffPropertyCollection(
                    path=f"data/{node_id}/{element_name}/property/{prop.type}"
                )
            diff_element.change.properties[prop.type].changes.append(prop)
            diff_element.change.summary.inc(prop.action.value)

        # Fix: Add summary to element

    def _add_node_element_relationship_many(
        self,
        node_id: str,
        element_name: str,
        branch: str,
        relationship: BranchDiffRelationshipMany,
    ) -> None:
        if element_name not in self.entries[node_id].elements:
            self.entries[node_id].elements[element_name] = BranchDiffElement(
                type=DiffElementType.RELATIONSHIP_MANY,
                name=element_name,
                path=f"data/{node_id}/{element_name}",
                change=BranchDiffElementRelationshipMany(),
            )

        diff_element = self.entries[node_id].elements[element_name]

        if branch not in diff_element.change.branches:
            diff_element.change.branches.append(branch)

        diff_element.change.peers.extend(relationship.peers)

    async def _process_nodes(self) -> None:  # pylint: disable=too-many-branches
        # Generate the Diff per node and associated the appropriate relationships if they are present in the schema

        nodes = await self.diff.get_nodes(session=self.session)

        for branch_name, items in nodes.items():  # pylint: disable=too-many-nested-blocks
            branch_display_labels = self.display_labels.get(branch_name, {})
            for item in items.values():
                if self.kinds_to_include and item.kind not in self.kinds_to_include:
                    continue

                item_graphql = item.to_graphql()

                # We need to convert the list of attributes to a dict under elements
                item_dict = copy.deepcopy(item_graphql)
                del item_dict["attributes"]
                item_elements = {attr["name"]: attr for attr in item_graphql["attributes"]}

                display_label = branch_display_labels.get(item.id, "")
                node_diff = BranchDiffNode(**item_dict, elements=item_elements, display_label=display_label)
                self._add_node_to_diff(node_id=item_dict["id"], kind=item_dict["kind"])
                self._set_display_label(node_id=item_dict["id"], branch=branch_name, display_label=display_label)
                self._set_node_action(node_id=item_dict["id"], branch=branch_name, action=item_dict["action"])
                schema = registry.get_schema(name=node_diff.kind, branch=node_diff.branch)

                # Extract the value from the list of properties
                for _, element in node_diff.elements.items():
                    node_diff.summary.inc(element.action.value)
                    self._add_node_summary(node_id=item_dict["id"], action=element.action)

                    for prop in element.properties:
                        if prop.type == "HAS_VALUE":
                            element.value = prop
                        else:
                            element.summary.inc(prop.action.value)

                    if element.value:
                        element.properties.remove(element.value)
                    self._add_node_element_attribute(node_id=item_dict["id"], branch=branch_name, element=element)

                if item.id in self.rels_per_node[branch_name]:
                    for rel_name, rels in self.rels_per_node[branch_name][item.id].items():
                        if rel_schema := schema.get_relationship_by_identifier(id=rel_name, raise_on_error=False):
                            diff_rel = None
                            if rel_schema.cardinality == RelationshipCardinality.ONE:
                                diff_rel = extract_diff_relationship_one(
                                    node_id=item.id,
                                    name=rel_schema.name,
                                    identifier=rel_name,
                                    rels=rels,
                                    display_labels=branch_display_labels,
                                )
                            elif rel_schema.cardinality == RelationshipCardinality.MANY:
                                diff_rel = extract_diff_relationship_many(
                                    node_id=item.id,
                                    name=rel_schema.name,
                                    identifier=rel_name,
                                    rels=rels,
                                    display_labels=branch_display_labels,
                                )

                            if diff_rel:
                                node_diff.elements[diff_rel.name] = diff_rel
                                node_diff.summary.inc(diff_rel.action.value)
                                self._add_node_summary(node_id=item_dict["id"], action=diff_rel.action)
                                self._add_node_element_relationship(
                                    node_id=node_diff.id,
                                    element_name=diff_rel.name,
                                    branch=branch_name,
                                    relationship=diff_rel,
                                )

                self.diffs.append(node_diff)

    async def _process_relationships(self) -> None:
        # Check if all nodes associated with a relationship have been accounted for
        # If a node is missing it means its changes are only related to its relationships
        for branch_name, _ in self.rels_per_node.items():
            branch_display_labels = self.display_labels.get(branch_name, {})
            for node_in_rel, _ in self.rels_per_node[branch_name].items():
                if node_in_rel in self.impacted_nodes:
                    continue

                node_diff = None
                for rel_name, rels in self.rels_per_node[branch_name][node_in_rel].items():
                    node_kind = rels[0].nodes[node_in_rel].kind

                    if self.kinds_to_include and node_kind not in self.kinds_to_include:
                        continue

                    schema = registry.get_schema(name=node_kind, branch=branch_name)
                    rel_schema = schema.get_relationship_by_identifier(id=rel_name, raise_on_error=False)
                    if not rel_schema:
                        continue

                    if not node_diff:
                        node_diff = BranchDiffNode(
                            branch=branch_name,
                            id=node_in_rel,
                            kind=node_kind,
                            action=DiffAction.UPDATED,
                            display_label=branch_display_labels.get(node_in_rel, ""),
                        )
                    self._add_node_to_diff(node_id=node_in_rel, kind=node_kind)
                    self._set_display_label(
                        node_id=node_in_rel,
                        branch=branch_name,
                        display_label=branch_display_labels.get(node_in_rel, ""),
                    )
                    self._set_node_action(node_id=node_in_rel, branch=branch_name, action=DiffAction.UPDATED)

                    if rel_schema.cardinality == RelationshipCardinality.ONE:
                        diff_rel = extract_diff_relationship_one(
                            node_id=node_in_rel,
                            name=rel_schema.name,
                            identifier=rel_name,
                            rels=rels,
                            display_labels=branch_display_labels,
                        )

                    elif rel_schema.cardinality == RelationshipCardinality.MANY:
                        diff_rel = extract_diff_relationship_many(
                            node_id=node_in_rel,
                            name=rel_schema.name,
                            identifier=rel_name,
                            rels=rels,
                            display_labels=branch_display_labels,
                        )

                    if diff_rel:
                        node_diff.elements[diff_rel.name] = diff_rel
                        node_diff.summary.inc(diff_rel.action.value)
                        self._add_node_summary(node_id=node_in_rel, action=diff_rel.action)
                        self._add_node_element_relationship(
                            node_id=node_diff.id,
                            element_name=diff_rel.name,
                            branch=branch_name,
                            relationship=diff_rel,
                        )

                if node_diff:
                    self.diffs.append(node_diff)

    async def generate_diff_payload(self) -> BranchDiff:
        # Query the Diff per Nodes and per Relationships from the database

        self.rels = await self.diff.get_relationships(session=self.session)

        await self._prepare()
        # Organize the Relationships data per node and per relationship name in order to simplify the association with the nodes Later on.

        await self._process_nodes()
        await self._process_relationships()
        # conflict_data = {conflict.path: conflict for conflict in self.conflicts}

        return BranchDiff(
            diffs=list(self.entries.values()),
        )


async def generate_diff_payload(  # pylint: disable=too-many-branches,too-many-statements
    session: AsyncSession, diff: Diff, kinds_to_include: Optional[List[str]] = None
) -> Dict[str, List[BranchDiffNode]]:
    response = defaultdict(list)
    nodes_in_diff = []

    # Query the Diff per Nodes and per Relationships from the database
    nodes = await diff.get_nodes(session=session)
    rels = await diff.get_relationships(session=session)

    # Organize the Relationships data per node and per relationship name in order to simplify the association with the nodes Later on.
    rels_per_node = await diff.get_relationships_per_node(session=session)
    node_ids = await diff.get_node_id_per_kind(session=session)

    display_labels = await get_display_labels(nodes=node_ids, session=session)

    # Generate the Diff per node and associated the appropriate relationships if they are present in the schema
    for branch_name, items in nodes.items():  # pylint: disable=too-many-nested-blocks
        branch_display_labels = display_labels.get(branch_name, {})
        for item in items.values():
            if kinds_to_include and item.kind not in kinds_to_include:
                continue

            item_graphql = item.to_graphql()

            # We need to convert the list of attributes to a dict under elements
            item_dict = copy.deepcopy(item_graphql)
            del item_dict["attributes"]
            item_elements = {attr["name"]: attr for attr in item_graphql["attributes"]}

            node_diff = BranchDiffNode(
                **item_dict, elements=item_elements, display_label=branch_display_labels.get(item.id, "")
            )

            schema = registry.get_schema(name=node_diff.kind, branch=node_diff.branch)

            # Extract the value from the list of properties
            for _, element in node_diff.elements.items():
                node_diff.summary.inc(element.action.value)

                for prop in element.properties:
                    if prop.type == "HAS_VALUE":
                        element.value = prop
                    else:
                        element.summary.inc(prop.action.value)

                if element.value:
                    element.properties.remove(element.value)

            if item.id in rels_per_node[branch_name]:
                for rel_name, rels in rels_per_node[branch_name][item.id].items():
                    if rel_schema := schema.get_relationship_by_identifier(id=rel_name, raise_on_error=False):
                        diff_rel = None
                        if rel_schema.cardinality == RelationshipCardinality.ONE:
                            diff_rel = extract_diff_relationship_one(
                                node_id=item.id,
                                name=rel_schema.name,
                                identifier=rel_name,
                                rels=rels,
                                display_labels=branch_display_labels,
                            )
                        elif rel_schema.cardinality == RelationshipCardinality.MANY:
                            diff_rel = extract_diff_relationship_many(
                                node_id=item.id,
                                name=rel_schema.name,
                                identifier=rel_name,
                                rels=rels,
                                display_labels=branch_display_labels,
                            )

                        if diff_rel:
                            node_diff.elements[diff_rel.name] = diff_rel
                            node_diff.summary.inc(diff_rel.action.value)

            response[branch_name].append(node_diff)
            nodes_in_diff.append(node_diff.id)

    # Check if all nodes associated with a relationship have been accounted for
    # If a node is missing it means its changes are only related to its relationships
    for branch_name, _ in rels_per_node.items():
        branch_display_labels = display_labels.get(branch_name, {})
        for node_in_rel, _ in rels_per_node[branch_name].items():
            if node_in_rel in nodes_in_diff:
                continue

            node_diff = None
            for rel_name, rels in rels_per_node[branch_name][node_in_rel].items():
                node_kind = rels[0].nodes[node_in_rel].kind

                if kinds_to_include and node_kind not in kinds_to_include:
                    continue

                schema = registry.get_schema(name=node_kind, branch=branch_name)
                rel_schema = schema.get_relationship_by_identifier(id=rel_name, raise_on_error=False)
                if not rel_schema:
                    continue

                if not node_diff:
                    node_diff = BranchDiffNode(
                        branch=branch_name,
                        id=node_in_rel,
                        kind=node_kind,
                        action=DiffAction.UPDATED,
                        display_label=branch_display_labels.get(node_in_rel, ""),
                    )

                if rel_schema.cardinality == RelationshipCardinality.ONE:
                    diff_rel = extract_diff_relationship_one(
                        node_id=node_in_rel,
                        name=rel_schema.name,
                        identifier=rel_name,
                        rels=rels,
                        display_labels=branch_display_labels,
                    )
                    if diff_rel:
                        node_diff.elements[diff_rel.name] = diff_rel
                        node_diff.summary.inc(diff_rel.action.value)

                elif rel_schema.cardinality == RelationshipCardinality.MANY:
                    diff_rel = extract_diff_relationship_many(
                        node_id=node_in_rel,
                        name=rel_schema.name,
                        identifier=rel_name,
                        rels=rels,
                        display_labels=branch_display_labels,
                    )
                    if diff_rel:
                        node_diff.elements[diff_rel.name] = diff_rel
                        node_diff.summary.inc(diff_rel.action.value)

            if node_diff:
                response[branch_name].append(node_diff)

    return response


@router.get("/data")
async def get_diff_data_deprecated(
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> Dict[str, List[BranchDiffNode]]:
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    schema = registry.schema.get_full(branch=branch)
    return await generate_diff_payload(diff=diff, session=session, kinds_to_include=list(schema.keys()))


@router.get("/schema")
async def get_diff_schema_deprecated(
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> Dict[str, List[BranchDiffNode]]:
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    return await generate_diff_payload(diff=diff, session=session, kinds_to_include=INTERNAL_SCHEMA_NODE_KINDS)


@router.get("/data-new")
async def get_diff_data(
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> BranchDiff:
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    schema = registry.schema.get_full(branch=branch)
    diff_payload = DiffPayload(session=session, diff=diff, kinds_to_include=list(schema.keys()))
    return await diff_payload.generate_diff_payload()


@router.get("/schema-new")
async def get_diff_schema(
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> BranchDiff:
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    diff_payload = DiffPayload(session=session, diff=diff, kinds_to_include=INTERNAL_SCHEMA_NODE_KINDS)
    return await diff_payload.generate_diff_payload()


@router.get("/files")
async def get_diff_files(
    request: Request,
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> Dict[str, Dict[str, BranchDiffRepository]]:
    response: Dict[str, Dict[str, BranchDiffRepository]] = defaultdict(dict)
    rpc_client: InfrahubRpcClient = request.app.state.rpc_client

    # Query the Diff for all files and repository from the database
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    diff_files = await diff.get_files(session=session, rpc_client=rpc_client)

    for branch_name, items in diff_files.items():
        for item in items:
            if item.repository not in response[branch_name]:
                response[branch_name][item.repository] = BranchDiffRepository(
                    id=item.repository,
                    display_name=f"Repository ({item.repository})",
                    commit_from=item.commit_from,
                    commit_to=item.commit_to,
                    branch=branch_name,
                )

            response[branch_name][item.repository].files.append(BranchDiffFile(**item.to_graphql()))

    return response


@router.get("/artifacts")
async def get_diff_artifacts(
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> Dict[str, BranchDiffArtifact]:
    response = {}

    # Query the Diff for all artifacts
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    payload = await generate_diff_payload(diff=diff, session=session, kinds_to_include=["CoreArtifact"])

    for branch_name, data in payload.items():
        for node in data:
            if "storage_id" not in node.elements or "checksum" not in node.elements:
                continue

            diff_artifact = BranchDiffArtifact(
                id=node.id, action=node.action, branch=branch_name, display_label=node.display_label
            )

            if node.action in [DiffAction.UPDATED, DiffAction.ADDED]:
                diff_artifact.item_new = BranchDiffArtifactStorage(
                    storage_id=node.elements["storage_id"].value.value.new,
                    checksum=node.elements["checksum"].value.value.new,
                )

            if node.action in [DiffAction.UPDATED, DiffAction.REMOVED]:
                diff_artifact.item_previous = BranchDiffArtifactStorage(
                    storage_id=node.elements["storage_id"].value.value.previous,
                    checksum=node.elements["checksum"].value.value.previous,
                )

            response[node.id] = diff_artifact

    return response
