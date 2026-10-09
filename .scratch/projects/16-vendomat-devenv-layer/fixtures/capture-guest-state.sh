#!/usr/bin/env bash
# Read-only guest state capture. Never run on Framework or server.
set -euo pipefail
[[ "${VENDOMAT_VM_GUEST:-}" == "1" && -f /etc/vendomat-vm-adoption-marker ]] || {
  echo 'Refusing: this must run inside the disposable adoption fixture VM' >&2
  exit 64
}
printf '%s\n' '=== TOOL VERSIONS ==='
for exe in nix lsblk findmnt sfdisk sha256sum bootctl systemctl; do
  command -v "$exe" || :
done
nix --version
uname -a
printf '%s\n' '=== PARTITIONS ==='
lsblk --json --bytes --output NAME,PATH,TYPE,SIZE,PTTYPE,PARTUUID,UUID,FSTYPE,MOUNTPOINTS
printf '%s\n' '=== MOUNTS ==='
findmnt --json --output TARGET,SOURCE,FSTYPE,OPTIONS
printf '%s\n' '=== BOOT AND PROFILE ==='
readlink -f /run/current-system
readlink -f /nix/var/nix/profiles/system
find /nix/var/nix/profiles -maxdepth 1 -name 'system-*-link' -printf '%f %l\n' | LC_ALL=C sort
printf '%s\n' '=== FILES / HASHES ==='
for file in /var/lib/adoption-fixture/document.bin /home/tester/adoption-fixture.txt /etc/vendomat-vm-adoption-marker; do
  test -f "$file" || { echo "MISSING: $file"; continue; }
  stat --printf='%n owner=%u:%g mode=%a size=%s\n' "$file"
  sha256sum "$file"
done
printf '%s\n' '=== FAILED UNITS ==='
systemctl --failed --no-pager --no-legend || :
printf '%s\n' '=== ESP FILES ==='
find /boot -type f \( -path '*/EFI/*' -o -path '*/loader/entries/*' \) -print0 | sort -z | xargs -0 -r sha256sum
