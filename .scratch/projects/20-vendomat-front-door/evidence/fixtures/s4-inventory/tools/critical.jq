# NON-PRODUCTION spike fixture (project 20, spike S4). Reads the JSON that audit.nix writes.
def under($p): select(.path == $p or (.path|startswith($p + ".")));
def rk: if .=="data" then 0 elif .=="reference" then 1 elif .=="untyped" then 2 else 3 end;
. as $all
| $prefixes | map(. as $p | [ $all[] | under($p) | select(.cls!="container") ] as $e
  | { prefix: $p, n: ($e|length),
      data: ([$e[]|select(.cls=="data")]|length), ref: ([$e[]|select(.cls=="reference")]|length),
      untyped: ([$e[]|select(.cls=="untyped")]|length), nodata: ([$e[]|select(.cls=="nodata")]|length),
      bad: ([$e[]|select(.cls=="untyped" or .cls=="nodata")|.path]|.[:6]),
      own: ([ $all[] | select(.path==$p) | .chain ]|first) })
