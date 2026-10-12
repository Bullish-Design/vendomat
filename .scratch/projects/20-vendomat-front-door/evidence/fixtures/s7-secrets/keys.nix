# NON-PRODUCTION fixture for spike S7. Generates TEST-ONLY ssh key pairs at build time.
# The private keys land in the Nix store. Never reuse them anywhere.
pkgs:
pkgs.runCommand "s7-test-keys" { nativeBuildInputs = [ pkgs.openssh ]; } ''
  mkdir $out
  for n in admin installer wrong; do
    ssh-keygen -q -t ed25519 -N "" -C "s7-test-only-$n" -f $out/$n
  done
''
