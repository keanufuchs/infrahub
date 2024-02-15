from infrahub_sync.adapters.nautobot import NautobotAdapter

from .sync_models import (
 BuiltinLocation,
 BuiltinRole,
 BuiltinStatus,
 BuiltinTag,
 CoreOrganization,
 CoreStandardGroup,
 InfraAutonomousSystem,
 InfraCircuit,
 InfraDevice,
 InfraIPAddress,
 InfraPlatform,
 InfraPrefix,
 InfraProviderNetwork,
 InfraRack,
 InfraRouteTarget,
 InfraVLAN,
 InfraVRF,
 TemplateCircuitType,
 TemplateDeviceType,
)


# -------------------------------------------------------
# AUTO-GENERATED FILE, DO NOT MODIFY
#  This file has been generated with the command `infrahub-sync generate`
#  All modifications will be lost the next time you reexecute this command
# -------------------------------------------------------
class NautobotSync(NautobotAdapter):
 CoreStandardGroup = CoreStandardGroup
 BuiltinTag = BuiltinTag
 InfraAutonomousSystem = InfraAutonomousSystem
 InfraCircuit = InfraCircuit
 TemplateCircuitType = TemplateCircuitType
 InfraDevice = InfraDevice
 TemplateDeviceType = TemplateDeviceType
 InfraIPAddress = InfraIPAddress
 InfraPlatform = InfraPlatform
 InfraProviderNetwork = InfraProviderNetwork
 InfraPrefix = InfraPrefix
 InfraRack = InfraRack
 InfraRouteTarget = InfraRouteTarget
 InfraVLAN = InfraVLAN
 InfraVRF = InfraVRF
 CoreOrganization = CoreOrganization
 BuiltinStatus = BuiltinStatus
 BuiltinRole = BuiltinRole
 BuiltinLocation = BuiltinLocation
