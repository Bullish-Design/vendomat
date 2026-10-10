# Stand-in preflight program for the devenv distribution fixture. It is a
# minimal reference for the `vendomat.preflight/v1` contract. It checks only
# the disks it receives. The Vendomat Python preflight replaces it.
PATH=/run/current-system/sw/bin:$PATH
set -u
machine=""; nonce=""; phases=""; mode=""; disks=""
while [ $# -gt 0 ]; do
  case "$1" in
    --machine) machine=$2; shift 2 ;;
    --nonce) nonce=$2; shift 2 ;;
    --phases) phases=$2; shift 2 ;;
    --disko-mode) mode=$2; shift 2 ;;
    --disk) disks="$disks $2"; shift 2 ;;
    *) echo "preflight: unknown argument $1" >&2; exit 2 ;;
  esac
done
[ -n "$machine" ] && [ -n "$nonce" ] && [ -n "$disks" ] || { echo "preflight: missing argument" >&2; exit 2; }

# A run record on the target. The fixture reads it to prove that the program ran.
printf '%s %s %s\n' "$(date +%s)" "$machine" "$nonce" >> /var/log/vendomat-preflight.log 2>/dev/null || true
machine_id=$(cat /etc/machine-id)
boot_id=$(cat /proc/sys/kernel/random/boot_id)
overall=pass
checks=""
disk_json=""
sep=""

add_check() { # id status detail
  checks="$checks$sep_c{\"id\":\"$1\",\"status\":\"$2\",\"detail\":\"$3\"}"
  sep_c=","
  [ "$2" = pass ] || overall=fail
}
sep_c=""

for disk in $disks; do
  if [ ! -b "$disk" ]; then
    add_check "disk-present" fail "$disk is not a block device"
    continue
  fi
  real=$(readlink -f "$disk")
  base=${real##*/}
  size=$(blockdev --getsize64 "$real")
  serial=$(cat "/sys/block/$base/serial" 2>/dev/null || echo unknown)
  model=$(cat "/sys/block/$base/device/model" 2>/dev/null || echo virtio)
  disk_json="$disk_json$sep{\"by_id\":\"$disk\",\"model\":\"$model\",\"serial\":\"$serial\",\"size_bytes\":$size}"
  sep=","
  add_check "disk-present" pass "$disk"
  if [ -z "$(wipefs --no-act "$real" 2>/dev/null)" ] && [ -z "$(blkid -p "$real" 2>/dev/null)" ]; then
    add_check "blank-signature" pass "no signature on $disk"
  else
    add_check "blank-signature" fail "signature found on $disk"
  fi
  if findmnt -rn -S "$real" >/dev/null 2>&1 || lsblk -rno MOUNTPOINT "$real" | grep -q .; then
    add_check "not-mounted" fail "$disk or a partition is mounted"
  else
    add_check "not-mounted" pass "$disk is not mounted"
  fi
done
if findmnt -rn /mnt >/dev/null 2>&1; then
  add_check "mnt-free" fail "something is mounted at /mnt"
else
  add_check "mnt-free" pass "nothing at /mnt"
fi

printf '{"schema":"vendomat.preflight/v1","result":"%s","machine":"%s","nonce":"%s",' "$overall" "$machine" "$nonce"
printf '"host":{"machine_id":"%s","boot_id":"%s"},' "$machine_id" "$boot_id"
printf '"disks":[%s],"checks":[%s]}\n' "$disk_json" "$checks"
[ "$overall" = pass ]
