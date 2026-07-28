# Python source catalog

Vendomat separates committed source policy from machine-global checkout state:

```text
<vendomat checkout>/vendor/python/*.toml   reviewed repository + immutable commit policy
~/vendor/<package>/                       writable third-party Git checkout cache
<consumer>/.vendomat/sources.toml         generated, ignored agent source map
```

`~/vendor` is the default global source root. Override it with `VENDOMAT_SOURCE_ROOT` or
`--source-root PATH` when a machine needs a different location. `--vendomat-root` (also accepted
as `--catalog-root`) selects the Vendomat checkout containing committed catalog policy. A
Nix-installed CLI derives that catalog root from the existing `VENDOMAT_VENDOR_ROOT` environment
variable, while still writing third-party clones to the user's global source root.

Owned projects remain canonical sibling checkouts. For example, KnapPy's catalog `../knappy` path
is resolved relative to the consumer and is never copied into `~/vendor`.

```sh
vendomat vendor sync --repo-root /path/to/consumer
vendomat vendor status --repo-root /path/to/consumer
vendomat vendor doctor --repo-root /path/to/consumer
```

`vendor sync` only clones, fetches, and detaches reviewed third-party sources. It never writes a
source into `pyproject.toml`, `[tool.uv.sources]`, or `uv.lock`; these checkouts are for agent
grounding and investigation, not Python installation.

The generated map has a `[sources]` table of search paths and a matching `[revisions]` table of
reviewed catalog commits. The revision identifies reference source; compare the separately
resolved installed version and origin in `uv.lock` before treating it as runtime truth.
