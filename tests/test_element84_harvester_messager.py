import json
from unittest import mock

from element84_harvester.element84_harvester_messager import Element84HarvesterMessager


def test_process_msg_updated():
    mock_s3_client = mock.MagicMock()
    mock_producer = mock.MagicMock()

    messager = Element84HarvesterMessager(
        s3_client=mock_s3_client,
        output_bucket="files_bucket_name",
        cat_output_prefix="stac-harvester/",
        producer=mock_producer,
    )

    test_msg = {
        "harvested_data": {
            "key/to/data1": {"id": "data1-id"},
            "key/to/data2": {"id": "data2-id"},
        },
        "deleted_keys": [],
    }

    expected_action_1 = Element84HarvesterMessager.OutputFileAction(
        file_body=json.dumps({"id": "data1-id"}),
        cat_path="key/to/data1",
    )
    expected_action_2 = Element84HarvesterMessager.OutputFileAction(
        file_body=json.dumps({"id": "data2-id"}),
        cat_path="key/to/data2",
    )

    result = messager.process_msg(test_msg)

    assert result == [expected_action_1, expected_action_2]


def test_process_msg_deleted():
    mock_s3_client = mock.MagicMock()
    mock_producer = mock.MagicMock()

    messager = Element84HarvesterMessager(
        s3_client=mock_s3_client,
        output_bucket="files_bucket_name",
        cat_output_prefix="stac-harvester/",
        producer=mock_producer,
    )

    test_msg = {
        "harvested_data": {},
        "deleted_keys": ["key/to/data1", "key/to/data2"],
    }

    expected_action_1 = Element84HarvesterMessager.OutputFileAction(
        file_body=None,  # pyright: ignore[reportArgumentType]
        cat_path="key/to/data1",
    )
    expected_action_2 = Element84HarvesterMessager.OutputFileAction(
        file_body=None,  # pyright: ignore[reportArgumentType]
        cat_path="key/to/data2",
    )

    result = messager.process_msg(test_msg)

    assert result == [expected_action_1, expected_action_2]


def test_process_msg_update_and_delete():
    mock_s3_client = mock.MagicMock()
    mock_producer = mock.MagicMock()

    messager = Element84HarvesterMessager(
        s3_client=mock_s3_client,
        output_bucket="files_bucket_name",
        cat_output_prefix="stac-harvester/",
        producer=mock_producer,
    )

    test_msg = {
        "harvested_data": {
            "key/to/data1": {"id": "data1-id"},
            "key/to/data2": {"id": "data2-id"},
        },
        "deleted_keys": ["key/to/data3", "key/to/data4"],
    }

    expected_action_1 = Element84HarvesterMessager.OutputFileAction(
        file_body=json.dumps({"id": "data1-id"}),
        cat_path="key/to/data1",
    )
    expected_action_2 = Element84HarvesterMessager.OutputFileAction(
        file_body=json.dumps({"id": "data2-id"}),
        cat_path="key/to/data2",
    )
    expected_action_3 = Element84HarvesterMessager.OutputFileAction(
        file_body=None,  # pyright: ignore[reportArgumentType]
        cat_path="key/to/data3",
    )
    expected_action_4 = Element84HarvesterMessager.OutputFileAction(
        file_body=None,  # pyright: ignore[reportArgumentType]
        cat_path="key/to/data4",
    )

    result = messager.process_msg(test_msg)

    assert result == [
        expected_action_1,
        expected_action_2,
        expected_action_3,
        expected_action_4,
    ]


def test_gen_empty_catalogue_message():
    mock_s3_client = mock.MagicMock()
    mock_producer = mock.MagicMock()

    messager = Element84HarvesterMessager(
        s3_client=mock_s3_client,
        output_bucket="files_bucket_name",
        cat_output_prefix="stac-harvester/",
        producer=mock_producer,
    )

    test_msg = {
        "harvested_data": {"key/to/data1": {"id": "data1-id"}},
        "deleted_keys": [],
    }

    result = messager.gen_empty_catalogue_message(test_msg)

    assert result == {
        "id": "harvester/element84",
        "workspace": "default_workspace",
        "repository": "",
        "branch": "",
        "bucket_name": "files_bucket_name",
        "source": "",
        "target": "",
    }
