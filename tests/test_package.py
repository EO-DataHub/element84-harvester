import json
import os
from unittest import mock
from unittest.mock import patch

import boto3
import moto
import pytest
from click.testing import CliRunner

from element84_harvester.__main__ import get_collections, harvest
from element84_harvester.response_adaptor import rewrite_hrefs

UPSTREAM_URL = "https://earth-search.aws.element84.com/v1"
PUBLIC_URL = "https://example.com/api/catalogue/stac/catalogs/public/catalogs/element84"


@pytest.fixture(autouse=True)
def setenvvar(monkeypatch):
    with mock.patch.dict(os.environ, clear=True):
        envvars = {
            "ELEMENT84_API_URL": UPSTREAM_URL,
            "ELEMENT84_PUBLIC_URL": PUBLIC_URL,
            "VALID_COLLECTIONS": "sentinel-2-c1-l2a",
            "PUBLIC_CATALOGUE_ROOT": "catalogs/public",
        }
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield


@pytest.fixture
def mock_collection_response():
    return {
        "type": "Collection",
        "id": "sentinel-2-c1-l2a",
        "stac_version": "1.0.0",
        "description": "Sentinel-2 Collection 1 Level-2A",
        "license": "proprietary",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [["2015-06-27T10:25:31Z", None]]},
        },
        "links": [
            {"rel": "self", "href": f"{UPSTREAM_URL}/collections/sentinel-2-c1-l2a"},
            {"rel": "items", "href": f"{UPSTREAM_URL}/collections/sentinel-2-c1-l2a/items"},
        ],
        "item_assets": {},
    }


def _mock_pulsar(mock_create_client):
    mock_client = mock.MagicMock()
    mock_producer = mock.MagicMock()
    mock_create_client.return_value = mock_client
    mock_client.create_producer.return_value = mock_producer
    return mock_producer


@moto.mock_aws
@patch("element84_harvester.__main__.get_pulsar_client")
def test_harvest(mock_create_client, requests_mock, mock_collection_response):
    requests_mock.get(
        f"{UPSTREAM_URL}/collections/sentinel-2-c1-l2a",
        text=json.dumps(mock_collection_response),
    )
    mock_producer = _mock_pulsar(mock_create_client)

    bucket_name = "my-bucket"
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket_name)

    runner = CliRunner()
    result = runner.invoke(harvest, f"workspace catalogue {bucket_name}".split())
    assert result.exit_code == 0, result.output

    s3 = boto3.resource("s3")
    my_bucket = s3.Bucket(bucket_name)

    # catalog.json + collection.json + harvested-metadata manifest
    assert len(list(my_bucket.objects.all())) == 3

    args, kwargs = mock_producer.send.call_args
    call_args = json.loads(args[0])
    assert {
        "id",
        "workspace",
        "bucket_name",
        "added_keys",
        "updated_keys",
        "deleted_keys",
        "source",
        "target",
    }.issubset(call_args.keys())
    assert call_args["bucket_name"] == bucket_name
    assert len(call_args["added_keys"]) == 2
    assert len(call_args["updated_keys"]) == len(call_args["deleted_keys"]) == 0

    for key in call_args["added_keys"]:
        assert "earth-search.aws.element84.com" not in key


@moto.mock_aws
@patch("element84_harvester.__main__.Element84HarvesterMessager.consume")
@patch("element84_harvester.__main__.get_pulsar_client")
def test_harvest_expected_calls(
    mock_create_client, mock_messager_consume, requests_mock, mock_collection_response
):
    requests_mock.get(
        f"{UPSTREAM_URL}/collections/sentinel-2-c1-l2a",
        text=json.dumps(mock_collection_response),
    )
    mock_messager_consume.return_value = None
    _mock_pulsar(mock_create_client)

    bucket_name = "my-bucket"
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket_name)

    runner = CliRunner()
    runner.invoke(harvest, f"workspace catalogue {bucket_name}".split())

    mock_messager_consume.assert_called_once()


@moto.mock_aws
@patch("element84_harvester.__main__.get_pulsar_client")
def test_harvest_second_run_no_changes_sends_nothing(
    mock_create_client, requests_mock, mock_collection_response
):
    requests_mock.get(
        f"{UPSTREAM_URL}/collections/sentinel-2-c1-l2a",
        text=json.dumps(mock_collection_response),
    )
    mock_producer = _mock_pulsar(mock_create_client)

    bucket_name = "my-bucket"
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket_name)

    runner = CliRunner()
    runner.invoke(harvest, f"workspace catalogue {bucket_name}".split())
    assert mock_producer.send.call_count == 1

    runner.invoke(harvest, f"workspace catalogue {bucket_name}".split())
    # Nothing changed upstream, so no second catalogue-change message is sent.
    assert mock_producer.send.call_count == 1


@moto.mock_aws
@patch("element84_harvester.__main__.get_pulsar_client")
def test_harvest_removed_collection_produces_deleted_keys(
    mock_create_client, requests_mock, mock_collection_response, monkeypatch
):
    requests_mock.get(
        f"{UPSTREAM_URL}/collections/sentinel-2-c1-l2a",
        text=json.dumps(mock_collection_response),
    )
    mock_producer = _mock_pulsar(mock_create_client)

    bucket_name = "my-bucket"
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket_name)

    runner = CliRunner()
    runner.invoke(harvest, f"workspace catalogue {bucket_name}".split())

    monkeypatch.setenv("VALID_COLLECTIONS", "")
    runner.invoke(harvest, f"workspace catalogue {bucket_name}".split())

    assert mock_producer.send.call_count == 2
    args, kwargs = mock_producer.send.call_args
    call_args = json.loads(args[0])
    assert len(call_args["deleted_keys"]) == 1
    assert call_args["deleted_keys"][0].endswith("collections/sentinel-2-c1-l2a.json")
    assert call_args["added_keys"] == call_args["updated_keys"] == []


def test_get_collections(requests_mock, mock_collection_response):
    requests_mock.get(
        f"{UPSTREAM_URL}/collections/sentinel-2-c1-l2a",
        text=json.dumps(mock_collection_response),
    )

    collections = get_collections()

    assert len(collections) == 1
    assert collections[0]["id"] == "sentinel-2-c1-l2a"


def test_get_collections_rewrites_hrefs(requests_mock, mock_collection_response):
    requests_mock.get(
        f"{UPSTREAM_URL}/collections/sentinel-2-c1-l2a",
        text=json.dumps(mock_collection_response),
    )

    collections = get_collections()

    for link in collections[0]["links"]:
        assert link["href"].startswith(PUBLIC_URL)
        assert "earth-search.aws.element84.com" not in link["href"]


def test_rewrite_hrefs_no_public_url_configured(monkeypatch, mock_collection_response):
    monkeypatch.delenv("ELEMENT84_PUBLIC_URL", raising=False)

    result = rewrite_hrefs(mock_collection_response)

    assert result == mock_collection_response
