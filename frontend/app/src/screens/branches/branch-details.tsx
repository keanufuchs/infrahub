import { BUTTON_TYPES, Button } from "@/components/buttons/button";
import { Badge } from "@/components/display/badge";
import { DateDisplay } from "@/components/display/date-display";
import SlideOver from "@/components/display/slide-over";
import ObjectForm from "@/components/form/object-form";
import ModalDelete from "@/components/modals/modal-delete";
import { ALERT_TYPES, Alert } from "@/components/ui/alert";
import { PROPOSED_CHANGES_OBJECT } from "@/config/constants";
import { QSP } from "@/config/qsp";
import graphqlClient from "@/graphql/graphqlClientApollo";
import { deleteBranch } from "@/graphql/mutations/branches/deleteBranch";
import { mergeBranch } from "@/graphql/mutations/branches/mergeBranch";
import { rebaseBranch } from "@/graphql/mutations/branches/rebaseBranch";
import { validateBranch } from "@/graphql/mutations/branches/validateBranch";
import { getBranchDetailsQuery } from "@/graphql/queries/branches/getBranchDetails";
import { useAuth } from "@/hooks/useAuth";
import useQuery from "@/hooks/useQuery";
import ErrorScreen from "@/screens/errors/error-screen";
import NoDataFound from "@/screens/errors/no-data-found";
import LoadingScreen from "@/screens/loading-screen/loading-screen";
import { branchesState } from "@/state/atoms/branches.atom";
import { datetimeAtom } from "@/state/atoms/time.atom";
import { objectToString } from "@/utils/common";
import { constructPath, getCurrentQsp } from "@/utils/fetch";
import { gql } from "@apollo/client";
import { CheckIcon, ShieldCheckIcon } from "@heroicons/react/20/solid";
import { ArrowPathIcon, PlusIcon, TrashIcon } from "@heroicons/react/24/outline";
import { Icon } from "@iconify-icon/react";
import { useAtom } from "jotai";
import { useAtomValue } from "jotai/index";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";

export const BranchDetails = () => {
  const { "*": branchName } = useParams();
  const date = useAtomValue(datetimeAtom);
  const { isAuthenticated } = useAuth();
  const [branches, setBranches] = useAtom(branchesState);

  const [isLoadingRequest, setIsLoadingRequest] = useState(false);
  const [displayModal, setDisplayModal] = useState(false);
  const [detailsContent, setDetailsContent] = useState({});
  const [showCreateDrawer, setShowCreateDrawer] = useState(false);

  const navigate = useNavigate();

  const branchAction = async ({ successMessage, errorMessage, request, options }: any) => {
    if (!branchName) return;

    try {
      setIsLoadingRequest(true);

      const mutationString = request({ data: objectToString(options) });

      const mutation = gql`
        ${mutationString}
      `;

      const result = await graphqlClient.mutate({
        mutation,
        context: {
          branch: branchName,
          date,
        },
      });

      setDetailsContent(result);

      toast(<Alert type={ALERT_TYPES.SUCCESS} message={successMessage} />, {
        toastId: "alert-success",
      });
    } catch (error: any) {
      setDetailsContent(error);

      toast(<Alert type={ALERT_TYPES.SUCCESS} message={errorMessage} />);
    }

    setIsLoadingRequest(false);
  };

  const { loading, error, data } = useQuery(getBranchDetailsQuery, { variables: { branchName } });

  if (loading) {
    return <LoadingScreen />;
  }

  if (error) {
    return <ErrorScreen message="Something went wrong when fetching the branch details." />;
  }

  const branchData = data?.Branch;

  if (!branchData || branchData.length === 0) {
    return <NoDataFound message={`Branch ${branchName} does not exists.`} />;
  }

  const branch = branchData[0];

  return (
    <div className="bg-custom-white">
      {displayModal && (
        <ModalDelete
          title="Delete"
          description={
            <>
              Are you sure you want to remove the branch
              <br /> <b>`{branch?.name}`</b>?
            </>
          }
          onCancel={() => setDisplayModal(false)}
          onDelete={async () => {
            await branchAction({
              successMessage: "Branch deleted successfully!",
              errorMessage: "An error occurred while deleting the branch",
              request: deleteBranch,
              options: {
                name: branch.name,
              },
            });

            const queryStringParams = getCurrentQsp();
            const isDeletedBranchSelected = queryStringParams.get(QSP.BRANCH) === branch.name;

            const path = isDeletedBranchSelected
              ? constructPath("/branches", [{ name: QSP.BRANCH, exclude: true }])
              : constructPath("/branches");

            navigate(path);
            const nextBranches = branches.filter(({ name }) => name !== branch.name);
            setBranches(nextBranches);
          }}
          open={displayModal}
          setOpen={() => setDisplayModal(false)}
        />
      )}

      {!loading && branch?.name && (
        <>
          <div className="border-t border-b border-gray-200 px-2 py-2">
            <dl className="divide-y divide-gray-200">
              <div className="p-2 grid grid-cols-3 gap-4 text-xs">
                <dt className="text-sm font-medium text-gray-500">Name</dt>
                <dd className="flex text-gray-900">{branch.name}</dd>
              </div>
              <div className="p-2 grid grid-cols-3 gap-4 text-xs">
                <dt className="text-sm font-medium text-gray-500">Origin branch</dt>
                <dd className="flex text-gray-900">
                  <Badge className="text-sm">{branch.origin_branch}</Badge>
                </dd>
              </div>
              <div className="p-2 grid grid-cols-3 gap-4 text-xs">
                <dt className="text-sm font-medium text-gray-500">Branched</dt>
                <dd className="flex text-gray-900">
                  <DateDisplay date={branch.branched_at} />
                </dd>
              </div>
              <div className="p-2 grid grid-cols-3 gap-4 text-xs">
                <dt className="text-sm font-medium text-gray-500">Created</dt>
                <dd className="flex text-gray-900">
                  <DateDisplay date={branch.created_at} />
                </dd>
              </div>
            </dl>
          </div>
        </>
      )}

      <div className="p-6">
        <div className="mb-6">
          {branch?.name && (
            <>
              <div className="flex flex-1 flex-col md:flex-row">
                <Button
                  disabled={!isAuthenticated || branch.is_default}
                  className="mr-0 md:mr-3"
                  onClick={() =>
                    branchAction({
                      successMessage: "Branch merged successfully!",
                      errorMessage: "An error occurred while merging the branch",
                      request: mergeBranch,
                      options: {
                        name: branch.name,
                      },
                    })
                  }
                  buttonType={BUTTON_TYPES.VALIDATE}
                >
                  Merge
                  <CheckIcon className="ml-2 h-4 w-4" aria-hidden="true" />
                </Button>

                <Button
                  disabled={!isAuthenticated || branch.is_default}
                  className="mr-0 md:mr-3"
                  onClick={() => setShowCreateDrawer(true)}
                >
                  Propose change
                  <PlusIcon className="ml-2 h-4 w-4" aria-hidden="true" />
                </Button>

                <Button
                  disabled={!isAuthenticated || branch.is_default}
                  className="mr-0 md:mr-3"
                  onClick={() =>
                    branchAction({
                      successMessage: "Branch rebased successfully!",
                      errorMessage: "An error occurred while rebasing the branch",
                      request: rebaseBranch,
                      options: {
                        name: branch.name,
                      },
                    })
                  }
                >
                  Rebase
                  <ArrowPathIcon className="ml-2 h-4 w-4" aria-hidden="true" />
                </Button>

                <Button
                  disabled={branch.is_default}
                  className="mr-0 md:mr-3"
                  onClick={() =>
                    branchAction({
                      successMessage: "The branch is valid!",
                      errorMessage: "An error occurred while validating the branch",
                      request: validateBranch,
                      options: {
                        name: branch.name,
                      },
                    })
                  }
                  buttonType={BUTTON_TYPES.WARNING}
                >
                  Validate
                  <ShieldCheckIcon className="ml-2 h-4 w-4" aria-hidden="true" />
                </Button>

                <Button
                  disabled={!isAuthenticated || branch.is_default}
                  className="mr-0 md:mr-3"
                  onClick={() => setDisplayModal(true)}
                  buttonType={BUTTON_TYPES.CANCEL}
                >
                  Delete
                  <TrashIcon className="ml-2 h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </>
          )}
        </div>

        {isLoadingRequest && (
          <div className="">
            <LoadingScreen />
          </div>
        )}

        {detailsContent && !isLoadingRequest && (
          <div className="">
            <pre>{JSON.stringify(detailsContent, null, 2)}</pre>
          </div>
        )}
      </div>

      <SlideOver
        title={
          <div className="space-y-2">
            <div className="flex items-center w-full">
              <span className="text-lg font-semibold mr-3">Create Proposed Changes</span>
              <div className="flex-1"></div>
              <div className="flex items-center">
                <Icon icon={"mdi:layers-triple"} />
                <div className="ml-1.5 pb-1">{branch?.name}</div>
              </div>
            </div>
            <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20 mr-2">
              <svg
                className="h-1.5 w-1.5 mr-1 fill-yellow-500"
                viewBox="0 0 6 6"
                aria-hidden="true"
              >
                <circle cx={3} cy={3} r={3} />
              </svg>
              {PROPOSED_CHANGES_OBJECT}
            </span>
          </div>
        }
        open={showCreateDrawer}
        setOpen={setShowCreateDrawer}
      >
        <ObjectForm
          kind={PROPOSED_CHANGES_OBJECT}
          onSuccess={() => setShowCreateDrawer(false)}
          onCancel={() => setShowCreateDrawer(false)}
        />
      </SlideOver>
    </div>
  );
};
