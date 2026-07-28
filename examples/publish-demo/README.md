# Vendomat publish demo

This Python consumer keeps an editable local dependency, but publishes a GitHub-pinned uv source.

Run the proof from the Vendomat repository root:

```sh
devenv shell -- examples/publish-demo/verify-publish.sh
```

The script creates a temporary Git repository and bare remote; it does not contact GitHub or
modify this checkout. It verifies that the remote sees the `git` + `tag` source while the local
consumer still has `path = "vendor/acme-widget"`.

The real pre-push path runs `uv lock` after materializing Git sources, then rejects package
additions, removals, and version changes.

The mapping in `vendomat.toml` is an exact multiline replacement. Add one mapping for each
dependency source block you want Vendomat to publish.
