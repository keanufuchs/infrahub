import { CheckIcon, ShieldCheckIcon } from "@heroicons/react/24/outline";
import { formatDistanceToNow } from "date-fns";
import { useAtom } from "jotai";
import * as R from "ramda";
import { toast } from "react-toastify";
import { Alert, ALERT_TYPES } from "../../components/alert";
import { Badge } from "../../components/badge";
import { Button, BUTTON_TYPES } from "../../components/button";
import { Pill } from "../../components/pill";
import { Tooltip } from "../../components/tooltip";
import { branchesState } from "../../state/atoms/branches.atom";

export const BranchesItems = () => {
  const [storedBranches] = useAtom(branchesState);

  const sortByName = R.sortBy(R.compose(R.toLower, R.prop("name")));

  const sortedBranches = sortByName(storedBranches.filter(b => b.name !== "main"));

  const branches = [
    ...storedBranches.filter(b => b.name === "main"),
    ...sortedBranches
  ];

  const mergeBranch = (id: string) => {
    toast(<Alert type={ALERT_TYPES.SUCCESS} message={"Super relevant message here"} />);
  };

  const rebaseBranch = (id: string) => {
    toast(<Alert type={ALERT_TYPES.INFO} message={"Super relevant message here"} />);
  };

  const validateBranch = (id: string) => {
    toast(<Alert type={ALERT_TYPES.WARNING} message={"Super relevant message here"} />);
  };

  const createPullRequest = (id: string) => {
    toast(<Alert message={"Super relevant message here"} />);
  };

  const deleteBranch = (id: string) => {
    toast(<Alert type={ALERT_TYPES.ERROR} message={"Super relevant message here"} />);
  };

  return (
    <ul className="grid gap-6 grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 p-6">
      {
        branches.map(
          (branch) => (
            <li key={branch.name} className="col-span-1 divide-y divide-gray-200 rounded-lg bg-white shadow">
              <div className="flex w-full items-center justify-between space-x-6 p-6">
                <div className="flex flex-1">
                  <div className="flex flex-1 flex-col">
                    <div className="flex flex-1 items-center space-x-3">
                      {
                        branch.is_default
                          && (
                            <Tooltip message={"Default branch"}>
                              <ShieldCheckIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                            </Tooltip>
                          )
                      }

                      <h3 className="text-sm font-medium text-gray-900 py-0.5">{branch.name}</h3>

                      {
                        !branch.is_default
                          && (
                            <Tooltip message={"Origin branch"}>
                              <Badge>{branch.origin_branch}</Badge>
                            </Tooltip>
                          )
                      }
                    </div>

                    <p className="mt-2 text-sm text-gray-500">
                      {branch.description || "-"}
                    </p>
                  </div>

                  <div className="flex flex-col items-end">
                    <Pill>Branched {formatDistanceToNow(new Date(branch.branched_from), { addSuffix: true })}</Pill>

                    {
                      !branch.is_default
                        && (
                          <Pill className="mt-2">Created {formatDistanceToNow(new Date(branch.created_at), { addSuffix: true })}</Pill>
                        )
                    }
                  </div>
                </div>
              </div>
              <div>
                <div className="-mt-px px-3 py-3 flex divide-x divide-gray-200">
                  <div className="flex w-0 flex-1 flex-col md:flex-row">
                    {
                      !branch.is_default
                      && (
                        <>
                          <Button
                            className="mr-0 md:mr-3"
                            onClick={() => mergeBranch(branch.id)}
                            type={BUTTON_TYPES.VALIDATE}
                            disabled
                          >
                            Merge
                            <CheckIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                          </Button>

                          <Button
                            className="mr-0 md:mr-3"
                            onClick={() => createPullRequest(branch.id)}
                            disabled
                          >
                            Pull request
                            <CheckIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                          </Button>

                          <Button
                            className="mr-0 md:mr-3"
                            onClick={() => rebaseBranch(branch.id)}
                            disabled
                          >
                            Rebase
                            <CheckIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                          </Button>

                          <Button
                            className="mr-0 md:mr-3"
                            onClick={() => validateBranch(branch.id)}
                            type={BUTTON_TYPES.WARNING}
                          >
                            Validate
                            <ShieldCheckIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                          </Button>

                          <Button
                            className="mr-0 md:mr-3"
                            onClick={() => deleteBranch(branch.id)}
                            type={BUTTON_TYPES.CANCEL}
                            disabled
                          >
                            Delete
                            <ShieldCheckIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                          </Button>
                        </>
                      )
                    }
                  </div>
                </div>
              </div>
            </li>
          )
        )
      }
    </ul>
  );
};