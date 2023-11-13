from __future__ import annotations

import enum
from typing import List

from infrahub.exceptions import ValidationError
from infrahub.utils import InfrahubNumberEnum, InfrahubStringEnum

GLOBAL_BRANCH_NAME = "-global-"

RESERVED_BRANCH_NAMES = [GLOBAL_BRANCH_NAME]

RESERVED_ATTR_REL_NAMES = [
    "any",
    "attribute",
    "attributes",
    "attr",
    "attrs",
    "relationship",
    "relationships",
    "rel",
    "rels",
]


class PermissionLevel(enum.Flag):
    READ = 1
    WRITE = 2
    ADMIN = 3
    DEFAULT = 0


class AccountRole(InfrahubStringEnum):
    ADMIN = "admin"
    READ_ONLY = "read-only"
    READ_WRITE = "read-write"


class AccountType(InfrahubStringEnum):
    USER = "User"
    SCRIPT = "Script"
    BOT = "Bot"
    Git = "Git"


class ArtifactStatus(InfrahubStringEnum):
    ERROR = "Error"
    PENDING = "Pending"
    PROCESSING = "Processing"
    READY = "Ready"


class BranchSupportType(InfrahubStringEnum):
    AWARE = "aware"
    AGNOSTIC = "agnostic"
    LOCAL = "local"


class BranchConflictKeep(InfrahubStringEnum):
    TARGET = "target"
    SOURCE = "source"


class ContentType(InfrahubStringEnum):
    APPLICATION_JSON = "application/json"
    TEXT_PLAIN = "text/plain"


class CriticalityLevel(InfrahubNumberEnum):
    one = 1
    two = 2
    three = 3
    four = 4
    five = 5
    six = 6
    seven = 7
    eight = 8
    nine = 9
    ten = 1


class DiffAction(InfrahubStringEnum):
    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


class MutationAction(InfrahubStringEnum):
    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"
    UNDEFINED = "undefined"


class PathType(InfrahubStringEnum):
    NODE = "node"
    ATTRIBUTE = "attribute"
    RELATIONSHIP_ONE = "relationship_one"
    RELATIONSHIP_MANY = "relationship_many"

    @classmethod
    def from_relationship(cls, relationship: RelationshipCardinality) -> PathType:
        if relationship == RelationshipCardinality.ONE:
            return cls("relationship_one")

        return cls("relationship_many")


class FilterSchemaKind(InfrahubStringEnum):
    TEXT = "Text"
    LIST = "Text"
    NUMBER = "Number"
    BOOLEAN = "Boolean"
    OBJECT = "Object"
    MULTIOBJECT = "MultiObject"
    ENUM = "Enum"


class ProposedChangeState(InfrahubStringEnum):
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    CANCELED = "canceled"

    def validate_state_check_run(self) -> None:
        if self == ProposedChangeState.OPEN:
            return

        raise ValidationError(input_value="Unable to trigger check on proposed changes that aren't in the open state")

    def validate_state_transition(self, updated_state: ProposedChangeState) -> None:
        if self == ProposedChangeState.OPEN:
            return
        if self in [ProposedChangeState.CANCELED, ProposedChangeState.MERGED]:
            raise ValidationError(
                input_value=f"A proposed change is not allowed to transition from the {self.value} state"
            )
        if self == ProposedChangeState.CLOSED and updated_state not in [
            ProposedChangeState.CANCELED,
            ProposedChangeState.OPEN,
        ]:
            raise ValidationError(
                input_value="A closed proposed change is only allowed to transition to the open state"
            )


class RelationshipCardinality(InfrahubStringEnum):
    ONE = "one"
    MANY = "many"


class RelationshipKind(InfrahubStringEnum):
    GENERIC = "Generic"
    ATTRIBUTE = "Attribute"
    COMPONENT = "Component"
    PARENT = "Parent"
    GROUP = "Group"


class RelationshipStatus(InfrahubStringEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class Severity(InfrahubStringEnum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidatorConclusion(InfrahubStringEnum):
    UNKNOWN = "unknown"
    FAILURE = "failure"
    SUCCESS = "success"


class ValidatorState(InfrahubStringEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


RESTRICTED_NAMESPACES: List[str] = [
    "Account",
    "Branch",
    "Builtin",
    # "Core",
    "Deprecated",
    "Diff",
    "Infrahub",
    "Internal",
    "Lineage",
]
