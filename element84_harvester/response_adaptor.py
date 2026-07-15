import json
import os

ELEMENT84_API_URL_DEFAULT = "https://earth-search.aws.element84.com/v1"


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
