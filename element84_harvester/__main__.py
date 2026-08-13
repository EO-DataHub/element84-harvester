import hashlib
import json
import logging
import os

import click
import requests
from botocore.exceptions import ClientError
from eodhp_utils.aws.s3 import upload_file_s3
from eodhp_utils.runner import get_boto3_session, get_pulsar_client, setup_logging

from element84_harvester.element84_harvester_messager import Element84HarvesterMessager
from element84_harvester.response_adaptor import (
    ELEMENT84_API_URL_DEFAULT,
    add_sentinel_2_c1_l2a_metadata,
    rewrite_hrefs,
)

setup_logging(verbosity=2)

public_catalogue_root = os.getenv("PUBLIC_CATALOGUE_ROOT", "catalogs/public")


def get_collections() -> list:
    """Fetch each allowlisted collection's full STAC document from Earth Search.

    Unlike Planet's item-types API, Earth Search already serves valid STAC collections, so there's
    no need to list every upstream collection just to filter it down to the allowlist - each
    allowlisted collection is fetched directly by id.
    """
    element84_api_url = os.environ.get("ELEMENT84_API_URL", ELEMENT84_API_URL_DEFAULT)
    valid_collection_ids = [c for c in os.environ.get("VALID_COLLECTIONS", "").split(",") if c]
    logging.info(f"Valid collections are: {valid_collection_ids}")

    collections = []
    for collection_id in valid_collection_ids:
        response = requests.get(f"{element84_api_url}/collections/{collection_id}")
        response.raise_for_status()
        collections.append(add_sentinel_2_c1_l2a_metadata(rewrite_hrefs(response.json())))

    return collections


def get_file_hash(data: str) -> str:
    """Returns hash of data available"""

    def _md5_hash(byte_str: bytes) -> str:
        """Calculates an md5 hash for given bytestring"""
        md5 = hashlib.md5()
        md5.update(byte_str)
        return md5.hexdigest()

    return _md5_hash(data.encode("utf-8"))


def get_file_s3(bucket: str, key: str, s3_client) -> str | None:
    """Retrieve data from an S3 bucket"""
    try:
        file_obj = s3_client.get_object(Bucket=bucket, Key=key)
        return file_obj["Body"].read().decode("utf-8")
    except ClientError as e:
        logging.warning(f"File retrieval failed for {key}: {e}")
        return None


def get_metadata(bucket: str, key: str, s3_client) -> dict:
    """Read file at given S3 location and parse as JSON"""
    previously_harvested = get_file_s3(bucket, key, s3_client)
    if previously_harvested is None:
        return {}
    return json.loads(previously_harvested)


def make_catalogue() -> dict:
    """Top level catalogue for element84 data"""
    return {
        "type": "Catalog",
        "id": "element84",
        "stac_version": "1.0.0",
        "description": "Element84 Earth Search Datasets",
        "links": [],
    }


@click.group()
def cli():
    """This is just a placeholder to act as the entrypoint, you can do things with global options here
    if required"""
    pass


@cli.command()
# not currently used but keeping the same structure as the other harvester repos
@click.argument("workspace_name", type=str)
@click.argument(
    "catalog", type=str
)  # not currently used but keeping the same structure as the other harvester repos
@click.argument("s3_bucket", type=str)
def harvest(workspace_name: str, catalog: str, s3_bucket: str):
    s3_client = get_boto3_session().client("s3")

    harvested_data = {}
    latest_harvested = {}

    logging.info("Harvesting from element84 Earth Search")

    key_root = f"{public_catalogue_root}/catalogs/element84"

    pulsar_client = get_pulsar_client()
    producer = pulsar_client.create_producer(
        topic="harvested", producer_name="stac_harvester/element84", chunking_enabled=True
    )

    element84_harvester_messager = Element84HarvesterMessager(
        s3_client=s3_client,
        output_bucket=s3_bucket,
        cat_output_prefix="git-harvester/",
        producer=producer,
    )

    metadata_s3_key = "harvested-metadata/element84"
    previously_harvested = get_metadata(s3_bucket, metadata_s3_key, s3_client)
    logging.info(f"Previously harvested URLs: {previously_harvested}")

    catalogue_data = make_catalogue()
    catalogue_key = f"{key_root}.json"

    file_hash = get_file_hash(json.dumps(catalogue_data))
    previous_hash = previously_harvested.pop(catalogue_key, None)
    latest_harvested[catalogue_key] = file_hash
    if not previous_hash or previous_hash != file_hash:
        logging.info(f"Added: {catalogue_key}")
        harvested_data[catalogue_key] = catalogue_data

    for collection in get_collections():
        collection_id = collection["id"]
        collection_key = f"{key_root}/collections/{collection_id}.json"

        file_hash = get_file_hash(json.dumps(collection))
        previous_hash = previously_harvested.pop(collection_key, None)
        latest_harvested[collection_key] = file_hash
        if not previous_hash or previous_hash != file_hash:
            logging.info(f"Added: {collection_key}")
            harvested_data[collection_key] = collection

    deleted_keys = list(previously_harvested.keys())

    # Send message for altered keys
    msg = {"harvested_data": harvested_data, "deleted_keys": deleted_keys}
    element84_harvester_messager.consume(msg)

    upload_file_s3(json.dumps(latest_harvested), s3_bucket, metadata_s3_key, s3_client)


if __name__ == "__main__":
    cli(obj={})
