# Strict YAML subset parser in pure Nix (builtins only). Descends from the Rust primop `vendomatFromYAML`
# (devenv fork patch 0009). Parser v3 of the project 21 spike, plus a nesting limit and value positions. Block maps, block lists (of strings, maps, and lists), plain / "double" /
# 'single' scalars, comments. Every scalar stays a string. Errors read FILE:LINE:COL: reason.
# Indentation is the leading run of spaces and tabs. The parser compares it as a string, with no tab width.
# A compact item (`- key: v`, `- - x`) opens a block. The block indentation is one of two strings:
# the item indentation plus one space for the `-` and one for each space after it (the space form), or the item
# indentation plus one tab (the tab form). The first line after the item line fixes the form. The other
# continuation lines of the item must then use the same string. A nested compact item does the same at its depth.
# A column counts characters. A tab counts as one column.
# A child block must extend the parent string. Siblings must match exactly. A dedent must land on an open level.
# Else the error reads "unexpected indentation" (deeper row, or only spaces) or "inconsistent tabs and spaces".
# Only spaces separate `-` and `:` from what follows. A tab in a plain or quoted value stays text.
# A plain map value must not start with `- ` or be `-`: a list starts on the next line.
#
# Use: `(import ./parse.nix) "vendomat.yaml" text`. The first argument is the file name for the error
# lines. The call returns an attribute set:
#   value      The parsed tree: maps, lists, and text.
#   positions  The side table of positions (see below). Nothing forces it until a caller reads it.
#   at         `at PATH` returns { key; value; } for a key path, or null. PATH is a list of text: the map
#              keys, and "[N]" for item N of a list (counted from 0). `key` is the position of the key (the
#              dash for a list item). `value` is the position of the text of a scalar. For a map or a list
#              the value position equals the key position. A position is "LINE:COL", like in an error line.
# The side table `positions` is a tree. Each entry is { key; value; sub; }. `sub` holds the entries of the
# children of a map or a list.
#
# Nesting limit: a file may nest maps and lists up to 64 levels. The top map is level 1. A deeper
# file fails with `FILE:LINE:COL: nesting deeper than 64 levels` at its first row of level 65. Nix would
# overflow its stack at about 800 levels, with an error that names no file (VMT-013).
file: text:
let
  inherit (builtins) elem elemAt length match stringLength substring split filter isString isList head tail
    genList foldl' seq fromJSON toJSON tryEval concatLists;

  fail = n: c: why: throw "${file}:${toString n}:${toString c}: ${why}";
  maxDepth = 64;
  loc = n: c: "${toString n}:${toString c}"; # a position, "LINE:COL"

  # --- Characters. Nix strings hold bytes; the parser counts Unicode characters in columns.
  u = hex: fromJSON ''"\u${hex}"'';
  cont = "[${substring 1 1 (u "0080")}-${substring 1 1 (u "00bf")}]"; # UTF-8 continuation bytes
  clen = s: stringLength s - length (filter isList (split cont s));
  # White space for `trim`: the tab and the Rust `char::is_whitespace` set. The space is handled apart.
  wsToks = map u ([ "0009" "000b" "000c" "000d" "0085" "00a0" "1680" "2028" "2029" "202f" "205f" "3000" ]
    ++ genList (i: "200${substring i 1 "0123456789a"}") 11);
  hasAt = s: off: t: off >= 0 && substring off (stringLength t) s == t;
  # A run of spaces is counted with `split`, which does not recurse. Other white space is rare.
  trimEnd = s:
    let
      pieces = split "[^ ]" s;
      s1 = substring 0 (stringLength s - stringLength (elemAt pieces (length pieces - 1))) s;
      n = stringLength s1;
      hit = filter (t: hasAt s1 (n - stringLength t) t) wsToks;
    in
    if hit == [ ] then s1 else trimEnd (substring 0 (n - stringLength (head hit)) s1);
  trimStart = s:
    let
      s1 = substring (spaces s) (stringLength s) s;
      hit = filter (t: hasAt s1 0 t) wsToks;
    in
    if hit == [ ] then s1 else trimStart (substring (stringLength (head hit)) (stringLength s1) s1);
  trim = s: trimStart (trimEnd s);
  spaces = s: stringLength (head (split "[^ ]" s)); # count of leading spaces
  hasTab = s: length (split "\t" s) > 1;

  # Indentation strings. `isPre a b`: `a` is a proper prefix of `b` (`b` is a deeper level than `a`).
  isPre = a: b: stringLength a < stringLength b && substring 0 (stringLength a) b == a;

  # --- Scalars (defined first: the row scan uses `quoted`)
  badStart = {
    "&" = "anchors (&) are not accepted";
    "*" = "aliases (*) are not accepted";
    "!" = "tags (!) are not accepted";
    "[" = "flow style is not accepted";
    "{" = "flow style is not accepted";
    "|" = "block scalars are not accepted; use one quoted line";
    ">" = "block scalars are not accepted; use one quoted line";
  };

  # Read a quoted text at the start of `s`. `c` is the column of the opening quote.
  # Result: { value; end }. `end` is the byte offset after the closing quote.
  quoted = n: c: s:
    let
      single = substring 0 1 s == "'";
      toks = split (if single then "('')|(')" else ''(\\(.${cont}*)?)|(")'') (substring 1 (stringLength s) s);
      escapes = { "\"" = "\""; "\\" = "\\"; n = "\n"; t = "\t"; };
      # Walk the tokens: text, match, text, match, ... Stop at the closing quote.
      step = st: k:
        if st.end != null then st
        else
          let
            seg = elemAt toks (2 * k); g = elemAt toks (2 * k + 1);
            upto = st.used + stringLength seg;
            close = st // { value = st.acc + seg; end = upto + 1; };
            e = elemAt g 1;
            r = if e == null then null else escapes.${e} or null;
          in
          if single then
            (if elemAt g 0 != null then st // { acc = st.acc + seg + "'"; used = upto + 2; } else close)
          else if elemAt g 2 != null then close
          else if r == null then fail n (c + clen (substring 0 upto s)) "escape \\${if e == null then "" else e} is not accepted"
          else st // { acc = st.acc + seg + r; used = upto + stringLength (elemAt g 0); };
      done = foldl' step { acc = ""; used = 1; end = null; } (genList (k: k) (length toks / 2));
    in
    if done.end == null then fail n c "the quoted string does not end on this line" else done;

  scalar = n: c: s:
    let
      ch = substring 0 1 s;
      plain = trimEnd (head (split " #" s));
    in
    if ch == "\"" || ch == "'" then
      let q = quoted n c s; rest = trim (substring q.end (stringLength s) s); in
      if rest != "" && substring 0 1 rest != "#" then fail n (c + clen (substring 0 q.end s)) "text after the closing quote"
      else q.value
    else if badStart ? ${ch} then fail n c badStart.${ch}
    else if elem ch [ "%" "@" "`" "," "]" "}" "?" ] then fail n c "'${ch}' cannot start a value; quote the text"
    else if length (split ": " plain) > 1 || hasAt plain (stringLength plain - 1) ":"
    then fail n (c + clen (head (split ":" plain))) "a colon inside a plain value; quote the text"
    else plain;

  isKey = k: k != "" && match "[A-Za-z_]" (substring 0 1 k) != null && length (split "[^A-Za-z0-9_.-]" k) == 1;
  isItem = s: s == "-" || hasAt s 0 "- ";
  # A plain map value that starts like a list item.
  dashValue = body: let p = trimEnd (head (split " #" body)); in p == "-" || hasAt p 0 "- ";

  # Does `s` (the text after `- `) start a map entry? A key is quoted or plain, and the colon is followed by a
  # space or the end. A quoted key is also accepted with any text after the colon; the map reader then
  # reports the missing space. A bad quoted text is no key: the scalar reader reports it later, in order.
  startsEntry = s:
    let
      ch = substring 0 1 s;
      q = tryEval (let r = quoted 0 0 s; in seq r.end (seq r.value r));
      bare = head (split ":" s);
      nxt = substring (stringLength bare + 1) 1 s;
    in
    if ch == "\"" || ch == "'" then q.success && hasAt s q.value.end ":"
    else isKey bare && hasAt s (stringLength bare) ":" && (nxt == "" || nxt == " ");

  # --- Rows. Scan every line first (document markers), then keep the non-blank, non-comment ones.
  # A row is { line; ind; off; text }. `ind` is the indentation string. `off` is the count of characters
  # before `text`. A compact item turns into a marker row `-` plus the rows of what follows the `- `.
  # The rows after the marker sit at the block indentation of the item (the blocks nest as for a bare item).
  # `toJSON` fails on bytes that are not UTF-8. The primop rejects such a file too.
  lines = seq (toJSON text) (filter isString (split "\n" text));
  # `nxt` is the indentation of the next code line, or null. It fixes the form of a compact item (see the header).
  expand = n: ind: off: s: nxt:
    let
      after = substring 1 (stringLength s) s;
      skip = spaces after;
      rest = substring skip (stringLength after) after;
      sp = ind + " " + substring 0 skip after;
      tab = ind + "\t";
      near = x: nxt != null && (nxt == x || isPre x nxt);
      ind' = if near tab then tab else sp;
      off' = off + 1 + skip;
      here = { line = n; inherit ind off; text = s; };
    in
    if !isItem s || rest == "" || substring 0 1 rest == "#" then [ here ]
    else if isItem rest || startsEntry rest
    then [ (here // { text = "-"; }) ] ++ expand n ind' off' rest nxt
    else [ here ];
  lineInfo = idx: raw:
    let
      n = idx + 1;
      l = if hasAt raw (stringLength raw - 1) "\r" then substring 0 (stringLength raw - 1) raw else raw;
      ind = head (split "[^ \t]" l);
      off = stringLength ind;
      s = substring off (stringLength l) l;
      t = trim l;
    in
    if (hasAt l 0 "---" || hasAt l 0 "...") && (t == "---" || t == "...")
    then fail n 1 "document markers are not accepted; one document per file"
    else if s == "" || substring 0 1 s == "#" then null
    else { line = n; inherit ind off; text = s; };
  infos = genList (i: lineInfo i (elemAt lines i)) (length lines);
  code = seq (foldl' (_: x: seq (x == null) null) null infos) (filter (x: x != null) infos);
  rows = concatLists (genList
    (k: let c = elemAt code k; in expand c.line c.ind c.off c.text (if k + 1 < length code then (elemAt code (k + 1)).ind else null))
    (length code));
  m = length rows;
  at = i: elemAt rows i;

  # --- Blocks. Each function returns { value; next }. `next` is the index of the next row.
  # A loop over the rows of one block is a `genericClosure` chain. It keeps the Nix stack shallow:
  # the call depth follows the nesting of the file, not its length. A step forces its value into
  # `key`, so the errors come in file order.
  loop = more: step: init:
    let r = builtins.genericClosure { startSet = [ init ]; operator = st: if more st then [ (step st) ] else [ ]; }; in
    elemAt r (length r - 1);

  # A block `ind` ends at row `nxt`, whose indentation is not `ind`. A deeper row is an error. A shallower
  # row ends the block: the parent decides. The parent fails when the row is not one of its own levels.
  # A row that follows a deeper block and sits between two levels, or that does not extend or shorten
  # `ind`, reads "inconsistent tabs and spaces" when a tab is in the row or in the row before it.
  stop = nxt: ind:
    if nxt >= m then null
    else
      let
        r = at nxt; x = r.ind; prev = (at (nxt - 1)).ind;
        bad = why: fail r.line (r.off + 1) why;
      in
      if isPre ind x then
        (if prev == ind || !(hasTab x || hasTab prev) then bad "unexpected indentation" else bad "inconsistent tabs and spaces")
      else if isPre x ind then null
      else bad "inconsistent tabs and spaces";

  # `d` is the level of the block. The top map is level 1.
  block = i: ind: d:
    if d > maxDepth then fail (at i).line ((at i).off + 1) "nesting deeper than ${toString maxDepth} levels"
    else if isItem (at i).text then list i ind d
    else mapping i ind d;

  # The block under a key or an item at level `d`. Result: { value; next; pos } like a block.
  child = i: ind: n: c: d:
    if i < m && isPre ind (at i).ind then block i (at i).ind (d + 1)
    else if i < m && (at i).ind != ind && !(isPre (at i).ind ind) then fail (at i).line ((at i).off + 1) "inconsistent tabs and spaces"
    else fail n c ''no value; write "" for an empty text'';

  # A loop over the rows of a list. `acc` holds the items, `pos` the entries of the side table.
  list = i: ind: d:
    let
      more = st: st.key < m && (at st.key).ind == ind;
      step = st:
        let
          i' = st.key; r = at i'; s = r.text; n = r.line; c = r.off;
          after = substring 1 (stringLength s) s;
          skip = spaces after;
          rest = substring skip (stringLength after) after;
          name = "[${toString (length st.acc)}]";
          here = loc n (c + 1);
          push = value: nxt: vpos: sub: {
            key = seq value nxt;
            acc = st.acc ++ [ value ];
            pos = st.pos // { ${name} = { key = here; value = vpos; inherit sub; }; };
          };
        in
        if !isItem s then fail n (c + 1) "expected a list item"
        else if rest == "" || substring 0 1 rest == "#" then
          let v = child (i' + 1) ind n (c + 1) d; in push v.value v.next here v.pos
        else push (scalar n (c + 2 + skip) rest) (i' + 1) (loc n (c + 2 + skip)) { };
      done = loop more step { key = i; acc = [ ]; pos = { }; };
    in
    seq (stop done.key ind) { value = done.acc; next = done.key; pos = done.pos; };

  mapping = i: ind: d:
    let
      more = st: st.key < m && (at st.key).ind == ind;
      step = st:
        let
          i' = st.key; r = at i'; s = r.text; n = r.line; c = r.off;
          ch = substring 0 1 s;
          isQ = ch == "\"" || ch == "'";
          q = quoted n (c + 1) s;
          bare = head (split ":" s);
          key = if isQ then q.value else bare;
          keyEnd = if isQ then q.end else stringLength bare; # byte offset of the colon
          after = substring (keyEnd + 1) (stringLength s) s;
          skip = spaces after;
          body = substring skip (stringLength after) after;
          bodyCol = c + 1 + clen (substring 0 (stringLength s - stringLength body) s); # column of the value text
          here = loc n (c + 1);
          put = value: nxt: vpos: sub: {
            key = seq value nxt;
            acc = st.acc // { ${key} = value; };
            seen = st.seen // { ${key} = n; };
            pos = st.pos // { ${key} = { key = here; value = vpos; inherit sub; }; };
          };
        in
        if isQ && !(hasAt s q.end ":") then fail n (c + 1 + clen (substring 0 q.end s)) "expected ':' after the key"
        else if !isQ && (!isKey bare || !(hasAt s keyEnd ":")) then
          (if elem ch [ "&" "*" "!" "[" "{" ] then fail n (c + 1) badStart.${ch}
           else if ch == "-" then fail n (c + 1) "list item where a key was expected"
           else fail n (c + 1) "expected 'key: value'")
        else if after != "" && substring 0 1 after != " " then fail n (c + 1) "expected a space after ':'"
        else if st.seen ? ${key} then fail n (c + 1) "duplicate key '${key}'; first on line ${toString st.seen.${key}}"
        else if body == "" || substring 0 1 body == "#" then
          let v = child (i' + 1) ind n (c + 1 + clen (substring 0 (keyEnd + 1) s)) d; in put v.value v.next here v.pos
        else if dashValue body then fail n bodyCol "a list must start on the next line"
        else put (scalar n bodyCol body) (i' + 1) (loc n bodyCol) { };
      done = loop more step { key = i; acc = { }; seen = { }; pos = { }; };
    in
    seq (stop done.key ind) { value = done.acc; next = done.key; pos = done.pos; };

  # --- File
  top =
    if m == 0 then { value = { }; pos = { }; }
    else
      let r = at 0; in
      if r.ind != "" then fail r.line (r.off + 1) "unexpected indentation"
      else if isItem r.text then fail r.line 1 "the file must be a map"
      else mapping 0 "" 1;

  # The entry of the side table for a key path, or null.
  entryAt = path:
    if path == [ ] then null
    else (foldl' (e: seg: if e == null then null else e.sub.${seg} or null) { sub = top.pos; } path);
in
{
  value = top.value;
  positions = top.pos;
  at = entryAt;
}
