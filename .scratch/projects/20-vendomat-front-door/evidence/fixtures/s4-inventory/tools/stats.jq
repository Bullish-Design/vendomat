# NON-PRODUCTION spike fixture (project 20, spike S4). Reads the JSON that audit.nix writes.
def settable: select((.internal|not) and (.readOnly|not) and (.visible != false));
def counts(f): [ .[] | f ] | group_by(.cls) | map({key:.[0].cls, value:length}) | from_entries;
def cause: if .cls == "data" or .cls == "reference" or .cls=="container" then "-"
  elif (.chain|test("functionTo|function")) then "function"
  elif (.chain|test("deferredModule")) then "deferredModule"
  elif (.chain|test("optionType")) then "optionType"
  elif (.chain|test("Toplevel|nixpkgs-(config|overlay)")) then "module/config/overlay"
  elif (.chain|test("raw")) then "raw"
  elif (.chain|test("unspecified")) then "unspecified"
  elif (.chain|test("anything")) then "anything"
  elif (.chain|test("attrs")) then "attrs (untyped attrset)"
  elif (.chain|test("unknown")) then "unknown" else "other:" + .chain end;
{
 total: length,
 containers: (map(select(.cls=="container"))|length),
 leaves: (map(select(.cls!="container"))|length),
 leaf_counts: (map(select(.cls!="container"))|counts(.)),
 settable_leaf_counts: (map(select(.cls!="container")|settable)|counts(.)),
 causes: (map(select(.cls=="untyped" or .cls=="nodata")|{cls, c:cause})|group_by(.cls+"/"+.c)|map({k:(.[0].cls+"/"+.[0].c), n:length})|sort_by(-.n)),
 settable_causes: (map(select(.cls=="untyped" or .cls=="nodata")|settable|{cls, c:cause})|group_by(.cls+"/"+.c)|map({k:(.[0].cls+"/"+.[0].c), n:length})|sort_by(-.n))
}
