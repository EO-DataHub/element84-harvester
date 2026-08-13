import json
import os

ELEMENT84_API_URL_DEFAULT = "https://earth-search.aws.element84.com/v1"

# See https://github.com/EO-DataHub/project_management/issues/580
SENTINEL_2_C1_L2A_ACKNOWLEDGEMENT = (
    "This collection is sourced from the Registry of Open Data on AWS. The STAC catalogue is "
    "provided by Element 84 Earth Search, and made discoverable through the EODH's federated "
    "search catalogue. Please note, users accessing this collection via EODH should "
    "appropriately acknowledge usage of this dataset in line with the Registry of Open Data on "
    "AWS guidance (see How to Cite): https://registry.opendata.aws/sentinel-2-l2a-cogs"
)
SENTINEL_2_C1_L2A_THUMBNAIL_URL = (
    "https://eodhp-thumbnails.s3.eu-west-2.amazonaws.com/element84/sentinel-2-c1-l2a/e84_s2.png"
)


def rewrite_hrefs(stac_doc: dict) -> dict:
    """Rewrite upstream Earth Search URLs to the platform's public URL.

    Mirrors the `sub_filter` text substitution already performed by the element84 nginx proxy
    (apps/resource-catalogue/base/proxies/element84/files/default.conf in
    eodhp-argocd-deployment): a literal string replacement over the serialized document rather
    than a structural walk, since that's what the existing proxy does and there's no need to
    re-derive equivalent rewrite logic from scratch.
    """
    public_url = os.environ.get("ELEMENT84_PUBLIC_URL")
    if not public_url:
        return stac_doc

    upstream_url = os.environ.get("ELEMENT84_API_URL", ELEMENT84_API_URL_DEFAULT)
    return json.loads(json.dumps(stac_doc).replace(upstream_url, public_url))


def add_sentinel_2_c1_l2a_metadata(stac_doc: dict) -> dict:
    """Add EODH-specific acknowledgement text and thumbnail to the sentinel-2-c1-l2a collection.

    See https://github.com/EO-DataHub/project_management/issues/580
    """
    if stac_doc.get("id") != "sentinel-2-c1-l2a":
        return stac_doc

    stac_doc["description"] = f"{stac_doc['description']}\n\n{SENTINEL_2_C1_L2A_ACKNOWLEDGEMENT}"
    stac_doc.setdefault("assets", {})["thumbnail"] = {
        "href": SENTINEL_2_C1_L2A_THUMBNAIL_URL,
        "type": "image/png",
        "roles": ["thumbnail"],
    }
    return stac_doc
