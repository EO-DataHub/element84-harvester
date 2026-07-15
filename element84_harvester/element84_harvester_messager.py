import json
from typing import Sequence

from eodhp_utils.messagers import Messager


class Element84HarvesterMessager(Messager[str]):
    """
    Loads STAC files harvested from the element84 Earth Search API into an S3 bucket with file key
    relating to the owning catalog combined with the file path in the public catalogue.
    For example: git-harvester/catalogs/public/catalogs/element84/collections/sentinel-2-c1-l2a.json
    Then sends a catalogue harvested message via Pulsar to trigger transformer and ingester.
    """

    def process_msg(self, msg: dict) -> Sequence[Messager.Action]:
        action_list = []
        harvested_data = msg["harvested_data"]
        deleted_keys = msg["deleted_keys"]

        for key, value in harvested_data.items():
            action_list.append(
                Messager.OutputFileAction(
                    file_body=json.dumps(value),
                    cat_path=key,
                )
            )

        for key in deleted_keys:
            action_list.append(Messager.OutputFileAction(file_body=None, cat_path=key))

        return action_list

    def gen_empty_catalogue_message(self, msg):
        return {
            "id": "harvester/element84",
            "workspace": "default_workspace",
            "repository": "",
            "branch": "",
            "bucket_name": self.output_bucket,
            "source": "",
            "target": "",
        }
