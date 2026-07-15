# element84-harvester

Harvests the element84 Earth Search STAC catalogue (`https://earth-search.aws.element84.com/v1`)
and publishes it into the EO-DataHub `public` catalogue, so it appears as a real child in the
platform's catalogue tree instead of only being reachable via direct proxy URL.

Only the `sentinel-2-c1-l2a` collection is harvested (see `VALID_COLLECTIONS`). Like
`planet-harvester`, this harvester never fetches or writes STAC items — only `catalog.json` /
`collection.json` documents. Live item search/query traffic continues to be served by
`stac-element84-proxy`, which runs alongside this harvester unchanged.

## Getting started

This repo follows the same conventions as `planet-harvester` / `template-python`:

```commandline
make setup
```

creates a `venv`, builds `requirements.txt`/`requirements-dev.txt` from `pyproject.toml`, installs
dependencies, and installs `pre-commit`. See `Makefile` for `test`, `lint`, `dockerbuild`,
`dockerpush` targets.

## License

This project is licensed under the United Kingdom Research and Innovation BSD Licence. See
[LICENSE](LICENSE) for details.
