import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import { NODE_PATH_EXCLUDELIST } from "@/config/constants";
import { tDataDiffNode, tDataDiffNodePropertyChange } from "@/screens/diff/data-diff-node";
import { Icon } from "@iconify-icon/react";

export const displayValue = (value: any) => {
  if (typeof value === "boolean") {
    return `${value}`;
  }

  if (value === "NULL") {
    return "-";
  }

  return value?.display_label || value || "-";
};

const getValueTooltip = (value: any) => {
  if (!value?.kind) {
    return null;
  }

  return (
    <div className="flex items-center">
      Kind: <Badge>{value.kind}</Badge>
    </div>
  );
};

// Display the values
// (only new one for "added", only old ones for "deleted", and previous + new for "updated")
export const diffContent: { [key: string]: any } = {
  added: (property: tDataDiffNodePropertyChange) => {
    const { value } = property;

    const { new: newValue } = value;

    const newMesage = getValueTooltip(newValue);

    return (
      <div className="flex">
        {newMesage ? (
          <Tooltip enabled content={newMesage}>
            <Badge variant="green-outline">{displayValue(newValue)}</Badge>
          </Tooltip>
        ) : (
          <Badge variant="green-outline">{displayValue(newValue)}</Badge>
        )}
      </div>
    );
  },
  removed: (property: tDataDiffNodePropertyChange) => {
    const { value } = property;

    const { previous: previousValue } = value;

    const previousMessage = getValueTooltip(previousValue);

    return (
      <div className="flex">
        {previousMessage ? (
          <Tooltip enabled content={previousMessage}>
            <Badge variant="red-outline">{displayValue(previousValue)}</Badge>
          </Tooltip>
        ) : (
          <Badge variant="red-outline">{displayValue(previousValue)}</Badge>
        )}
      </div>
    );
  },
  updated: (property: tDataDiffNodePropertyChange) => {
    const { value } = property;

    const { new: newValue, previous: previousValue } = value;

    const previousMessage = getValueTooltip(previousValue);
    const newMessage = getValueTooltip(newValue);

    return (
      <div className="flex items-center">
        <div className="flex items-center">
          {previousMessage ? (
            <Tooltip enabled content={previousMessage}>
              <Badge variant="blue-outline">{displayValue(previousValue)}</Badge>
            </Tooltip>
          ) : (
            <Badge variant="blue-outline">{displayValue(previousValue)}</Badge>
          )}
        </div>

        <div className="flex items-center">
          <Icon icon={"mdi:chevron-right"} className="mx-2" aria-hidden="true" />
        </div>

        <div className="flex">
          {newMessage ? (
            <Tooltip enabled content={newMessage}>
              <Badge variant="blue-outline">{displayValue(newValue)}</Badge>
            </Tooltip>
          ) : (
            <Badge variant="blue-outline">{displayValue(newValue)}</Badge>
          )}
        </div>
      </div>
    );
  },
  conflict: (property: tDataDiffNodePropertyChange) => {
    const { value } = property;

    const { new: newValue, previous: previousValue } = value;

    const previousMessage = getValueTooltip(previousValue);

    const newMesage = getValueTooltip(newValue);

    return (
      <div className="flex items-center">
        <div className="flex items-center">
          {previousMessage ? (
            <Tooltip enabled content={previousMessage}>
              <Badge variant="blue-outline">{displayValue(previousValue)}</Badge>
            </Tooltip>
          ) : (
            <Badge variant="blue-outline">{displayValue(previousValue)}</Badge>
          )}
        </div>

        <div className="flex items-center">
          <Icon icon={"mdi:chevron-right"} className="mx-2" aria-hidden="true" />
        </div>

        <div className="flex">
          {newMesage ? (
            <Tooltip enabled content={newMesage}>
              <Badge variant="blue-outline">{displayValue(newValue)}</Badge>
            </Tooltip>
          ) : (
            <Badge variant="blue-outline">{displayValue(newValue)}</Badge>
          )}
        </div>
      </div>
    );
  },
};

export const getThreadLabel = (node?: tDataDiffNode, currentBranch?: string, path?: string) => {
  // Get main object name
  const objectName = node?.display_label && currentBranch && node?.display_label[currentBranch];

  const nodePath = path
    ?.split("/")
    // Get the path without the beginning "data/xxxx-xxxx-xxxx-xxxx"
    .slice(2)
    // Do not include some values from the path
    .filter((item) => !NODE_PATH_EXCLUDELIST.includes(item));

  // Construct path like "item1 > item2 > item3"
  const nodeLabel = nodePath?.reduce((acc, item) => (acc ? `${acc} > ${item}` : item), "").trim();

  if (objectName) {
    return `${objectName} > ${nodeLabel}`;
  }

  return nodeLabel;
};

// Get thread title from the thread or a defined label
export const getThreadTitle = (thread?: any, label?: string) => {
  const string = thread?.label?.value ?? thread?.display_label ?? label;

  if (!string) {
    return "";
  }

  return (
    <div className="flex mb-2">
      {string && <Badge variant={string === "Conversation" ? null : "green"}>{string}</Badge>}
    </div>
  );
};

const badgeTypes: { [key: string]: string } = {
  added: "green",
  updated: "blue",
  removed: "red",
};

export const getBadgeType = (action?: string) => {
  if (!action) return undefined;

  return badgeTypes[action];
};
