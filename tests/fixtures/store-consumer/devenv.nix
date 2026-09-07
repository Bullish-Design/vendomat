# The consumer side of the Face D fixture.
#
# It declares NO manager anywhere: no repoman.lock, no `uv add gitman`, nothing in
# pyproject.toml. The commands arrive as a Nix closure on PATH. That absence IS the
# thing under test — CONCEPT 03 §7 asks that the consumer's venv contain neither the
# manager distributions nor their console-script wrappers.
{ ... }:

{
  repoman.enable = true;
  repoman.managers = [ "copy" ];

  # Face D. `enable` already defaults to true once vendomat is imported (sub-phase 4);
  # stated here because a fixture should not rely on a default it exists to verify.
  vendor.toolchain.enable = true;
  vendor.toolchain.mode = "store";

  # A venv, so the test can look inside one and find no managers. Its only job is to
  # host an application's own dependencies — of which this fixture has none.
  languages.python = {
    enable = true;
    version = "3.13";
    venv.enable = true;
    uv.enable = true;
  };
}
