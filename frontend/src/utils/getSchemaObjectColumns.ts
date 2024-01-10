import * as R from "ramda";
import {
  attributesKindForDetailsView,
  attributesKindForListView,
  relationshipsForDetailsView,
  relationshipsForListView,
  relationshipsForTabs,
} from "../config/constants";
import { iGenericSchema, iNodeSchema } from "../state/atoms/schema.atom";

export const getObjectAttributes = (
  schema: iNodeSchema | iGenericSchema,
  fromListView?: boolean
) => {
  if (!schema) {
    return [];
  }

  const kinds = fromListView ? attributesKindForListView : attributesKindForDetailsView;

  const attributes = (schema.attributes || [])
    .filter((attribute) => kinds.includes(attribute.kind))
    .map((row) => ({
      label: row.label ?? "",
      name: row.name,
      kind: row.kind,
    }));

  return attributes;
};

export const getObjectRelationships = (
  schema?: iNodeSchema | iGenericSchema,
  fromListView?: boolean
) => {
  if (!schema) {
    return [];
  }

  const kinds = fromListView ? relationshipsForListView : relationshipsForDetailsView;

  const relationships = (schema.relationships || [])
    .filter((relationship) => kinds[relationship.cardinality].includes(relationship.kind ?? ""))
    .map((relationship) => ({
      label: relationship.label ?? "",
      name: relationship.name,
      paginated: relationship.cardinality === "many",
    }));

  return relationships;
};

export const getTabs = (schema: iNodeSchema | iGenericSchema) => {
  if (!schema) {
    return [];
  }

  // Relationship kind to show in LIST VIEW - Attribute, Parent
  const relationships = (schema.relationships || [])
    .filter((relationship) =>
      relationshipsForTabs[relationship.cardinality].includes(relationship.kind)
    )
    .map((relationship) => ({
      label: relationship.label,
      name: relationship.name,
    }));

  return relationships;
};

export const getSchemaObjectColumns = (
  schema?: iNodeSchema | iGenericSchema,
  fromListView?: boolean
) => {
  if (!schema) {
    return [];
  }

  const attributes = getObjectAttributes(schema, fromListView);
  const relationships = getObjectRelationships(schema, fromListView);

  const columns = R.concat(attributes, relationships);
  return columns;
};

export const getGroupColumns = (schema?: iNodeSchema | iGenericSchema) => {
  if (!schema) {
    return [];
  }

  const defaultColumns = [{ label: "Type", name: "__typename" }];
  const attributes = getObjectAttributes(schema);
  const relationships = getObjectRelationships(schema);

  const columns = R.concat(attributes, relationships);

  return [...defaultColumns, ...columns];
};

export const getAttributeColumnsFromNodeOrGenericSchema = (
  schemaList: iNodeSchema[],
  generics: iGenericSchema[],
  kind: String,
  fromListView?: boolean
) => {
  const generic = generics.find((g) => g.kind === kind);
  const peerSchema = schemaList.find((s) => s.kind === kind);

  if (generic) {
    return getObjectAttributes(generic, fromListView);
  }
  if (peerSchema) {
    return getObjectAttributes(peerSchema, fromListView);
  }
  return [];
};

export const getObjectTabs = (tabs: any[], data: any) => {
  return tabs.map((tab: any) => ({
    ...tab,
    count: data[tab.name].count,
  }));
};
