# S5 fixture, NON-PRODUCTION.
# S5 fixture. A tiny imported module from a flake:false path input.
{ ... }: { env.S5_TOOLS_MOD = "loaded"; }
