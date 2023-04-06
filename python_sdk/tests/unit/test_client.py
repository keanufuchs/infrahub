import inspect

import pytest
from pytest_httpx import HTTPXMock

from infrahub_client import InfrahubClient, InfrahubClientSync
from infrahub_client.data import RepositoryData
from infrahub_client.exceptions import FilterNotFound, NodeNotFound
from infrahub_client.node import InfrahubNode, InfrahubNodeSync

async_client_methods = [method for method in dir(InfrahubClient) if not method.startswith("_")]
sync_client_methods = [method for method in dir(InfrahubClientSync) if not method.startswith("_")]

client_types = ["standard", "sync"]


def replace_async_return_annotation(annotation: str) -> str:
    """Allows for comparison between sync and async return annotations."""
    replacements = {
        "InfrahubClient": "InfrahubClientSync",
        "InfrahubNode": "InfrahubNodeSync",
        "List[InfrahubNode]": "List[InfrahubNodeSync]",
    }
    return replacements.get(annotation) or annotation


def replace_sync_return_annotation(annotation: str) -> str:
    """Allows for comparison between sync and async return annotations."""
    replacements = {
        "InfrahubClientSync": "InfrahubClient",
        "InfrahubNodeSync": "InfrahubNode",
        "List[InfrahubNodeSync]": "List[InfrahubNode]",
    }
    return replacements.get(annotation) or annotation


async def test_method_sanity():
    """Validate that there is at least one public method and that both clients look the same."""
    assert async_client_methods
    assert async_client_methods == sync_client_methods


@pytest.mark.parametrize("method", async_client_methods)
async def test_validate_method_signature(method):
    async_method = getattr(InfrahubClient, method)
    sync_method = getattr(InfrahubClientSync, method)
    async_sig = inspect.signature(async_method)
    sync_sig = inspect.signature(sync_method)
    assert async_sig.parameters == sync_sig.parameters
    assert async_sig.return_annotation == replace_sync_return_annotation(sync_sig.return_annotation)
    assert replace_async_return_annotation(async_sig.return_annotation) == sync_sig.return_annotation


async def test_init_client():
    await InfrahubClient.init()

    assert True


async def test_init_client_sync():
    InfrahubClientSync.init()

    assert True


async def test_get_repositories(mock_branches_list_query, mock_repositories_query):  # pylint: disable=unused-argument
    client = await InfrahubClient.init(address="http://mock", insert_tracker=True)
    repos = await client.get_list_repositories()

    expected_response = RepositoryData(
        id="9486cfce-87db-479d-ad73-07d80ba96a0f",
        name="infrahub-demo-edge",
        location="git@github.com:dgarros/infrahub-demo-edge.git",
        branches={"cr1234": "bbbbbbbbbbbbbbbbbbbb", "main": "aaaaaaaaaaaaaaaaaaaa"},
    )
    assert len(repos) == 1
    assert repos["infrahub-demo-edge"] == expected_response


@pytest.mark.parametrize("client_type", client_types)
async def test_method_all(clients, mock_query_repository_all_01, client_type):  # pylint: disable=unused-argument
    if client_type == "standard":
        repos = await clients.standard.all(kind="Repository")
    else:
        repos = clients.sync.all(kind="Repository")
    assert len(repos) == 2


@pytest.mark.parametrize("client_type", client_types)
async def test_method_get_by_id(
    httpx_mock: HTTPXMock, clients, mock_schema_query_01, client_type
):  # pylint: disable=unused-argument
    response = {
        "data": {
            "repository": [
                {
                    "id": "bfae43e8-5ebb-456c-a946-bf64e930710a",
                    "name": {"value": "infrahub-demo-core"},
                    "location": {"value": "git@github.com:opsmill/infrahub-demo-core.git"},
                    "commit": {"value": "bbbbbbbbbbbbbbbbbbbb"},
                }
            ]
        }
    }

    httpx_mock.add_response(method="POST", json=response, match_headers={"X-Infrahub-Tracker": "query-repository-get"})

    if client_type == "standard":
        repo = await clients.standard.get(kind="Repository", id="bfae43e8-5ebb-456c-a946-bf64e930710a")
        assert isinstance(repo, InfrahubNode)
    else:
        repo = clients.sync.get(kind="Repository", id="bfae43e8-5ebb-456c-a946-bf64e930710a")
        assert isinstance(repo, InfrahubNodeSync)
    assert repo.id == "bfae43e8-5ebb-456c-a946-bf64e930710a"


@pytest.mark.parametrize("client_type", client_types)
async def test_method_get_by_name(
    httpx_mock: HTTPXMock, clients, mock_schema_query_01, client_type
):  # pylint: disable=unused-argument
    response = {
        "data": {
            "repository": [
                {
                    "id": "bfae43e8-5ebb-456c-a946-bf64e930710a",
                    "name": {"value": "infrahub-demo-core"},
                    "location": {"value": "git@github.com:opsmill/infrahub-demo-core.git"},
                    "commit": {"value": "bbbbbbbbbbbbbbbbbbbb"},
                }
            ]
        }
    }

    httpx_mock.add_response(method="POST", json=response, match_headers={"X-Infrahub-Tracker": "query-repository-get"})

    if client_type == "standard":
        repo = await clients.standard.get(kind="Repository", name__value="infrahub-demo-core")
        assert isinstance(repo, InfrahubNode)
    else:
        repo = clients.sync.get(kind="Repository", name__value="infrahub-demo-core")
        assert isinstance(repo, InfrahubNodeSync)
    assert repo.id == "bfae43e8-5ebb-456c-a946-bf64e930710a"


@pytest.mark.parametrize("client_type", client_types)
async def test_method_get_not_found(
    httpx_mock: HTTPXMock, clients, mock_schema_query_01, client_type
):  # pylint: disable=unused-argument
    response: dict = {"data": {"repository": []}}
    httpx_mock.add_response(method="POST", json=response, match_headers={"X-Infrahub-Tracker": "query-repository-get"})

    with pytest.raises(NodeNotFound):
        if client_type == "standard":
            await clients.standard.get(kind="Repository", name__value="infrahub-demo-core")
        else:
            clients.sync.get(kind="Repository", name__value="infrahub-demo-core")


@pytest.mark.parametrize("client_type", client_types)
async def test_method_get_found_many(
    httpx_mock: HTTPXMock, clients, mock_schema_query_01, client_type
):  # pylint: disable=unused-argument
    response: dict = {
        "data": {
            "repository": [
                {
                    "id": "bfae43e8-5ebb-456c-a946-bf64e930710a",
                    "name": {"value": "infrahub-demo-core"},
                    "location": {"value": "git@github.com:opsmill/infrahub-demo-core.git"},
                    "commit": {"value": "bbbbbbbbbbbbbbbbbbbb"},
                },
                {
                    "id": "9486cfce-87db-479d-ad73-07d80ba96a0f",
                    "name": {"value": "infrahub-demo-edge"},
                    "location": {"value": "git@github.com:opsmill/infrahub-demo-edge.git"},
                    "commit": {"value": "aaaaaaaaaaaaaaaaaaaa"},
                },
            ]
        }
    }

    httpx_mock.add_response(method="POST", json=response, match_headers={"X-Infrahub-Tracker": "query-repository-get"})

    with pytest.raises(IndexError):
        if client_type == "standard":
            await clients.standard.get(kind="Repository", id="bfae43e8-5ebb-456c-a946-bf64e930710a")
        else:
            clients.sync.get(kind="Repository", id="bfae43e8-5ebb-456c-a946-bf64e930710a")


@pytest.mark.parametrize("client_type", client_types)
async def test_method_get_invalid_filter(
    httpx_mock: HTTPXMock, clients, mock_schema_query_01, client_type
):  # pylint: disable=unused-argument
    with pytest.raises(FilterNotFound):
        if client_type == "standard":
            await clients.standard.get(kind="Repository", name__name="infrahub-demo-core")
        else:
            clients.sync.get(kind="Repository", name__name="infrahub-demo-core")


@pytest.mark.parametrize("client_type", client_types)
async def test_method_filters_many(
    httpx_mock: HTTPXMock, clients, mock_schema_query_01, client_type
):  # pylint: disable=unused-argument
    response = {
        "data": {
            "repository": [
                {
                    "id": "bfae43e8-5ebb-456c-a946-bf64e930710a",
                    "name": {"value": "infrahub-demo-core"},
                    "location": {"value": "git@github.com:opsmill/infrahub-demo-core.git"},
                    "commit": {"value": "bbbbbbbbbbbbbbbbbbbb"},
                },
                {
                    "id": "9486cfce-87db-479d-ad73-07d80ba96a0f",
                    "name": {"value": "infrahub-demo-edge"},
                    "location": {"value": "git@github.com:opsmill/infrahub-demo-edge.git"},
                    "commit": {"value": "aaaaaaaaaaaaaaaaaaaa"},
                },
            ]
        }
    }

    httpx_mock.add_response(
        method="POST", json=response, match_headers={"X-Infrahub-Tracker": "query-repository-filters"}
    )

    if client_type == "standard":
        repos = await clients.standard.filters(
            kind="Repository", ids=["bfae43e8-5ebb-456c-a946-bf64e930710a", "9486cfce-87db-479d-ad73-07d80ba96a0f"]
        )
    else:
        repos = clients.sync.filters(
            kind="Repository", ids=["bfae43e8-5ebb-456c-a946-bf64e930710a", "9486cfce-87db-479d-ad73-07d80ba96a0f"]
        )
    assert len(repos) == 2


@pytest.mark.parametrize("client_type", client_types)
async def test_method_filters_empty(
    httpx_mock: HTTPXMock, clients, mock_schema_query_01, client_type
):  # pylint: disable=unused-argument
    response: dict = {"data": {"repository": []}}
    httpx_mock.add_response(
        method="POST", json=response, match_headers={"X-Infrahub-Tracker": "query-repository-filters"}
    )

    if client_type == "standard":
        repos = await clients.standard.filters(
            kind="Repository", ids=["bfae43e8-5ebb-456c-a946-bf64e930710a", "9486cfce-87db-479d-ad73-07d80ba96a0f"]
        )
    else:
        repos = clients.sync.filters(
            kind="Repository", ids=["bfae43e8-5ebb-456c-a946-bf64e930710a", "9486cfce-87db-479d-ad73-07d80ba96a0f"]
        )
    assert len(repos) == 0
