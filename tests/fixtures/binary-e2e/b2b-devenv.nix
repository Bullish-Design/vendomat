{ inputs, ... }:
{
  env.A_DATA = builtins.readFile "${inputs.a}/data.txt";
  env.B_DATA = builtins.readFile "${inputs.b}/data.txt";
}
