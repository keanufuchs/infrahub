from dataclasses import dataclass
from typing import Optional

from infrahub.core import registry
from infrahub.core.branch import Branch
from infrahub.core.constants import RelationshipCardinality
from infrahub.core.query.node import NodeListGetInfoQuery
from infrahub.core.schema.generic_schema import GenericSchema
from infrahub.database import InfrahubDatabase
from infrahub.exceptions import ValidationError

from ..model import RelationshipManager, RelationshipUpdateDetails
from .interface import RelationshipManagerConstraintInterface


@dataclass
class NodeToValidate:
    uuid: str
    cardinality: RelationshipCardinality
    min_count: Optional[int] = None
    max_count: Optional[int] = None


class RelationshipPeerKindConstraint(RelationshipManagerConstraintInterface):
    def __init__(self, db: InfrahubDatabase, branch: Optional[Branch] = None):
        self.db = db
        self.branch = branch

    async def check(self, relm: RelationshipManager, update_details: RelationshipUpdateDetails) -> None:
        branch = await registry.get_branch(db=self.db) if not self.branch else self.branch
        peer_schema = registry.schema.get(name=relm.schema.peer, branch=branch, duplicate=False)
        if isinstance(peer_schema, GenericSchema):
            allowed_kinds = peer_schema.used_by
        else:
            allowed_kinds = [peer_schema.kind]

        if not update_details.peer_ids_present_local_only:
            return

        peers_query = await NodeListGetInfoQuery.init(
            db=self.db, branch=branch, ids=update_details.peer_ids_present_local_only
        )
        await peers_query.execute(db=self.db)

        errors: list[ValidationError] = []
        async for peer_node in peers_query.get_nodes(db=self.db, duplicate=False):
            if not peer_node.schema:
                raise ValueError(f"Cannot identify schema for node {peer_node.node_uuid}")
            if peer_node.schema.kind not in allowed_kinds:
                errors.append(
                    ValidationError(
                        {
                            relm.name: (
                                f"{peer_node.schema.kind} - {peer_node.node_uuid} cannot be added to relationship, "
                                f"must be of type: {allowed_kinds}"
                            )
                        }
                    )
                )

        if not errors:
            return

        raise ValidationError(errors)
