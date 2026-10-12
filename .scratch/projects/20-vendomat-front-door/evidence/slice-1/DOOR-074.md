# `DOOR-074`: workspace and release channel gate

Date: 2026-10-12. Result: the workspace gate passes with the `.4` fork and a loopback release
channel. The actual collection branch remains to be published and checked.

## Inputs and versions

| Item | Value |
| --- | --- |
| Fork | `devenv 2.4.0+c66ba87` |
| Host launcher | Built from the current Vendomat flake |
| Testee | `0.6.1` |
| Testee PATH | `.4` fork directory first |
| Nix unsafe setting | `allow-unsafe-native-code-during-evaluation = false` |
| Gate | `testee verify front-door-e2e` |
| Raw logs | `~/.local/state/vendomat/p20/2026-10-12/slice-1/F-front-door/` |

## Observations

- `vendomat new` copied `vendomat.yaml`, `devenv.yaml`, `devenv.nix`, and `.gitignore`.
- The new workspace entered the shell. Its lock pinned the initial commit of the `release` branch.
- Creating, editing, and deleting `vendomat.yaml` changed the next shell without another setup
  command. A fresh clone and `direnv` saw the same catalog values.
- A moved `release` branch stayed locked until `devenv update vendomat`. The update selected the
  new source. Restoring the earlier `devenv.lock` restored the earlier shell.
- Testee verified the consumer with the fork first on `PATH`.

## Commands and results

| Command | Expected | Actual | Log |
| --- | --- | --- | --- |
| `vendomat new DIR` | Create a fixed workspace | Four expected files | `vendomat-new.log` |
| `.4 devenv --no-tui shell` | Enter the new workspace | Exit 0; lock pins local `release` | `shell-created.log` |
| `.4 devenv shell` after file create/edit/delete | Read current file contents | All values changed as expected | `file-missing.log`, `file-create.log`, `file-edit.log`, `file-delete.log` |
| `direnv exec DIR ...` | Read current workspace values | New workspace and clone both saw `one:3.10` | `direnv-new.log`, `direnv-clone.log` |
| `git clone DIR CLONE`, then `.4 devenv shell` | Enter the cloned workspace | Clone saw `one:3.10` | `workspace-clone.log`, `clone-shell.log` |
| `testee verify` in the consumer | Use the fork evaluator | GREEN | `testee-green.log` |

The test changed only the Vendomat source URL in the throwaway workspace to a local `git://`
server. The repository template still contains `git://server/vendomat?ref=release`. That URL has
not been tested against the collection yet.
