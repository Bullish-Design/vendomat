---
name: dep-typer
description: Use when writing or editing a Typer CLI in this repo — declaring commands, arguments vs options, the 0/1/2/3 exit-code contract via typer.Exit, no_args_is_help, and testing with CliRunner. Curated for typer 0.12.
auto_trigger:
  keywords: ["typer", "typer.Option", "typer.Argument", "typer.Exit", "CliRunner", "add a CLI command", "exit code contract", "no_args_is_help"]
---

# typer — building a CLI the `*man`-family way

A curated, usage-gated skill: it is installed into a repo only when that repo actually depends on
`typer`. Written against **typer 0.12**.

## Command surface

Declare one `typer.Typer` app; each subcommand is a `@app.command()` function. Make a bare
invocation print help instead of erroring:

```python
app = typer.Typer(help="...", no_args_is_help=True)

@app.command()
def sync() -> None: ...
```

## Arguments vs. options

Declared as parameter defaults, never decorators:

- positional → `lib: str = typer.Argument(...)`
- flag → `force: bool = typer.Option(False, "--force")` (a `bool` yields `--force/--no-force`)

## Exit codes are the contract

Raise `typer.Exit(code=...)` — `0` ok · `1` domain decision/finding · `2` infra/config · `3`
invalid usage. Don't collapse everything to `0`/`1`; the exit code is the CLI's API.

```python
raise typer.Exit(code=self_check_exit(checks))
```

## Output

Use `typer.echo`, not `print`. Render structured results through Pydantic models at the edge so
output stays normalized across the family.

## Testing

```python
from typer.testing import CliRunner
runner = CliRunner()
result = runner.invoke(app, ["sync", "--vendor-root", str(p)])
assert result.exit_code == 0
```

Deeper gotchas live in this entry's `notes.md` (curation source, not installed).
