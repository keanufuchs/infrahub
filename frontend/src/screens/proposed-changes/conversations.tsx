import { gql, useReactiveVar } from "@apollo/client";
import { PencilIcon, Square3Stack3DIcon } from "@heroicons/react/24/outline";
import { formatISO } from "date-fns";
import { useAtom } from "jotai";
import { useContext, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";
import { ALERT_TYPES, Alert } from "../../components/alert";
import { AVATAR_SIZE, Avatar } from "../../components/avatar";
import { Badge } from "../../components/badge";
import { Button } from "../../components/button";
import { AddComment } from "../../components/conversations/add-comment";
import { Thread } from "../../components/conversations/thread";
import { DateDisplay } from "../../components/date-display";
import SlideOver from "../../components/slide-over";
import { Tooltip } from "../../components/tooltip";
import {
  ACCOUNT_OBJECT,
  DEFAULT_BRANCH_NAME,
  PROPOSED_CHANGES_CHANGE_THREAD,
  PROPOSED_CHANGES_CHANGE_THREAD_OBJECT,
  PROPOSED_CHANGES_OBJECT,
  PROPOSED_CHANGES_THREAD_COMMENT_OBJECT,
} from "../../config/constants";
import { AuthContext } from "../../decorators/withAuth";
import graphqlClient from "../../graphql/graphqlClientApollo";
import { createObject } from "../../graphql/mutations/objects/createObject";
import { deleteObject } from "../../graphql/mutations/objects/deleteObject";
import { updateObjectWithId } from "../../graphql/mutations/objects/updateObjectWithId";
import { getProposedChangesThreads } from "../../graphql/queries/proposed-changes/getProposedChangesThreads";
import { branchVar } from "../../graphql/variables/branchVar";
import { dateVar } from "../../graphql/variables/dateVar";
import useQuery from "../../hooks/useQuery";
import { branchesState } from "../../state/atoms/branches.atom";
import { schemaState } from "../../state/atoms/schema.atom";
import { constructPath } from "../../utils/fetch";
import { stringifyWithoutQuotes } from "../../utils/string";
import { DynamicFieldData } from "../edit-form-hook/dynamic-control-types";
import ErrorScreen from "../error-screen/error-screen";
import LoadingScreen from "../loading-screen/loading-screen";
import ObjectItemEditComponent from "../object-item-edit/object-item-edit-paginated";

type tProposedChangesDetails = {
  proposedChangesDetails?: any;
};

export const getFormStructure = (
  branches: any[] = [],
  reviewers: any[] = [],
  data?: any
): DynamicFieldData[] => [
  {
    name: "name.value",
    kind: "Text",
    type: "text",
    label: "Name",
    value: data?.name?.value ?? "",
    options: { values: [] },
    config: {},
    isProtected: false,
  },
  {
    name: "source_branch.value",
    kind: "String",
    type: "select",
    label: "Source Branch",
    value: data?.source_branch?.value ?? "",
    options: { values: branches },
    config: {},
    isProtected: !!data?.source_branch?.value,
  },
  {
    name: "destination_branch.value",
    kind: "Text",
    type: "text",
    label: "Destination Branch",
    value: "main",
    options: { values: [] },
    config: {},
    isProtected: true,
  },
  {
    name: "reviewers.list",
    kind: "String",
    type: "multiselect",
    label: "Reviewers",
    value: data?.reviewers?.edges.map((edge: any) => edge?.node?.id).filter(Boolean) ?? "",
    options: {
      values: reviewers,
    },
    config: {},
    isProtected: false,
  },
];

export const Conversations = (props: tProposedChangesDetails) => {
  const { proposedChangesDetails } = props;

  const { proposedchange } = useParams();
  const [branches] = useAtom(branchesState);
  const [schemaList] = useAtom(schemaState);
  const branch = useReactiveVar(branchVar);
  const date = useReactiveVar(dateVar);
  const auth = useContext(AuthContext);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingApprove, setIsLoadingApprove] = useState(false);
  // const [isLoadingMerge, setIsLoadingMerge] = useState(false);
  const [showEditDrawer, setShowEditDrawer] = useState(false);
  const navigate = useNavigate();

  const schemaData = schemaList.filter((s) => s.name === PROPOSED_CHANGES_CHANGE_THREAD)[0];
  const accountSchemaData = schemaList.filter((s) => s.name === ACCOUNT_OBJECT)[0];

  const queryString = schemaData
    ? getProposedChangesThreads({
        id: proposedchange,
        kind: schemaData.kind,
        accountKind: accountSchemaData.kind,
      })
    : // Empty query to make the gql parsing work
      // TODO: Find another solution for queries while loading schemaData
      "query { ok }";

  const query = gql`
    ${queryString}
  `;

  const { loading, error, data, refetch } = useQuery(query, { skip: !schemaData });

  if (!schemaData || loading) {
    return <LoadingScreen />;
  }

  if (error) {
    return <ErrorScreen />;
  }

  const threads = data ? data[schemaData.kind]?.edges?.map((edge: any) => edge.node) : [];
  const reviewers = proposedChangesDetails?.reviewers?.edges.map((edge: any) => edge.node) ?? [];
  const approvers = proposedChangesDetails?.approved_by?.edges.map((edge: any) => edge.node) ?? [];
  const approverId = auth?.data?.sub;
  const canApprove = !approvers?.map((a: any) => a.id).includes(approverId);
  const path = constructPath("/proposed-changes");

  const handleSubmit = async (data: any, event: any) => {
    let threadId;

    try {
      event.target.reset();

      if (!data || !approverId) {
        return;
      }

      const newDate = formatISO(new Date());

      const newThread = {
        change: {
          id: proposedchange,
        },
        created_at: {
          value: newDate,
        },
        resolved: {
          value: false,
        },
      };

      const threadMutationString = createObject({
        kind: PROPOSED_CHANGES_CHANGE_THREAD_OBJECT,
        data: stringifyWithoutQuotes(newThread),
      });

      const threadMutation = gql`
        ${threadMutationString}
      `;

      const result = await graphqlClient.mutate({
        mutation: threadMutation,
        context: {
          branch: branch?.name,
          date,
        },
      });

      threadId = result?.data[`${PROPOSED_CHANGES_CHANGE_THREAD_OBJECT}Create`]?.object?.id;

      const newComment = {
        text: {
          value: data.comment,
        },
        created_by: {
          id: approverId,
        },
        created_at: {
          value: newDate,
        },
        thread: {
          id: threadId,
        },
      };

      const mutationString = createObject({
        kind: PROPOSED_CHANGES_THREAD_COMMENT_OBJECT,
        data: stringifyWithoutQuotes(newComment),
      });

      const mutation = gql`
        ${mutationString}
      `;

      await graphqlClient.mutate({
        mutation,
        context: {
          branch: branch?.name,
          date,
        },
      });

      toast(<Alert type={ALERT_TYPES.SUCCESS} message={"Comment added"} />);

      refetch();

      setIsLoading(false);
    } catch (error: any) {
      if (threadId) {
        const mutationString = deleteObject({
          name: PROPOSED_CHANGES_CHANGE_THREAD_OBJECT,
          data: stringifyWithoutQuotes({
            id: threadId,
          }),
        });

        const mutation = gql`
          ${mutationString}
        `;

        await graphqlClient.mutate({
          mutation,
          context: { branch: branch?.name, date },
        });
        return;
      }

      console.error("An error occured while creating the comment: ", error);

      toast(
        <Alert
          type={ALERT_TYPES.ERROR}
          message={"An error occured while creating the comment"}
          details={error.message}
        />
      );

      setIsLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!approverId) {
      return;
    }

    setIsLoadingApprove(true);

    const oldApproversId = approvers.map((a: any) => a.id);
    const newApproverId = approverId;
    const newApproversId = Array.from(new Set([...oldApproversId, newApproverId]));
    const newApprovers = newApproversId.map((id: string) => ({ id }));

    const data = {
      approved_by: newApprovers,
    };

    try {
      const mutationString = updateObjectWithId({
        kind: schemaData.kind,
        data: stringifyWithoutQuotes({
          id: proposedchange,
          ...data,
        }),
      });

      const mutation = gql`
        ${mutationString}
      `;

      await graphqlClient.mutate({
        mutation,
        context: { branch: branch?.name, date },
      });

      toast(<Alert type={ALERT_TYPES.SUCCESS} message="Proposed change approved" />);

      refetch();

      setIsLoadingApprove(false);

      return;
    } catch (e) {
      setIsLoading(false);
      toast(
        <Alert message="Something went wrong while updating the object" type={ALERT_TYPES.ERROR} />
      );
      console.error("Something went wrong while updating the object:", e);
      return;
    }
  };

  // const handleMerge = async () => {
  //   if (!proposedChangesDetails?.source_branch?.value) return;

  //   try {
  //     setIsLoadingMerge(true);

  //     const data = {
  //       name: proposedChangesDetails?.source_branch?.value,
  //     };

  //     const mutationString = mergeBranch({ data: objectToString(data) });

  //     const mutation = gql`
  //       ${mutationString}
  //     `;

  //     await graphqlClient.mutate({
  //       mutation,
  //       context: {
  //         date,
  //       },
  //     });

  //     toast(<Alert type={ALERT_TYPES.SUCCESS} message={"Branch merged successfuly!"} />);
  //   } catch (error: any) {
  //     console.log("error: ", error);

  //     toast(
  //       <Alert type={ALERT_TYPES.SUCCESS} message={"An error occured while merging the branch"} />
  //     );
  //   }

  //   setIsLoadingMerge(false);
  // };

  const branchesOptions: any[] = branches
    .filter((branch) => branch.name !== "main")
    .map((branch) => ({ id: branch.name, name: branch.name }));

  const reviewersOptions: any[] = data
    ? data[accountSchemaData.kind]?.edges.map((edge: any) => ({
        id: edge?.node.id,
        name: edge?.node?.display_label,
      }))
    : [];

  const formStructure = getFormStructure(branchesOptions, reviewersOptions, proposedChangesDetails);

  return (
    <div className="flex">
      <div className="flex-1 p-4 overflow-auto">
        <div>
          {threads.map((item: any, index: number) => (
            <Thread key={index} thread={item} refetch={refetch} />
          ))}
        </div>

        <div>
          <AddComment
            onSubmit={handleSubmit}
            isLoading={isLoading}
            disabled={!auth?.permissions?.write}
          />
        </div>
      </div>

      <div className="flex-3">
        <div className="bg-custom-white flex flex-col justify-start rounded-bl-lg">
          <div className="py-4 px-4">
            <div className="flex items-center">
              <div className="flex flex-1">
                <div
                  onClick={() => navigate(path)}
                  className="text-base font-semibold leading-6 text-gray-900 cursor-pointer hover:underline">
                  Proposed changes
                </div>
              </div>

              <div className="">
                <Button
                  disabled={!auth?.permissions?.write}
                  onClick={() => setShowEditDrawer(true)}
                  className="mr-4">
                  Edit
                  <PencilIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </div>
          </div>

          <div className="border-t border-gray-200 px-2 py-2 sm:p-0">
            <dl className="divide-y divide-gray-200">
              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">ID</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">{proposedchange}</dd>
              </div>

              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">Name</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">
                  {proposedChangesDetails?.name.value}
                </dd>
              </div>

              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">Source branch</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">
                  <Badge>{proposedChangesDetails?.source_branch.value}</Badge>
                </dd>
              </div>

              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">Destination branch</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">
                  <Badge>{proposedChangesDetails?.destination_branch.value}</Badge>
                </dd>
              </div>

              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">Created by</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">
                  <Tooltip message={proposedChangesDetails?.created_by?.node?.display_label}>
                    <Avatar
                      size={AVATAR_SIZE.SMALL}
                      name={proposedChangesDetails?.created_by?.node?.display_label}
                      className="mr-2 bg-custom-blue-green"
                    />
                  </Tooltip>
                </dd>
              </div>

              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">Reviewers</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">
                  {reviewers.map((reviewer: any, index: number) => (
                    <Tooltip key={index} message={reviewer.display_label}>
                      <Avatar
                        size={AVATAR_SIZE.SMALL}
                        name={reviewer.display_label}
                        className="mr-2"
                      />
                    </Tooltip>
                  ))}
                </dd>
              </div>

              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">Approved by</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">
                  {approvers.map((approver: any, index: number) => (
                    <Tooltip key={index} message={approver.display_label}>
                      <Avatar
                        size={AVATAR_SIZE.SMALL}
                        name={approver.display_label}
                        className="mr-2"
                      />
                    </Tooltip>
                  ))}
                </dd>
              </div>

              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">Updated</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">
                  <DateDisplay date={proposedChangesDetails?._updated_at} />
                </dd>
              </div>

              <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6 items-center">
                <dt className="text-sm font-medium text-gray-500">Actions</dt>
                <dd className="flex mt-1 text-gray-900 sm:col-span-2 sm:mt-0">
                  <Button
                    onClick={handleApprove}
                    // buttonType={BUTTON_TYPES.VALIDATE}
                    isLoading={isLoadingApprove}
                    disabled={!auth?.permissions?.write || !approverId || !canApprove}
                    className="mr-2">
                    Approve
                  </Button>

                  {/* <Button
                    onClick={handleMerge}
                    buttonType={BUTTON_TYPES.VALIDATE}
                    isLoading={isLoadingMerge}
                    disabled={!auth?.permissions?.write}>
                    Merge
                  </Button> */}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      <SlideOver
        title={
          <div className="space-y-2">
            <div className="flex items-center w-full">
              <span className="text-lg font-semibold mr-3">
                {proposedChangesDetails?.display_label}
              </span>
              <div className="flex-1"></div>
              <div className="flex items-center">
                <Square3Stack3DIcon className="w-5 h-5" />
                <div className="ml-1.5 pb-1">{branch?.name ?? DEFAULT_BRANCH_NAME}</div>
              </div>
            </div>
            <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20">
              <svg
                className="h-1.5 w-1.5 mr-1 fill-yellow-500"
                viewBox="0 0 6 6"
                aria-hidden="true">
                <circle cx={3} cy={3} r={3} />
              </svg>
              {schemaData.kind}
            </span>
            <div className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-custom-blue-500 ring-1 ring-inset ring-custom-blue-500/10 ml-3">
              <svg
                className="h-1.5 w-1.5 mr-1 fill-custom-blue-500"
                viewBox="0 0 6 6"
                aria-hidden="true">
                <circle cx={3} cy={3} r={3} />
              </svg>
              ID: {proposedChangesDetails?.id}
            </div>
          </div>
        }
        open={showEditDrawer}
        setOpen={setShowEditDrawer}>
        <ObjectItemEditComponent
          closeDrawer={() => setShowEditDrawer(false)}
          onUpdateComplete={() => refetch()}
          objectid={proposedchange!}
          objectname={PROPOSED_CHANGES_OBJECT!}
          formStructure={formStructure}
        />
      </SlideOver>
    </div>
  );
};
