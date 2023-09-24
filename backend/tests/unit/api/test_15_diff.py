import pytest
from deepdiff import DeepDiff

from infrahub.api.diff import get_display_labels, get_display_labels_per_kind
from infrahub.core.initialization import create_branch
from infrahub.core.manager import NodeManager
from infrahub.core.node import Node
from infrahub.database import InfrahubDatabase
from infrahub.message_bus.rpc import InfrahubRpcClientTesting


@pytest.fixture
def patch_rpc_client():
    import infrahub.message_bus.rpc

    infrahub.message_bus.rpc.InfrahubRpcClient = InfrahubRpcClientTesting


async def test_get_display_labels_per_kind(db: InfrahubDatabase, default_branch, car_person_data):
    persons_list = await NodeManager.query(db=db, schema="TestPerson", branch=default_branch)
    person_ids = [item.id for item in persons_list]
    display_labels = await get_display_labels_per_kind(
        kind="TestPerson", ids=person_ids, branch_name=default_branch.name, db=db
    )
    assert len(display_labels) == len(person_ids)


async def test_get_display_labels_per_kind_with_branch(db: InfrahubDatabase, default_branch, car_person_data):
    branch2 = await create_branch(branch_name="branch2", db=db)

    # Add a new Person
    p3 = await Node.init(db=db, schema="TestPerson", branch=branch2)
    await p3.new(db=db, name="Bill", height=160)
    await p3.save(db=db)

    persons_list = await NodeManager.query(db=db, schema="TestPerson", branch=branch2)
    person_ids = [item.id for item in persons_list]

    display_labels = await get_display_labels_per_kind(
        kind="TestPerson", ids=person_ids, branch_name=branch2.name, db=db
    )
    assert len(display_labels) == len(person_ids)


async def test_get_display_labels(db: InfrahubDatabase, default_branch, car_person_data):
    persons_list = await NodeManager.query(db=db, schema="TestPerson", branch=default_branch)
    person_ids = [item.id for item in persons_list]
    cars_list = await NodeManager.query(db=db, schema="TestCar", branch=default_branch)
    car_ids = [item.id for item in cars_list]

    display_labels = await get_display_labels(nodes={"main": {"TestPerson": person_ids, "TestCar": car_ids}}, db=db)
    assert len(display_labels["main"]) == len(car_ids) + len(person_ids)


async def test_get_display_labels_with_branch(db: InfrahubDatabase, default_branch, car_person_data):
    branch2 = await create_branch(branch_name="branch2", db=db)

    persons_list = await NodeManager.query(db=db, schema="TestPerson", branch=branch2)
    persons = {item.name.value: item for item in persons_list}

    repos_list = await NodeManager.query(db=db, schema="CoreRepository", branch=branch2)
    repos = {item.name.value: item for item in repos_list}

    cars_list = await NodeManager.query(db=db, schema="TestCar", branch=branch2)
    cars = {item.name.value: item for item in cars_list}

    # Add a new Person
    p3 = await Node.init(db=db, schema="TestPerson", branch=branch2)
    await p3.new(db=db, name="Bill", height=160)
    await p3.save(db=db)
    persons["Bill"] = p3

    await cars["volt"].owner.update(data=p3, db=db)
    await cars["volt"].save(db=db)

    repo01 = repos["repo01"]
    repo01.commit.value = "dddddddddd"
    await repo01.save(db=db)

    # Update P1 height in main
    p1 = await NodeManager.get_one(id=persons["John"].id, db=db)
    p1.height.value = 120
    await p1.save(db=db)

    persons_list = await NodeManager.query(db=db, schema="TestPerson", branch=branch2)
    person_ids = [item.id for item in persons_list]
    cars_list = await NodeManager.query(db=db, schema="TestCar", branch=branch2)
    car_ids = [item.id for item in cars_list]

    display_labels = await get_display_labels(
        nodes={branch2.name: {"TestPerson": person_ids, "TestCar": car_ids}}, db=db
    )
    assert len(display_labels["branch2"]) == len(car_ids) + len(person_ids)


# ----------------------------------------------------------------------
# New API
# ----------------------------------------------------------------------


@pytest.fixture
async def r1_update_01(data_diff_attribute):
    r1 = data_diff_attribute["r1"]

    expected_response = {
        "kind": "CoreRepository",
        "id": r1,
        "path": f"data/{r1}",
        "elements": {
            "description": {
                "type": "Attribute",
                "name": "description",
                "path": f"data/{r1}/description",
                "change": {
                    "type": "Attribute",
                    "branches": ["branch2"],
                    "id": "3dfe50e7-9dfb-490c-8c26-858a7c66b797",
                    "summary": {"added": 0, "removed": 0, "updated": 1},
                    "action": "updated",
                    "value": {
                        "path": f"data/{r1}/description/value",
                        "changes": [
                            {
                                "branch": "branch2",
                                "type": "HAS_VALUE",
                                "changed_at": "2023-08-01T11:07:25.255688Z",
                                "action": "updated",
                                "value": {"new": "Second update in Branch", "previous": "NULL"},
                            }
                        ],
                    },
                    "properties": {},
                },
            }
        },
        "summary": {"added": 0, "removed": 0, "updated": 1},
        "action": {"branch2": "updated"},
        "display_label": {"branch2": "repo01"},
    }
    return expected_response


async def test_diff_data_attribute_branch_only_default(
    db: InfrahubDatabase, client, client_headers, data_diff_attribute, r1_update_01
):
    with client:
        response = client.get(
            "/api/diff/data-new?branch=branch2&branch_only=true",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()

    assert len(data["diffs"]) == 1

    paths_to_exclude = [
        r"root\['elements'\]\['description'\]\['change'\]\['id'\]",
        r"root\['elements'\]\['description'\]\['change'\]\['value'\]\['changes'\]\[0\]\['changed_at'\]",
    ]

    assert (
        DeepDiff(r1_update_01, data["diffs"][0], exclude_regex_paths=paths_to_exclude, ignore_order=True).to_dict()
        == {}
    )


async def test_diff_data_attribute_all_branches(
    db: InfrahubDatabase, client, client_headers, data_diff_attribute, r1_update_01
):
    p1 = data_diff_attribute["p1"]
    c2 = data_diff_attribute["c2"]

    with client:
        response = client.get(
            "/api/diff/data-new?branch=branch2&branch_only=false",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()

    assert len(data["diffs"]) == 3

    expected_p1_update = {
        "kind": "TestPerson",
        "id": p1,
        "path": f"data/{p1}",
        "elements": {
            "height": {
                "type": "Attribute",
                "name": "height",
                "path": f"data/{p1}/height",
                "change": {
                    "type": "Attribute",
                    "branches": ["main"],
                    "id": "e5fba80e-e525-4e8d-81eb-820530b7ea8a",
                    "summary": {"added": 0, "removed": 0, "updated": 1},
                    "action": "updated",
                    "value": {
                        "path": f"data/{p1}/height/value",
                        "changes": [
                            {
                                "branch": "main",
                                "type": "HAS_VALUE",
                                "changed_at": "2023-08-01T11:15:13.765374Z",
                                "action": "updated",
                                "value": {"new": 120, "previous": 180},
                            }
                        ],
                    },
                    "properties": {},
                },
            }
        },
        "summary": {"added": 0, "removed": 0, "updated": 1},
        "action": {"main": "updated"},
        "display_label": {"main": "John"},
    }

    expected_c2_update = {
        "kind": "TestElectricCar",
        "id": c2,
        "path": f"data/{c2}",
        "elements": {
            "nbr_seats": {
                "type": "Attribute",
                "name": "nbr_seats",
                "path": f"data/{c2}/nbr_seats",
                "change": {
                    "type": "Attribute",
                    "branches": ["main"],
                    "id": "1654ddf7-bbea-40cd-930c-28d02d7b247a",
                    "summary": {"added": 0, "removed": 0, "updated": 1},
                    "action": "updated",
                    "value": {
                        "path": f"data/{c2}/nbr_seats/value",
                        "changes": [
                            {
                                "branch": "main",
                                "type": "HAS_VALUE",
                                "changed_at": "2023-08-01T11:15:13.874966Z",
                                "action": "updated",
                                "value": {"new": 4, "previous": 2},
                            }
                        ],
                    },
                    "properties": {},
                },
            }
        },
        "summary": {"added": 0, "removed": 0, "updated": 1},
        "action": {"main": "updated"},
        "display_label": {"main": "bolt #444444"},
    }

    paths_to_exclude = [
        r"root\[\d\]\['elements'\]\['\w+'\]\['change'\]\['id'\]",
        r"root\[\d\]\['elements'\]\['\w+'\]\['change'\]\['value'\]\['changes'\]\[0\]\['changed_at'\]",
    ]
    expected_response = [r1_update_01, expected_p1_update, expected_c2_update]

    assert (
        DeepDiff(expected_response, data["diffs"], exclude_regex_paths=paths_to_exclude, ignore_order=True).to_dict()
        == {}
    )


async def test_diff_data_attribute_conflict(db: InfrahubDatabase, client, client_headers, data_conflict_attribute):
    p1 = data_conflict_attribute["p1"]
    r1 = data_conflict_attribute["r1"]

    with client:
        response = client.get(
            "/api/diff/data-new?branch=branch2&branch_only=false",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()

    expected_response = [
        {
            "action": {
                "branch2": "updated",
                "main": "updated",
            },
            "display_label": {
                "branch2": "John",
                "main": "John",
            },
            "elements": {
                "height": {
                    "change": {
                        "action": "updated",
                        "branches": ["branch2", "main"],
                        "id": "2d697aa0-fbc7-4430-9ca8-3e2303612c67",
                        "properties": {},
                        "summary": {"added": 0, "removed": 0, "updated": 2},
                        "type": "Attribute",
                        "value": {
                            "changes": [
                                {
                                    "action": "updated",
                                    "branch": "branch2",
                                    "changed_at": "2023-08-03T04:51:30.023988Z",
                                    "type": "HAS_VALUE",
                                    "value": {"new": 666, "previous": 180},
                                },
                                {
                                    "action": "updated",
                                    "branch": "main",
                                    "changed_at": "2023-08-03T04:51:30.023988Z",
                                    "type": "HAS_VALUE",
                                    "value": {"new": 120, "previous": 180},
                                },
                            ],
                            "path": f"data/{p1}/height/value",
                        },
                    },
                    "name": "height",
                    "path": f"data/{p1}/height",
                    "type": "Attribute",
                },
            },
            "id": p1,
            "kind": "TestPerson",
            "path": f"data/{p1}",
            "summary": {"added": 0, "removed": 0, "updated": 2},
        },
        {
            "action": {
                "branch2": "updated",
                "main": "updated",
            },
            "display_label": {
                "branch2": "repo01",
                "main": "repo01",
            },
            "elements": {
                "description": {
                    "change": {
                        "action": "updated",
                        "branches": ["branch2", "main"],
                        "id": "eb98ef7c-3c6e-4a0a-85a2-d61065ce9c2c",
                        "properties": {},
                        "summary": {"added": 0, "removed": 0, "updated": 2},
                        "type": "Attribute",
                        "value": {
                            "changes": [
                                {
                                    "action": "updated",
                                    "branch": "branch2",
                                    "changed_at": "2023-08-03T04:51:30.074662Z",
                                    "type": "HAS_VALUE",
                                    "value": {
                                        "new": "Second update in Branch",
                                        "previous": "NULL",
                                    },
                                },
                                {
                                    "action": "updated",
                                    "branch": "main",
                                    "changed_at": "2023-08-03T04:51:29.959427Z",
                                    "type": "HAS_VALUE",
                                    "value": {"new": "update in main", "previous": "NULL"},
                                },
                            ],
                            "path": f"data/{r1}/description/value",
                        },
                    },
                    "name": "description",
                    "path": f"data/{r1}/description",
                    "type": "Attribute",
                },
            },
            "id": r1,
            "kind": "CoreRepository",
            "path": f"data/{r1}",
            "summary": {"added": 0, "removed": 0, "updated": 2},
        },
    ]

    paths_to_exclude = [
        r"root\[\d\]\['elements'\]\['\w+'\]\['change'\]\['id'\]",
        r"root\[\d\]\['elements'\]\['\w+'\]\['change'\]\['value'\]\['changes'\]\[\d\]\['changed_at'\]",
    ]

    assert (
        DeepDiff(expected_response, data["diffs"], exclude_regex_paths=paths_to_exclude, ignore_order=True).to_dict()
        == {}
    )


async def test_diff_data_relationship_one(db: InfrahubDatabase, client, client_headers, data_diff_relationship_one):
    john_id = data_diff_relationship_one["p1"]
    jane_id = data_diff_relationship_one["p2"]

    c1 = data_diff_relationship_one["c1"]
    c2 = data_diff_relationship_one["c2"]

    with client:
        response = client.get(
            "/api/diff/data-new?branch=branch2&branch_only=true",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()

    expected_c1 = {
        "kind": "TestElectricCar",
        "id": c1,
        "path": f"data/{c1}",
        "elements": {
            "previous_owner": {
                "type": "RelationshipOne",
                "name": "previous_owner",
                "path": f"data/{c1}/previous_owner",
                "change": {
                    "type": "RelationshipOne",
                    "id": "e4ba6625-812f-46ee-8344-167e0142c4bf",
                    "identifier": "person_previous__car",
                    "branches": ["branch2"],
                    "summary": {"added": 2, "removed": 0, "updated": 0},
                    "peer": {
                        "path": f"data/{c1}/previous_owner/peer",
                        "changes": [
                            {
                                "branch": "branch2",
                                "new": {"id": john_id, "kind": "TestPerson", "display_label": "John"},
                                "previous": {"id": jane_id, "kind": "TestPerson", "display_label": "Jane"},
                            }
                        ],
                    },
                    "properties": {
                        "IS_PROTECTED": {
                            "path": f"data/{c1}/previous_owner/property/IS_PROTECTED",
                            "changes": [
                                {
                                    "branch": "branch2",
                                    "type": "IS_PROTECTED",
                                    "changed_at": "2023-08-21T11:06:49.688893Z",
                                    "action": "added",
                                    "value": {"new": False, "previous": None},
                                }
                            ],
                        },
                        "IS_VISIBLE": {
                            "path": f"data/{c1}/previous_owner/property/IS_VISIBLE",
                            "changes": [
                                {
                                    "branch": "branch2",
                                    "type": "IS_VISIBLE",
                                    "changed_at": "2023-08-21T11:06:49.688893Z",
                                    "action": "added",
                                    "value": {"new": True, "previous": None},
                                }
                            ],
                        },
                    },
                    "changed_at": None,
                    "action": {"branch2": "updated"},
                },
            }
        },
        "summary": {"added": 0, "removed": 0, "updated": 1},
        "action": {"branch2": "updated"},
        "display_label": {"branch2": "volt #444444"},
    }

    expected_c2 = {
        "kind": "TestElectricCar",
        "id": c2,
        "path": f"data/{c2}",
        "elements": {
            "previous_owner": {
                "type": "RelationshipOne",
                "name": "previous_owner",
                "path": f"data/{c2}/previous_owner",
                "change": {
                    "type": "RelationshipOne",
                    "id": "053724da-2484-42d3-a38e-99cccaead03c",
                    "identifier": "person_previous__car",
                    "branches": ["branch2"],
                    "summary": {"added": 2, "removed": 0, "updated": 0},
                    "peer": {
                        "path": f"data/{c2}/previous_owner/peer",
                        "changes": [
                            {
                                "branch": "branch2",
                                "new": {"id": jane_id, "kind": "TestPerson", "display_label": "Jane"},
                                "previous": None,
                            }
                        ],
                    },
                    "properties": {
                        "IS_PROTECTED": {
                            "path": f"data/{c2}/previous_owner/property/IS_PROTECTED",
                            "changes": [
                                {
                                    "branch": "branch2",
                                    "type": "IS_PROTECTED",
                                    "changed_at": "2023-08-21T11:06:49.738741Z",
                                    "action": "added",
                                    "value": {"new": False, "previous": None},
                                }
                            ],
                        },
                        "IS_VISIBLE": {
                            "path": f"data/{c2}/previous_owner/property/IS_VISIBLE",
                            "changes": [
                                {
                                    "branch": "branch2",
                                    "type": "IS_VISIBLE",
                                    "changed_at": "2023-08-21T11:06:49.738741Z",
                                    "action": "added",
                                    "value": {"new": True, "previous": None},
                                }
                            ],
                        },
                    },
                    "changed_at": None,
                    "action": {"branch2": "added"},
                },
            }
        },
        "summary": {"added": 1, "removed": 0, "updated": 0},
        "action": {"branch2": "updated"},
        "display_label": {"branch2": "bolt #444444"},
    }

    paths_to_exclude = [
        r"root\[\d\]\['elements'\]\['previous\_owner'\]\['change'\]\['id'\]",
        r"root\[\d\]\['elements'\]\['previous\_owner'\]\['change'\]\['properties'\]\['\w+'\]\['changes'\]\[\d\]\['changed_at'\]",
    ]
    expected_response = [expected_c1, expected_c2]

    assert (
        DeepDiff(expected_response, data["diffs"], exclude_regex_paths=paths_to_exclude, ignore_order=True).to_dict()
        == {}
    )


async def test_diff_data_relationship_one_conflict(
    db: InfrahubDatabase, client, client_headers, data_conflict_relationship_one
):
    john_id = data_conflict_relationship_one["p1"]
    jane_id = data_conflict_relationship_one["p2"]

    c1 = data_conflict_relationship_one["c1"]
    c2 = data_conflict_relationship_one["c2"]

    with client:
        response = client.get(
            "/api/diff/data-new?branch=branch2&branch_only=false",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()

    expected_c1_response = {
        "kind": "TestElectricCar",
        "id": c1,
        "path": f"data/{c1}",
        "elements": {
            "previous_owner": {
                "type": "RelationshipOne",
                "name": "previous_owner",
                "path": f"data/{c1}/previous_owner",
                "change": {
                    "type": "RelationshipOne",
                    "id": "0ed90bf9-9082-4ba2-82dc-df66084cd54d",
                    "identifier": "person_previous__car",
                    "branches": ["branch2", "main"],
                    "summary": {"added": 2, "removed": 2, "updated": 0},
                    "peer": {
                        "path": f"data/{c1}/previous_owner/peer",
                        "changes": [
                            {
                                "branch": "branch2",
                                "new": {"id": john_id, "kind": "TestPerson", "display_label": "John"},
                                "previous": {"id": jane_id, "kind": "TestPerson", "display_label": "Jane"},
                            },
                            {
                                "branch": "main",
                                "new": None,
                                "previous": {"id": jane_id, "kind": "TestPerson", "display_label": "Jane"},
                            },
                        ],
                    },
                    "properties": {
                        "IS_PROTECTED": {
                            "path": f"data/{c1}/previous_owner/property/IS_PROTECTED",
                            "changes": [
                                {
                                    "branch": "branch2",
                                    "type": "IS_PROTECTED",
                                    "changed_at": "2023-08-02T04:57:01.411706Z",
                                    "action": "added",
                                    "value": {"new": False, "previous": None},
                                },
                                {
                                    "branch": "main",
                                    "type": "IS_PROTECTED",
                                    "changed_at": "2023-08-24T15:52:25.585684Z",
                                    "action": "removed",
                                    "value": {"new": False, "previous": False},
                                },
                            ],
                        },
                        "IS_VISIBLE": {
                            "path": f"data/{c1}/previous_owner/property/IS_VISIBLE",
                            "changes": [
                                {
                                    "branch": "branch2",
                                    "type": "IS_VISIBLE",
                                    "changed_at": "2023-08-02T04:57:01.411706Z",
                                    "action": "added",
                                    "value": {"new": True, "previous": None},
                                },
                                {
                                    "branch": "main",
                                    "type": "IS_VISIBLE",
                                    "changed_at": "2023-08-24T15:52:25.585684Z",
                                    "action": "removed",
                                    "value": {"new": True, "previous": True},
                                },
                            ],
                        },
                    },
                    "changed_at": None,
                    "action": {"branch2": "updated", "main": "removed"},
                },
            }
        },
        "summary": {"added": 0, "removed": 0, "updated": 1},
        "action": {"branch2": "updated", "main": "updated"},
        "display_label": {"branch2": "volt #444444", "main": "volt #444444"},
    }

    extracted_c1_response = [diff for diff in data["diffs"] if diff["id"] == c1]
    assert len(extracted_c1_response) == 1
    c1_response = extracted_c1_response[0]
    paths_to_exclude = [
        r"root\['summary'\]",
        r"root\['elements'\]\['previous_owner'\]\['change'\]\['id'\]",
        r"root\['elements'\]\['previous_owner'\]\['change'\]\['properties'\]\['\w+'\]\['changes'\]\[\d\]\['changed_at'\]",
    ]

    assert (
        DeepDiff(
            expected_c1_response,
            c1_response,
            exclude_regex_paths=paths_to_exclude,
            ignore_order=True,
        ).to_dict()
        == {}
    )

    expected_c2_response = {
        "kind": "TestElectricCar",
        "id": c2,
        "path": f"data/{c2}",
        "elements": {
            "previous_owner": {
                "type": "RelationshipOne",
                "name": "previous_owner",
                "path": f"data/{c2}/previous_owner",
                "change": {
                    "type": "RelationshipOne",
                    "id": "c00dc4ba-f7f1-48f9-9832-eb65d92ce594",
                    "identifier": "person_previous__car",
                    "branches": ["branch2", "main"],
                    "summary": {"added": 4, "removed": 0, "updated": 0},
                    "peer": {
                        "path": f"data/{c2}/previous_owner/peer",
                        "changes": [
                            {
                                "branch": "branch2",
                                "new": {
                                    "id": jane_id,
                                    "kind": "TestPerson",
                                    "display_label": "Jane",
                                },
                                "previous": None,
                            },
                            {
                                "branch": "main",
                                "new": {
                                    "id": john_id,
                                    "kind": "TestPerson",
                                    "display_label": "John",
                                },
                                "previous": None,
                            },
                        ],
                    },
                    "properties": {
                        "IS_PROTECTED": {
                            "path": f"data/{c2}/previous_owner/property/IS_PROTECTED",
                            "changes": [
                                {
                                    "branch": "branch2",
                                    "type": "IS_PROTECTED",
                                    "changed_at": "2023-08-11T12:49:48.161676Z",
                                    "action": "added",
                                    "value": {"new": False, "previous": None},
                                },
                                {
                                    "branch": "main",
                                    "type": "IS_PROTECTED",
                                    "changed_at": "2023-08-24T04:26:09.671810Z",
                                    "action": "added",
                                    "value": {"new": False, "previous": None},
                                },
                            ],
                        },
                        "IS_VISIBLE": {
                            "path": f"data/{c2}/previous_owner/property/IS_VISIBLE",
                            "changes": [
                                {
                                    "branch": "branch2",
                                    "type": "IS_VISIBLE",
                                    "changed_at": "2023-08-11T12:49:48.161676Z",
                                    "action": "added",
                                    "value": {"new": True, "previous": None},
                                },
                                {
                                    "branch": "main",
                                    "type": "IS_VISIBLE",
                                    "changed_at": "2023-08-24T04:26:09.671810Z",
                                    "action": "added",
                                    "value": {"new": True, "previous": None},
                                },
                            ],
                        },
                    },
                    "changed_at": None,
                    "action": {"branch2": "added", "main": "added"},
                },
            }
        },
        "summary": {"added": 2, "removed": 0, "updated": 0},
        "action": {
            "branch2": "updated",
            "main": "updated",
        },
        "display_label": {
            "branch2": "bolt #444444",
            "main": "bolt #444444",
        },
    }
    extracted_c2_response = [diff for diff in data["diffs"] if diff["id"] == c2]
    assert len(extracted_c2_response) == 1
    c2_response = extracted_c2_response[0]
    paths_to_exclude = [
        r"root\['summary'\]",
        r"root\['elements'\]\['previous_owner'\]\['change'\]\['id'\]",
        r"root\['elements'\]\['previous_owner'\]\['change'\]\['properties'\]\['\w+'\]\['changes'\]\[\d\]\['changed_at'\]",
    ]
    assert (
        DeepDiff(
            expected_c2_response,
            c2_response,
            exclude_regex_paths=paths_to_exclude,
            ignore_order=True,
        ).to_dict()
        == {}
    )


async def test_diff_data_relationship_many(db: InfrahubDatabase, client, client_headers, data_diff_relationship_many):
    org1 = data_diff_relationship_many["org1"]
    org3 = data_diff_relationship_many["org3"]

    red = data_diff_relationship_many["red"]
    blue = data_diff_relationship_many["blue"]
    green = data_diff_relationship_many["green"]
    orange = data_diff_relationship_many["orange"]

    with client:
        response = client.get(
            "/api/diff/data-new?branch=branch2&branch_only=false",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()

    expected_org3 = {
        "kind": "CoreOrganization",
        "id": org3.id,
        "path": f"data/{org3.id}",
        "elements": {
            "tags": {
                "type": "RelationshipMany",
                "name": "tags",
                "path": f"data/{org3.id}/tags",
                "change": {
                    "type": "RelationshipMany",
                    "identifier": "builtintag__coreorganization",
                    "branches": ["branch2"],
                    "summary": {"added": 4, "removed": 0, "updated": 0},
                    "peers": {
                        red.id: {
                            "branches": ["branch2"],
                            "peer": {"id": red.id, "kind": "BuiltinTag", "display_label": "red"},
                            "path": f"data/{org3.id}/tags/{red.id}",
                            "properties": {
                                "IS_PROTECTED": {
                                    "path": f"data/{org3.id}/tags/{red.id}/property/IS_PROTECTED",
                                    "changes": [
                                        {
                                            "branch": "branch2",
                                            "type": "IS_PROTECTED",
                                            "changed_at": "2023-08-17T15:24:53.870291Z",
                                            "action": "added",
                                            "value": {"new": False, "previous": None},
                                        }
                                    ],
                                },
                                "IS_VISIBLE": {
                                    "path": f"data/{org3.id}/tags/{red.id}/property/IS_VISIBLE",
                                    "changes": [
                                        {
                                            "branch": "branch2",
                                            "type": "IS_VISIBLE",
                                            "changed_at": "2023-08-17T15:24:53.870291Z",
                                            "action": "added",
                                            "value": {"new": True, "previous": None},
                                        }
                                    ],
                                },
                            },
                            "changed_at": None,
                            "action": {"branch2": "added"},
                        },
                        orange.id: {
                            "branches": ["branch2"],
                            "peer": {"id": orange.id, "kind": "BuiltinTag", "display_label": "orange"},
                            "path": f"data/{org3.id}/tags/{orange.id}",
                            "properties": {
                                "IS_PROTECTED": {
                                    "path": f"data/{org3.id}/tags/{orange.id}/property/IS_PROTECTED",
                                    "changes": [
                                        {
                                            "branch": "branch2",
                                            "type": "IS_PROTECTED",
                                            "changed_at": "2023-08-17T15:24:53.870291Z",
                                            "action": "added",
                                            "value": {"new": False, "previous": None},
                                        }
                                    ],
                                },
                                "IS_VISIBLE": {
                                    "path": f"data/{org3.id}/tags/{orange.id}/property/IS_VISIBLE",
                                    "changes": [
                                        {
                                            "branch": "branch2",
                                            "type": "IS_VISIBLE",
                                            "changed_at": "2023-08-17T15:24:53.870291Z",
                                            "action": "added",
                                            "value": {"new": True, "previous": None},
                                        }
                                    ],
                                },
                            },
                            "changed_at": None,
                            "action": {"branch2": "added"},
                        },
                    },
                },
            }
        },
        "summary": {"added": 3, "removed": 0, "updated": 0},
        "action": {"branch2": "updated"},
        "display_label": {"branch2": "Org3"},
    }

    expected_org1 = {
        "kind": "CoreOrganization",
        "id": org1.id,
        "path": f"data/{org1.id}",
        "elements": {
            "tags": {
                "type": "RelationshipMany",
                "name": "tags",
                "path": f"data/{org1.id}/tags",
                "change": {
                    "type": "RelationshipMany",
                    "identifier": "builtintag__coreorganization",
                    "branches": ["main"],
                    "summary": {"added": 2, "removed": 2, "updated": 0},
                    "peers": {
                        green.id: {
                            "branches": ["main"],
                            "peer": {"id": green.id, "kind": "BuiltinTag", "display_label": "green"},
                            "path": f"data/{org1.id}/tags/{green.id}",
                            "properties": {
                                "IS_VISIBLE": {
                                    "path": f"data/{org1.id}/tags/{green.id}/property/IS_VISIBLE",
                                    "changes": [
                                        {
                                            "branch": "main",
                                            "type": "IS_VISIBLE",
                                            "changed_at": "2023-08-17T15:24:53.747940Z",
                                            "action": "removed",
                                            "value": {"new": True, "previous": True},
                                        }
                                    ],
                                },
                                "IS_PROTECTED": {
                                    "path": f"data/{org1.id}/tags/{green.id}/property/IS_PROTECTED",
                                    "changes": [
                                        {
                                            "branch": "main",
                                            "type": "IS_PROTECTED",
                                            "changed_at": "2023-08-17T15:24:53.747940Z",
                                            "action": "removed",
                                            "value": {"new": False, "previous": False},
                                        }
                                    ],
                                },
                            },
                            "changed_at": None,
                            "action": {"main": "removed"},
                        },
                        blue.id: {
                            "branches": ["main"],
                            "peer": {"id": blue.id, "kind": "BuiltinTag", "display_label": "blue"},
                            "path": f"data/{org1.id}/tags/{blue.id}",
                            "properties": {
                                "IS_PROTECTED": {
                                    "changes": [
                                        {
                                            "action": "added",
                                            "branch": "main",
                                            "changed_at": "2023-08-24T16:05:09.207886Z",
                                            "type": "IS_PROTECTED",
                                            "value": {"new": False, "previous": None},
                                        },
                                    ],
                                    "path": f"data/{org1.id}/tags/{blue.id}/property/IS_PROTECTED",
                                },
                                "IS_VISIBLE": {
                                    "changes": [
                                        {
                                            "action": "added",
                                            "branch": "main",
                                            "changed_at": "2023-08-24T16:05:09.207886Z",
                                            "type": "IS_VISIBLE",
                                            "value": {"new": True, "previous": None},
                                        },
                                    ],
                                    "path": f"data/{org1.id}/tags/{blue.id}/property/IS_VISIBLE",
                                },
                            },
                            "changed_at": None,
                            "action": {"main": "added"},
                        },
                    },
                },
            }
        },
        "summary": {"added": 1, "removed": 1, "updated": 1},
        "action": {"main": "updated"},
        "display_label": {"main": "Org1"},
    }

    paths_to_exclude = [
        r"root\[\d\]\['elements'\]\['\w+'\]\['change'\]\['peers'\]\['[\w\-]+'\]\['properties'\]\['\w+'\]\['changes'\]\[\d\]\['changed_at'\]",
    ]
    expected_response = [expected_org1, expected_org3]

    assert (
        DeepDiff(expected_response, data["diffs"], exclude_regex_paths=paths_to_exclude, ignore_order=True).to_dict()
        == {}
    )


async def test_diff_data_relationship_many_conflict(
    db: InfrahubDatabase, client, client_headers, data_conflict_relationship_many
):
    org1 = data_conflict_relationship_many["org1"]
    red = data_conflict_relationship_many["red"]
    green = data_conflict_relationship_many["green"]

    with client:
        response = client.get(
            "/api/diff/data-new?branch=branch2&branch_only=false",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()

    expected_response = [
        {
            "kind": "CoreOrganization",
            "id": org1.id,
            "path": f"data/{org1.id}",
            "elements": {
                "tags": {
                    "type": "RelationshipMany",
                    "name": "tags",
                    "path": f"data/{org1.id}/tags",
                    "change": {
                        "type": "RelationshipMany",
                        "identifier": "builtintag__coreorganization",
                        "branches": ["main", "branch2"],
                        "summary": {"added": 0, "removed": 4, "updated": 1},
                        "peers": {
                            red.id: {
                                "branches": ["main", "branch2"],
                                "peer": {"id": red.id, "kind": "BuiltinTag", "display_label": "red"},
                                "path": f"data/{org1.id}/tags/{red.id}",
                                "properties": {
                                    "IS_VISIBLE": {
                                        "path": f"data/{org1.id}/tags/{red.id}/property/IS_VISIBLE",
                                        "changes": [
                                            {
                                                "branch": "main",
                                                "type": "IS_VISIBLE",
                                                "changed_at": "2023-08-17T15:56:27.114705Z",
                                                "action": "removed",
                                                "value": {"new": True, "previous": True},
                                            }
                                        ],
                                    },
                                    "IS_PROTECTED": {
                                        "path": f"data/{org1.id}/tags/{red.id}/property/IS_PROTECTED",
                                        "changes": [
                                            {
                                                "branch": "branch2",
                                                "type": "IS_PROTECTED",
                                                "changed_at": "2023-08-17T15:56:27.190831Z",
                                                "action": "updated",
                                                "value": {"new": True, "previous": False},
                                            },
                                            {
                                                "action": "removed",
                                                "branch": "main",
                                                "changed_at": "2023-08-24T16:00:37.422213Z",
                                                "type": "IS_PROTECTED",
                                                "value": {"new": False, "previous": False},
                                            },
                                        ],
                                    },
                                },
                                "changed_at": None,
                                "action": {
                                    "main": "removed",
                                    "branch2": "updated",
                                },
                            },
                            green.id: {
                                "branches": ["main"],
                                "peer": {"id": green.id, "kind": "BuiltinTag", "display_label": "green"},
                                "path": f"data/{org1.id}/tags/{green.id}",
                                "properties": {
                                    "IS_VISIBLE": {
                                        "path": f"data/{org1.id}/tags/{green.id}/property/IS_VISIBLE",
                                        "changes": [
                                            {
                                                "branch": "main",
                                                "type": "IS_VISIBLE",
                                                "changed_at": "2023-08-17T15:56:27.114705Z",
                                                "action": "removed",
                                                "value": {"new": True, "previous": True},
                                            }
                                        ],
                                    },
                                    "IS_PROTECTED": {
                                        "path": f"data/{org1.id}/tags/{green.id}/property/IS_PROTECTED",
                                        "changes": [
                                            {
                                                "branch": "main",
                                                "type": "IS_PROTECTED",
                                                "changed_at": "2023-08-17T15:56:27.114705Z",
                                                "action": "removed",
                                                "value": {"new": False, "previous": False},
                                            }
                                        ],
                                    },
                                },
                                "changed_at": None,
                                "action": {"main": "removed"},
                            },
                        },
                        # "action": {
                        #     "main": "removed",
                        #     "branch2": "updated",
                        # },
                    },
                }
            },
            "summary": {"added": 0, "removed": 3, "updated": 2},
            "action": {"main": "updated", "branch2": "updated"},
            "display_label": {"main": "Org1", "branch2": "Org1"},
        }
    ]
    paths_to_exclude = [
        r"root\[\d\]\['elements'\]\['\w+'\]\['change'\]\['peers'\]\['[\w\-]+'\]\['properties'\]\['\w+'\]\['changes'\]\[\d\]\['changed_at'\]",
    ]

    assert (
        DeepDiff(expected_response, data["diffs"], exclude_regex_paths=paths_to_exclude, ignore_order=True).to_dict()
        == {}
    )


# ----------------------------------------------------------------------
# Deprecated API
# ----------------------------------------------------------------------


async def test_diff_data_deprecated_endpoint_branch_only_default(
    db: InfrahubDatabase, client, client_headers, car_person_data_generic_diff
):
    c1 = car_person_data_generic_diff["c1"]
    c4 = car_person_data_generic_diff["c4"]
    p1 = car_person_data_generic_diff["p1"]
    p2 = car_person_data_generic_diff["p2"]
    p3 = car_person_data_generic_diff["p3"]
    r1 = car_person_data_generic_diff["r1"]

    with client:
        response = client.get(
            "/api/diff/data?branch=branch2&branch_only=true",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data is not None

    assert list(data.keys()) == ["branch2"]
    branch2 = {node["id"]: node for node in data["branch2"]}

    assert branch2[p1]["display_label"] == "John"
    assert branch2[p1]["kind"] == "TestPerson"
    assert branch2[p1]["action"] == "updated"
    assert branch2[p1]["summary"] == {"added": 0, "removed": 1, "updated": 0}
    assert branch2[p1]["elements"]["cars"]["peers"][0]["peer"]["id"] == c1
    assert branch2[p1]["elements"]["cars"]["peers"][0]["peer"]["kind"] == "TestElectricCar"

    assert branch2[p2]["display_label"] == "Jane"
    assert branch2[p2]["kind"] == "TestPerson"
    assert branch2[p2]["action"] == "updated"
    assert branch2[p2]["summary"] == {"added": 0, "removed": 1, "updated": 0}
    assert branch2[p2]["elements"]["cars"]["peers"][0]["peer"]["id"] == c4
    assert branch2[p2]["elements"]["cars"]["peers"][0]["peer"]["kind"] == "TestGazCar"

    assert branch2[p3]["display_label"] == "Bill"
    assert branch2[p3]["action"] == "added"
    assert branch2[p3]["summary"] == {"added": 3, "removed": 0, "updated": 0}
    assert branch2[p3]["elements"]["cars"]["peers"][0]["peer"]["id"] == c1
    assert len(branch2[p3]["elements"]["name"]["properties"]) == 2

    assert branch2[c1]["kind"] == "TestElectricCar"
    assert branch2[c1]["action"] == "updated"
    assert branch2[c1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert branch2[c1]["elements"]["owner"]["peer"]["new"]["id"] == p3
    assert branch2[c1]["elements"]["owner"]["peer"]["previous"]["id"] == p1
    # assert branch2[c1]["elements"]["owner"]["summary"] = {'added': 0, 'removed': 0, 'updated': 0}

    assert branch2[c4]["kind"] == "TestGazCar"
    assert branch2[c4]["action"] == "removed"
    assert branch2[c4]["summary"] == {"added": 0, "removed": 5, "updated": 0}
    assert branch2[c4]["elements"]["owner"]["peer"]["previous"]["id"] == p2

    assert branch2[r1]["kind"] == "CoreRepository"
    assert branch2[r1]["action"] == "updated"
    assert branch2[r1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert branch2[r1]["elements"]["description"]["value"]["value"]["new"] == "Second change in branch"
    # assert branch2[r1]["elements"]["commit"]["value"]["value"]['previous'] == "aaaaaaaaa" FIXME
    assert (
        branch2[r1]["elements"]["description"]["value"]["changed_at"]
        == car_person_data_generic_diff["time21"].to_iso8601_string()
    )


@pytest.mark.xfail(reason="Need to investigate, occasionally fails")
async def test_diff_data_deprecated_endpoint_branch_time_from(
    db: InfrahubDatabase, client, client_headers, car_person_data_generic_diff
):
    time20 = car_person_data_generic_diff["time20"]

    c4 = car_person_data_generic_diff["c4"]
    p2 = car_person_data_generic_diff["p2"]
    r1 = car_person_data_generic_diff["r1"]

    with client:
        response = client.get(
            f"/api/diff/data?branch=branch2&branch_only=true&time_from={time20.to_iso8601_string()}",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert list(data.keys()) == ["branch2"]
    assert len(data["branch2"]) == 3

    branch2 = {node["id"]: node for node in data["branch2"]}

    assert branch2[c4]["kind"] == "TestGazCar"
    assert branch2[c4]["action"] == "removed"
    assert branch2[c4]["summary"] == {"added": 0, "removed": 5, "updated": 0}
    assert branch2[c4]["elements"]["owner"]["peer"]["previous"]["id"] == p2

    assert branch2[p2]["display_label"] == "Jane"
    assert branch2[p2]["kind"] == "TestPerson"
    assert branch2[p2]["action"] == "updated"
    assert branch2[p2]["summary"] == {"added": 0, "removed": 1, "updated": 0}
    assert branch2[p2]["elements"]["cars"]["peers"][0]["peer"]["id"] == c4
    assert branch2[p2]["elements"]["cars"]["peers"][0]["peer"]["kind"] == "GazCar"

    assert branch2[r1]["kind"] == "CoreRepository"
    assert branch2[r1]["action"] == "updated"
    assert branch2[r1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert branch2[r1]["elements"]["description"]["value"]["value"]["new"] == "dddddddddd"
    assert branch2[r1]["elements"]["description"]["value"]["value"]["previous"] == "bbbbbbbbbbbbbbb"  # FIXME
    assert (
        branch2[r1]["elements"]["commit"]["value"]["changed_at"]
        == car_person_data_generic_diff["time21"].to_iso8601_string()
    )


async def test_diff_data_deprecated_endpoint_branch_time_from_to(
    db: InfrahubDatabase, client, client_headers, car_person_data_generic_diff
):
    time0 = car_person_data_generic_diff["time0"]
    time20 = car_person_data_generic_diff["time20"]

    c1 = car_person_data_generic_diff["c1"]
    p1 = car_person_data_generic_diff["p1"]
    p3 = car_person_data_generic_diff["p3"]
    r1 = car_person_data_generic_diff["r1"]

    with client:
        response = client.get(
            f"/api/diff/data?branch=branch2&branch_only=true&time_from={time0.to_iso8601_string()}&time_to={time20.to_iso8601_string()}",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert list(data.keys()) == ["branch2"]

    branch2 = {node["id"]: node for node in data["branch2"]}

    assert branch2[p1]["display_label"] == "John"
    assert branch2[p1]["kind"] == "TestPerson"
    assert branch2[p1]["action"] == "updated"
    assert branch2[p1]["summary"] == {"added": 0, "removed": 1, "updated": 0}
    assert branch2[p1]["elements"]["cars"]["peers"][0]["peer"]["id"] == c1
    assert branch2[p1]["elements"]["cars"]["peers"][0]["peer"]["kind"] == "TestElectricCar"

    assert branch2[p3]["display_label"] == "Bill"
    assert branch2[p3]["action"] == "added"
    assert branch2[p3]["summary"] == {"added": 3, "removed": 0, "updated": 0}
    assert branch2[p3]["elements"]["cars"]["peers"][0]["peer"]["id"] == c1
    assert len(branch2[p3]["elements"]["name"]["properties"]) == 2

    assert branch2[c1]["kind"] == "TestElectricCar"
    assert branch2[c1]["action"] == "updated"
    assert branch2[c1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert branch2[c1]["elements"]["owner"]["peer"]["new"]["id"] == p3
    assert branch2[c1]["elements"]["owner"]["peer"]["previous"]["id"] == p1

    assert branch2[r1]["kind"] == "CoreRepository"
    assert branch2[r1]["action"] == "updated"
    assert branch2[r1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert branch2[r1]["elements"]["description"]["value"]["value"]["new"] == "First change in branch"
    # assert branch2[r1]["elements"]["commit"]["value"]["value"]['previous'] == "aaaaaaaaa" FIXME
    assert (
        branch2[r1]["elements"]["description"]["value"]["changed_at"]
        == car_person_data_generic_diff["time12"].to_iso8601_string()
    )


async def test_diff_data_deprecated_endpoint_with_main_default(
    db: InfrahubDatabase, client, client_headers, car_person_data_generic_diff
):
    c2 = car_person_data_generic_diff["c2"]
    p1 = car_person_data_generic_diff["p1"]

    with client:
        response = client.get(
            "/api/diff/data?branch=branch2&branch_only=false",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert sorted(data.keys()) == ["branch2", "main"]
    assert len(data["branch2"]) == 5
    assert len(data["main"]) == 2

    # branch2 = { node["id"]: node for node in data["branch2"] }
    main = {node["id"]: node for node in data["main"]}

    assert main[p1]["kind"] == "TestPerson"
    assert main[p1]["action"] == "updated"
    assert main[p1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert main[p1]["elements"]["height"]["value"]["value"]["new"] == 120
    assert main[p1]["elements"]["height"]["value"]["value"]["previous"] == 180

    assert main[c2]["kind"] == "TestElectricCar"
    assert main[c2]["action"] == "updated"
    assert main[c2]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert main[c2]["elements"]["nbr_seats"]["value"]["value"]["new"] == 4
    assert main[c2]["elements"]["nbr_seats"]["value"]["value"]["previous"] == 2


async def test_diff_data_deprecated_endpoint_with_main_time_from(
    db: InfrahubDatabase, client, client_headers, car_person_data_generic_diff
):
    time20 = car_person_data_generic_diff["time20"]

    c2 = car_person_data_generic_diff["c2"]
    c4 = car_person_data_generic_diff["c4"]
    p2 = car_person_data_generic_diff["p2"]
    r1 = car_person_data_generic_diff["r1"]

    with client:
        response = client.get(
            f"/api/diff/data?branch=branch2&branch_only=false&time_from={time20.to_iso8601_string()}",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert sorted(data.keys()) == ["branch2", "main"]

    branch2 = {node["id"]: node for node in data["branch2"]}
    main = {node["id"]: node for node in data["main"]}

    assert main[c2]["kind"] == "TestElectricCar"
    assert main[c2]["action"] == "updated"
    assert main[c2]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert main[c2]["elements"]["nbr_seats"]["value"]["value"]["new"] == 4
    assert main[c2]["elements"]["nbr_seats"]["value"]["value"]["previous"] == 2

    assert branch2[c4]["kind"] == "TestGazCar"
    assert branch2[c4]["action"] == "removed"
    assert branch2[c4]["summary"] == {"added": 0, "removed": 5, "updated": 0}
    assert branch2[c4]["elements"]["owner"]["peer"]["previous"]["id"] == p2

    assert branch2[p2]["display_label"] == "Jane"
    assert branch2[p2]["kind"] == "TestPerson"
    assert branch2[p2]["action"] == "updated"
    assert branch2[p2]["summary"] == {"added": 0, "removed": 1, "updated": 0}
    assert branch2[p2]["elements"]["cars"]["peers"][0]["peer"]["id"] == c4
    assert branch2[p2]["elements"]["cars"]["peers"][0]["peer"]["kind"] == "TestGazCar"

    assert branch2[r1]["kind"] == "CoreRepository"
    assert branch2[r1]["action"] == "updated"
    assert branch2[r1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert branch2[r1]["elements"]["description"]["value"]["value"]["new"] == "Second change in branch"
    # assert branch2[r1]["elements"]["commit"]["value"]["value"]['previous'] == "bbbbbbbbbbbbbbb" FIXME
    assert (
        branch2[r1]["elements"]["description"]["value"]["changed_at"]
        == car_person_data_generic_diff["time21"].to_iso8601_string()
    )


async def test_diff_data_deprecated_endpoint_with_main_time_from_to(
    db: InfrahubDatabase, client, client_headers, car_person_data_generic_diff
):
    time0 = car_person_data_generic_diff["time0"]
    time20 = car_person_data_generic_diff["time20"]

    c1 = car_person_data_generic_diff["c1"]
    p1 = car_person_data_generic_diff["p1"]
    p3 = car_person_data_generic_diff["p3"]
    r1 = car_person_data_generic_diff["r1"]

    with client:
        response = client.get(
            f"/api/diff/data?branch=branch2&branch_only=false&time_from={time0.to_iso8601_string()}&time_to={time20.to_iso8601_string()}",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert sorted(data.keys()) == ["branch2", "main"]

    branch2 = {node["id"]: node for node in data["branch2"]}
    main = {node["id"]: node for node in data["main"]}

    # assert branch2[p1]["display_label"] == "John"
    # assert branch2[p1]["kind"] == "Person"
    # assert branch2[p1]["action"] == "updated"
    # assert branch2[p1]["summary"] == {'added': 0, 'removed': 1, 'updated': 0}
    # assert branch2[p1]["elements"]["cars"]["peers"][0]["peer"]["id"] == c1
    # assert branch2[p1]["elements"]["cars"]["peers"][0]["peer"]["kind"] == "ElectricCar"

    assert branch2[p3]["display_label"] == "Bill"
    assert branch2[p3]["action"] == "added"
    assert branch2[p3]["summary"] == {"added": 3, "removed": 0, "updated": 0}
    assert branch2[p3]["elements"]["cars"]["peers"][0]["peer"]["id"] == c1
    assert len(branch2[p3]["elements"]["name"]["properties"]) == 2

    assert branch2[c1]["kind"] == "TestElectricCar"
    assert branch2[c1]["action"] == "updated"
    assert branch2[c1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert branch2[c1]["elements"]["owner"]["peer"]["new"]["id"] == p3
    assert branch2[c1]["elements"]["owner"]["peer"]["previous"]["id"] == p1

    assert branch2[r1]["kind"] == "CoreRepository"
    assert branch2[r1]["action"] == "updated"
    assert branch2[r1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert branch2[r1]["elements"]["description"]["value"]["value"]["new"] == "First change in branch"
    # assert branch2[r1]["elements"]["commit"]["value"]["value"]['previous'] == "aaaaaaaaa" FIXME
    assert (
        branch2[r1]["elements"]["description"]["value"]["changed_at"]
        == car_person_data_generic_diff["time12"].to_iso8601_string()
    )

    assert main[p1]["kind"] == "TestPerson"
    assert main[p1]["action"] == "updated"
    assert main[p1]["summary"] == {"added": 0, "removed": 0, "updated": 1}
    assert main[p1]["elements"]["height"]["value"]["value"]["new"] == 120
    assert main[p1]["elements"]["height"]["value"]["value"]["previous"] == 180


async def test_diff_artifact(db: InfrahubDatabase, client, client_headers, car_person_data_artifact_diff):
    with client:
        response = client.get(
            "/api/diff/artifacts?branch=branch3",
            headers=client_headers,
        )

    assert response.status_code == 200
    data = response.json()

    expected_response = {
        car_person_data_artifact_diff["art2"]: {
            "action": "added",
            "branch": "branch3",
            "display_label": "bolt #444444 - myyartifact",
            "id": car_person_data_artifact_diff["art2"],
            "target": {
                "id": car_person_data_artifact_diff["c2"],
                "kind": "TestElectricCar",
                "display_label": "bolt #444444",
            },
            "item_new": {
                "checksum": "zxcv9063c26263353de24e1b913e1e1c",
                "storage_id": "qwertyui-073f-4173-aa4b-f50e1309f03c",
            },
            "item_previous": None,
        },
        car_person_data_artifact_diff["art1"]: {
            "action": "updated",
            "branch": "branch3",
            "display_label": "volt #444444 - myyartifact",
            "id": car_person_data_artifact_diff["art1"],
            "target": {
                "id": car_person_data_artifact_diff["c1"],
                "kind": "TestElectricCar",
                "display_label": "volt #444444",
            },
            "item_new": {
                "checksum": "zxcv9063c26263353de24e1b911z1x2c3v",
                "storage_id": "azertyui-073f-4173-aa4b-f50e1309f03c",
            },
            "item_previous": {
                "checksum": "60d39063c26263353de24e1b913e1e1c",
                "storage_id": "8caf6f89-073f-4173-aa4b-f50e1309f03c",
            },
        },
    }

    assert DeepDiff(expected_response, data, ignore_order=True).to_dict() == {}
