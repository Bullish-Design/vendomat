# typer — gotchas & patterns (raw curation material)

Freeform notes that feed `SKILL.md`. Not installed into a consumer; the curated skill is.

## Exit codes are the API

Honor the `*man` 0/1/2/3 contract by raising `typer.Exit(code=...)` — never `sys.exit` or a bare
`return`. `0` ok · `1` a domain decision/finding · `2` infra/config · `3` invalid usage. Typer maps
an uncaught exception to a non-zero code, but be explicit so the code is meaningful to callers.

## `no_args_is_help` instead of erroring on a bare invocation

```python
app = typer.Typer(no_args_is_help=True)
```

A bare `tool` then prints usage (exit 0) rather than a "missing command" error — the family default.

## Options vs. arguments

- Positional → `typer.Argument`; flags → `typer.Option`. Both are declared as defaults on the
  function parameter, *not* decorators.
- A type hint of `bool` with `typer.Option(False)` gives a `--flag/--no-flag` pair automatically.
- Prefer explicit `--name` over relying on the parameter name for anything user-facing.

## Testing

Use `typer.testing.CliRunner` — `result = runner.invoke(app, ["sub", "--flag"])`, then assert
`result.exit_code` and `result.stdout`. This is how the family smoke-tests its CLIs.

## Output

Use `typer.echo` (not `print`) so output routing/capture stays consistent. Normalize structured
output through Pydantic models and render them at the edge.
