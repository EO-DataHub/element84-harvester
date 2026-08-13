from element84_harvester.response_adaptor import (
    SENTINEL_2_C1_L2A_ACKNOWLEDGEMENT,
    SENTINEL_2_C1_L2A_THUMBNAIL_URL,
    add_sentinel_2_c1_l2a_metadata,
)


def test_add_sentinel_2_c1_l2a_metadata_adds_acknowledgement_and_thumbnail():
    stac_doc = {
        "id": "sentinel-2-c1-l2a",
        "description": "Sentinel-2 Collection 1 Level-2A",
    }

    result = add_sentinel_2_c1_l2a_metadata(stac_doc)

    assert result["description"] == (
        f"Sentinel-2 Collection 1 Level-2A\n\n{SENTINEL_2_C1_L2A_ACKNOWLEDGEMENT}"
    )
    assert result["assets"]["thumbnail"] == {
        "href": SENTINEL_2_C1_L2A_THUMBNAIL_URL,
        "type": "image/png",
        "roles": ["thumbnail"],
    }


def test_add_sentinel_2_c1_l2a_metadata_preserves_existing_assets():
    stac_doc = {
        "id": "sentinel-2-c1-l2a",
        "description": "Sentinel-2 Collection 1 Level-2A",
        "assets": {"other": {"href": "https://example.com/other.tif"}},
    }

    result = add_sentinel_2_c1_l2a_metadata(stac_doc)

    assert result["assets"]["other"] == {"href": "https://example.com/other.tif"}
    assert result["assets"]["thumbnail"]["href"] == SENTINEL_2_C1_L2A_THUMBNAIL_URL


def test_add_sentinel_2_c1_l2a_metadata_ignores_other_collections():
    stac_doc = {"id": "some-other-collection", "description": "Something else"}

    result = add_sentinel_2_c1_l2a_metadata(stac_doc)

    assert result == stac_doc
