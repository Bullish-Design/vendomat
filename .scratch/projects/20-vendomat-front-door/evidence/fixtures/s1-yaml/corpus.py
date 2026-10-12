# NON-PRODUCTION spike fixture (project 20, spike S1).
# Corpus of accepted and rejected `vendomat.yaml` inputs.
# ACCEPT: (id, description, input, expected tree)
# REJECT: (id, description, input, expected code, line, col)   line and col are 1-based.
# `input` is str (encoded UTF-8) or bytes. `[` `]` `{` `}` inside are plain test text.

ACCEPT = []
REJECT = []


def a(id_, desc, text, tree):
    ACCEPT.append((id_, desc, text, tree))


def r(id_, desc, text, code, line, col):
    REJECT.append((id_, desc, text, code, line, col))


# ------------------------------------------------------------------ accepted
a("A01", "CONCEPT section 3 example", """\
inputs:
  tools:
    url: "git://collection.example/tools?ref=refs/tags/v1.0.0"
imports:
  - "tools/devenv"
packages:
  - "ripgrep"
basix:
  machines:
    laptop:
      mode: "adopt-existing"
      disks:
        system:
          byId: "/dev/disk/by-id/example-id"
          role: "existing-system"
""", {
    "inputs": {"tools": {"url": "git://collection.example/tools?ref=refs/tags/v1.0.0"}},
    "imports": ["tools/devenv"],
    "packages": ["ripgrep"],
    "basix": {"machines": {"laptop": {"mode": "adopt-existing", "disks": {"system": {
        "byId": "/dev/disk/by-id/example-id", "role": "existing-system"}}}}},
})
a("A02", "empty file", "", {})
a("A03", "comments and blank lines only", "# a comment\n\n   # indented comment\n\n", {})
a("A04", "scalar kinds", 'name: "x"\ncount: 3\non_flag: true\noff_flag: false\nnothing: null\n',
  {"name": "x", "count": 3, "on_flag": True, "off_flag": False, "nothing": None})
a("A05", "integer edges", "zero: 0\nneg: -7\nmax: 9223372036854775807\nmin: -9223372036854775808\n",
  {"zero": 0, "neg": -7, "max": 9223372036854775807, "min": -9223372036854775808})
a("A06", "version strings stay strings when quoted", 'python: "3.10"\nother: "3.1"\nnode: "22"\n',
  {"python": "3.10", "other": "3.1", "node": "22"})
a("A07", "Norway problem words quoted", 'country: "NO"\nanswer: "no"\nflag: "yes"\nswitch: "on"\nnull_text: "null"\ntilde: "~"\n',
  {"country": "NO", "answer": "no", "flag": "yes", "switch": "on", "null_text": "null", "tilde": "~"})
a("A08", "quoted keys with dots and slashes", '''\
scripts:
  "my.script":
    exec: "echo hi"
files:
  ".config/foo.json":
    text: "{}"
''', {"scripts": {"my.script": {"exec": "echo hi"}}, "files": {".config/foo.json": {"text": "{}"}}})
a("A09", "single-quoted strings", "a: 'it''s'\nb: 'back\\slash'\nc: 'say \"hi\"'\nd: ''\n",
  {"a": "it's", "b": "back\\slash", "c": 'say "hi"', "d": ""})
a("A10", "double-quoted escapes", r'''a: "line\nbreak"
b: "tab\there"
c: "q\"uote"
d: "back\\slash"
e: "\u00e9\/"
f: "cr\rx"
''', {"a": "line\nbreak", "b": "tab\there", "c": 'q"uote', "d": "back\\slash", "e": "é/", "f": "cr\rx"})
a("A11", "literal unicode", 'greeting: "héllo wörld"\nemoji: "ok \U0001F600"\ncjk: "日本語"\n',
  {"greeting": "héllo wörld", "emoji": "ok \U0001F600", "cjk": "日本語"})
a("A12", "empty list and empty map", "packages: []\nenv: {}\nnested:\n  list: []\n  map: {}\n",
  {"packages": [], "env": {}, "nested": {"list": [], "map": {}}})
a("A13", "indented block list", 'packages:\n  - "a"\n  - "b"\n  - 3\n  - true\n  - null\n',
  {"packages": ["a", "b", 3, True, None]})
a("A14", "list at the indent of its key", 'packages:\n- "a"\n- "b"\nafter: 1\n',
  {"packages": ["a", "b"], "after": 1})
a("A15", "list of maps (postgres initialDatabases)", '''\
services:
  postgres:
    enable: true
    initialDatabases:
      - name: "app"
        user: "app"
      - name: "other"
''', {"services": {"postgres": {"enable": True, "initialDatabases": [{"name": "app", "user": "app"}, {"name": "other"}]}}})
a("A16", "list of lists", 'm:\n  - - "a"\n    - "b"\n  - - 1\n', {"m": [["a", "b"], [1]]})
a("A17", "block scalar | for enterShell", '''\
enterShell: |
  echo "welcome"
  export FOO=bar
  if [ -n "$X" ]; then
    echo "x"
  fi
''', {"enterShell": 'echo "welcome"\nexport FOO=bar\nif [ -n "$X" ]; then\n  echo "x"\nfi\n'})
a("A18", "block scalar |- strips the final newline", "text: |-\n  one\n  two\n", {"text": "one\ntwo"})
a("A19", "block scalar with blank lines, hash, colon, tab, trailing spaces", "text: |\n  # not a comment\n\n  key: value\n\tTAB-start\n  mid\ttab  \n\n\nnext: 1\n".replace("\n\tTAB-start", "\n  \tTAB-start"),
  {"text": "# not a comment\n\nkey: value\n\tTAB-start\nmid\ttab  \n", "next": 1})
a("A20", "block scalar as list item", "cmds:\n  - |\n    echo one\n    echo two\n  - \"plain\"\n", {"cmds": ["echo one\necho two\n", "plain"]})
a("A21", "block scalar in a list of maps", '''\
tasks:
  - name: "build"
    exec: |
      make
      make install
  - name: "test"
    exec: "make test"
''', {"tasks": [{"name": "build", "exec": "make\nmake install\n"}, {"name": "test", "exec": "make test"}]})
a("A22", "comments in all positions", '''\
# top
a: 1 # trailing
b: "x # not a comment"
c: # after key
  d: 2
  # between
  e: 3
list: # after key
  - 1 # item
''', {"a": 1, "b": "x # not a comment", "c": {"d": 2, "e": 3}, "list": [1]})
a("A23", "comment after block header", "t: | # note\n  body\n", {"t": "body\n"})
a("A24", "blank lines between entries", "a: 1\n\n\nb:\n\n  c: 2\n\n", {"a": 1, "b": {"c": 2}})
a("A26", "mixed indent widths in different maps", "a:\n    b: 1\nc:\n  d: 2\n", {"a": {"b": 1}, "c": {"d": 2}})
a("A27", "deep nesting", "a:\n b:\n  c:\n   d:\n    e:\n     f:\n      g:\n       h: 1\n", {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": 1}}}}}}}})
a("A28", "plain keys with hyphen and underscore", "nixpkgs-python: 1\n_private: 2\nA_b-c9: 3\n", {"nixpkgs-python": 1, "_private": 2, "A_b-c9": 3})
a("A29", "realistic devenv workspace", '''\
languages:
  python:
    enable: true
    version: "3.13"
    uv:
      enable: true
packages:
  - "ripgrep"
  - "python313Packages.requests"
env:
  GREET: "hello"
enterShell: |
  echo "ready"
scripts:
  hello:
    exec: |
      echo hello
processes:
  web:
    exec: "python -m http.server 8000"
services:
  postgres:
    enable: true
    port: 5432
    initialDatabases:
      - name: "app"
        user: "app"
''', {
    "languages": {"python": {"enable": True, "version": "3.13", "uv": {"enable": True}}},
    "packages": ["ripgrep", "python313Packages.requests"],
    "env": {"GREET": "hello"},
    "enterShell": 'echo "ready"\n',
    "scripts": {"hello": {"exec": "echo hello\n"}},
    "processes": {"web": {"exec": "python -m http.server 8000"}},
    "services": {"postgres": {"enable": True, "port": 5432, "initialDatabases": [{"name": "app", "user": "app"}]}},
})
a("A30", "Basix fresh-install machine", '''\
basix:
  machines:
    desk:
      mode: "fresh-install"
      disks:
        system:
          byId: "/dev/disk/by-id/nvme-EXAMPLE_4TB_0001"
          role: "install-target"
        data:
          byId: "/dev/disk/by-id/ata-EXAMPLE_0002"
          role: "protected"
      swapGiB: 16
''', {"basix": {"machines": {"desk": {"mode": "fresh-install", "disks": {
    "system": {"byId": "/dev/disk/by-id/nvme-EXAMPLE_4TB_0001", "role": "install-target"},
    "data": {"byId": "/dev/disk/by-id/ata-EXAMPLE_0002", "role": "protected"}}, "swapGiB": 16}}}})
a("A31", "path-looking strings stay strings", 'a: "./scripts/x.sh"\nb: "/abs/path"\nc: "../up"\nd: "~/home"\n',
  {"a": "./scripts/x.sh", "b": "/abs/path", "c": "../up", "d": "~/home"})
a("A32", "package attribute strings", 'packages:\n  - "python313Packages.requests"\n  - "nodePackages.typescript-language-server"\n  - "gnome-terminal"\n',
  {"packages": ["python313Packages.requests", "nodePackages.typescript-language-server", "gnome-terminal"]})
a("A33", "path option named passwordFile is not a secret value", 'services:\n  app:\n    passwordFile: "/run/secrets/db"\n    tokenFile: "/run/secrets/token"\n    hashedPasswordFile: "/run/secrets/h"\n',
  {"services": {"app": {"passwordFile": "/run/secrets/db", "tokenFile": "/run/secrets/token", "hashedPasswordFile": "/run/secrets/h"}}})
a("A34", "PasswordAuthentication boolean is not a secret", "services:\n  openssh:\n    settings:\n      PasswordAuthentication: false\n",
  {"services": {"openssh": {"settings": {"PasswordAuthentication": False}}}})
a("A35", "reserved words as quoted keys", '"true": 1\n"null": 2\n"no": 3\n"8080": "x"\n', {"true": 1, "null": 2, "no": 3, "8080": "x"})
a("A36", "empty strings", 'a: ""\nb: \'\'\n', {"a": "", "b": ""})
a("A37", "interpolation-looking and special text in quotes", 'a: "${HOME}/x"\nb: "k: v # w"\nc: "- not a list"\nd: "[1, 2]"\ne: "&anchor *alias !tag"\n',
  {"a": "${HOME}/x", "b": "k: v # w", "c": "- not a list", "d": "[1, 2]", "e": "&anchor *alias !tag"})
a("A38", "keys that differ by case", "a: 1\nA: 2\n", {"a": 1, "A": 2})
a("A39", "same key name in two maps", "x:\n  a: 1\ny:\n  a: 2\n", {"x": {"a": 1}, "y": {"a": 2}})
a("A40", "root map indented by two", "  a: 1\n  b:\n    c: 2\n", {"a": 1, "b": {"c": 2}})
a("A41", "trailing spaces before a comment and at line end", "a: 1   # c   \nb: \"x\"   \n", {"a": 1, "b": "x"})
a("A42", "block scalar with first line more indented", "t: |\n    deep\n  shallow\n".replace("    deep\n  shallow", "    deep\n    next\n      more"), {"t": "deep\nnext\n  more\n"})
a("A43", "empty block scalar", "t: |\nnext: 1\n", {"t": "", "next": 1})
a("A53", "block scalar of blank lines only", "t: |\n  \n\nnext: 1\n", {"t": "", "next": 1})
a("A44", "block scalar leading blank line", "t: |\n\n  body\n", {"t": "\nbody\n"})
a("A45", "unicode quoted key", '"ключ": 1\n', {"ключ": 1})
a("A46", "long string and long list", "s: \"" + "x" * 5000 + "\"\nl:\n" + "".join(f"  - {i}\n" for i in range(1000)), {"s": "x" * 5000, "l": list(range(1000))})
a("A47", "sequence of mixed nesting under list of maps", '''\
items:
  - id: 1
    tags:
      - "a"
      - "b"
    meta:
      k: "v"
  - id: 2
    tags: []
''', {"items": [{"id": 1, "tags": ["a", "b"], "meta": {"k": "v"}}, {"id": 2, "tags": []}]})
a("A48", "quoted-key list item map", 'l:\n  - "a.b": 1\n    "c d": 2\n', {"l": [{"a.b": 1, "c d": 2}]})
a("A49", "secret field set to null or empty is not a literal secret", 'services:\n  app:\n    password: null\n    token: ""\n',
  {"services": {"app": {"password": None, "token": ""}}})
a("A50", "imports with several inputs", '''\
inputs:
  tools:
    url: "git://collection.example/tools?ref=refs/tags/v1.0.0"
    flake: false
  lib:
    url: "git://collection.example/lib?ref=refs/tags/v2.3.1"
    inputs:
      nixpkgs:
        follows: "nixpkgs"
imports:
  - "tools/devenv"
  - "lib/devenv"
''', {"inputs": {"tools": {"url": "git://collection.example/tools?ref=refs/tags/v1.0.0", "flake": False},
                 "lib": {"url": "git://collection.example/lib?ref=refs/tags/v2.3.1", "inputs": {"nixpkgs": {"follows": "nixpkgs"}}}},
      "imports": ["tools/devenv", "lib/devenv"]})
a("A51", "double-quoted string with a literal # and ' and trailing comment", 'a: "it\'s #1" # real comment\n', {"a": "it's #1"})
a("A52", "block scalar contains --- and ... lines indented", "t: |\n  ---\n  ...\n  a: b\n", {"t": "---\n...\na: b\n"})

a("A54", "nesting 60 levels deep", "".join(" " * i + f"k{i}:\n" for i in range(60)) + " " * 60 + "v: 1\n", __import__("functools").reduce(lambda acc, i: {f"k{i}": acc}, range(59, -1, -1), {"v": 1}))

# ------------------------------------------------------------------ rejected
r("R01", "anchor on a scalar", "a: &x 1\n", "anchor", 1, 4)
r("R02", "anchor on a map", "base: &b\n  k: 1\n", "anchor", 1, 7)
r("R03", "alias", "a: &x 1\nb: *x\n", "anchor", 1, 4)  # first fault is the anchor
r("R04", "alias alone (no anchor first)", "b: *x\n", "alias", 1, 4)
r("R05", "tag !!str", "a: !!str 5\n", "tag", 1, 4)
r("R06", "custom tag", "a: !custom x\n", "tag", 1, 4)
r("R07", "flow list plain items", "a: [x, y]\n", "flow-collection", 1, 4)
r("R08", "flow list quoted items", 'a: ["x", "y"]\n', "flow-collection", 1, 4)
r("R09", "flow map", "a: {b: 1}\n", "flow-collection", 1, 4)
r("R10", "empty flow list with inner space", "a: [ ]\n", "flow-collection", 1, 4)
r("R11", "flow list inside list item", "a:\n  - [1, 2]\n", "flow-collection", 2, 5)
r("R12", "merge key", "base:\n  k: 1\nd:\n  <<: 1\n", "merge-key", 4, 3)
r("R13", "leading document marker", "---\na: 1\n", "document-marker", 1, 1)
r("R14", "second document", "a: 1\n---\nb: 2\n", "document-marker", 2, 1)
r("R15", "document end marker", "a: 1\n...\n", "document-marker", 2, 1)
r("R16", "YAML directive", "%YAML 1.2\n---\na: 1\n", "directive", 1, 1)
r("R17", "tab indentation", "a:\n\tb: 1\n", "tab", 2, 1)
r("R18", "tab after colon", "a:\t1\n", "tab", 1, 3)
r("R19", "byte order mark", b"\xef\xbb\xbfa: 1\n", "bom", 1, 1)
r("R20", "latin-1 byte, not UTF-8", b'a: "caf\xe9"\n', "not-utf8", 1, 8)
r("R21", "UTF-16 text", "a: 1\n".encode("utf-16"), "not-utf8", 1, 1)
r("R22", "CRLF line ends", "a: 1\r\nb: 2\r\n", "cr", 1, 5)
r("R23", "NUL character", b'a: "x\x00y"\n', "control-char", 1, 6)
r("R24", "ESC character", b'a: "x\x1by"\n', "control-char", 1, 6)
r("R25", "U+2028 inside a string", 'a: "x\u2028y"\n', "control-char", 1, 6)
r("R26", "U+0085 NEL inside a string", 'a: "x\u0085y"\n', "control-char", 1, 6)
r("R27", "U+FEFF inside a string", 'a: "x\ufeffy"\n', "control-char", 1, 6)
r("R28", "DEL character", b'a: "x\x7fy"\n', "control-char", 1, 6)
r("R29", "duplicate top-level key", "a: 1\nb: 2\na: 3\n", "duplicate-key", 3, 1)
r("R30", "duplicate nested key", "x:\n  y:\n    k: 1\n    k: 2\n", "duplicate-key", 4, 5)
r("R31", "duplicate key in a list item map", "l:\n  - a: 1\n    a: 2\n", "duplicate-key", 3, 5)
r("R32", "duplicate key, plain then quoted", 'a: 1\n"a": 2\n', "duplicate-key", 2, 1)
r("R33", "integer above int64", "a: 9223372036854775808\n", "int-range", 1, 4)
r("R34", "integer below int64", "a: -9223372036854775809\n", "int-range", 1, 4)
r("R35", "float 1.5", "a: 1.5\n", "float", 1, 4)
r("R36", "version 3.10 unquoted", "python: 3.10\n", "float", 1, 9)
r("R37", "exponent form 1e3", "a: 1e3\n", "float", 1, 4)
r("R38", "infinity", "a: .inf\n", "float", 1, 4)
r("R39", "not-a-number", "a: .nan\n", "float", 1, 4)
r("R40", "octal 0o12", "a: 0o12\n", "int-form", 1, 4)
r("R41", "hex 0x1F", "a: 0x1F\n", "int-form", 1, 4)
r("R42", "leading zero 012", "a: 012\n", "int-form", 1, 4)
r("R43", "plus sign +1", "a: +1\n", "int-form", 1, 4)
r("R44", "underscore 1_000", "a: 1_000\n", "int-form", 1, 4)
r("R45", "negative zero", "a: -0\n", "int-form", 1, 4)
r("R46", "yes", "a: yes\n", "implicit-string", 1, 4)
r("R47", "No (Norway)", "country: No\n", "implicit-string", 1, 10)
r("R48", "on", "a: on\n", "implicit-string", 1, 4)
r("R49", "True (capital)", "a: True\n", "implicit-string", 1, 4)
r("R50", "NULL (capital)", "a: NULL\n", "implicit-string", 1, 4)
r("R51", "tilde null", "a: ~\n", "null-form", 1, 4)
r("R52", "bare empty value", "a:\nb: 1\n", "empty-value", 1, 3)
r("R53", "bare empty value at end", "a:\n", "empty-value", 1, 3)
r("R54", "implicit string word", "a: hello\n", "implicit-string", 1, 4)
r("R55", "implicit multi-word string", "a: hello world\n", "implicit-string", 1, 4)
r("R56", "unquoted package in list", "packages:\n  - ripgrep\n", "implicit-string", 2, 5)
r("R57", "date", "a: 2024-01-01\n", "implicit-string", 1, 4)
r("R58", "sexagesimal 1:30", "a: 1:30\n", "implicit-string", 1, 4)
r("R59", "URL unquoted", "url: git://collection.example/tools\n", "implicit-string", 1, 6)
r("R60", "dotted plain key", "services.postgres.enable: true\n", "bad-key", 1, 1)
r("R61", "plain key with leading digit", "8080: x\n", "bad-key", 1, 1)
r("R62", "reserved plain key no", "no: 1\n", "reserved-key", 1, 1)
r("R63", "reserved plain key true", "true: 1\n", "reserved-key", 1, 1)
r("R64", "empty quoted key", '"": 1\n', "bad-key", 1, 1)
r("R65", "complex key", "? a\n: b\n", "complex-key", 1, 1)
r("R66", "folded scalar", "a: >\n  x\n", "folded-scalar", 1, 4)
r("R67", "keep chomping |+", "a: |+\n  x\n", "block-scalar-form", 1, 4)
r("R68", "indentation indicator |2", "a: |2\n   x\n", "block-scalar-form", 1, 4)
r("R69", "text after block header", "a: | x\n  y\n", "trailing-text", 1, 6)
r("R70", "multi-line double-quoted string", 'a: "one\n  two"\n', "unterminated-string", 1, 4)
r("R71", "unterminated single quote", "a: 'x\n", "unterminated-string", 1, 4)
r("R72", "bad escape \\x41", 'a: "\\x41"\n', "bad-escape", 1, 5)
r("R73", "bad escape \\e", 'a: "\\e"\n', "bad-escape", 1, 5)
r("R74", "escape \\u0000", 'a: "\\u0000"\n', "bad-escape", 1, 5)
r("R75", "surrogate escape", 'a: "\\ud83d\\ude00"\n', "bad-escape", 1, 5)
r("R76", "literal tab inside a string", 'a: "x\ty"\n', "tab", 1, 6)
r("R77", "text after closing quote", 'a: "x"y\n', "trailing-text", 1, 7)
r("R78", "two quoted strings", "a: 'x' 'y'\n", "trailing-text", 1, 8)
r("R79", "root is a list", "- a\n- b\n", "root-not-map", 1, 1)
r("R80", "root is a scalar", '"just text"\n', "syntax", 1, 12)
r("R81", "unexpected deeper indentation", "a: 1\n  b: 2\n", "indent", 2, 3)
r("R82", "dedent to an unmatched column", "a:\n    b: 1\n  c: 2\n", "indent", 3, 3)
r("R83", "list item where a key was expected", "a: 1\n- x\n", "syntax", 2, 1)
r("R84", "list starts on the key line", "a: - x\n", "syntax", 1, 4)
r("R85", "line without a colon", "a: 1\nb\n", "syntax", 2, 1)
r("R86", "space before colon", "a : 1\n", "syntax", 1, 1)
r("R87", "empty list item", "a:\n  -\nb: 1\n", "empty-value", 2, 4)
r("R88", "text glued after []", "a: []x\n", "trailing-text", 1, 6)
r("R89", "spaced empty map", "a: { }\n", "flow-collection", 1, 4)
r("R90", "comment glued to the value", "a: 1#c\n", "implicit-string", 1, 4)
r("R91", "reserved indicator @", "a: @foo\n", "syntax", 1, 4)
r("R92", "reserved indicator backtick", "a: `x`\n", "syntax", 1, 4)
r("R93", "anchor on a list item", "a:\n  - &x 1\n", "anchor", 2, 5)
r("R94", "tag on a list item", "a:\n  - !!str 1\n", "tag", 2, 5)
r("R95", "anchored key", "&k a: 1\n", "anchor", 1, 1)
r("R96", "block text under-indented after first text line", "a: |\n    four\n  two\n", "indent", 3, 3)
r("R97", "secret: literal password", 'services:\n  app:\n    password: "hunter2"\n', "secret", 3, 15)
r("R98", "secret: apiKey nested", 'services:\n  tideways:\n    apiKey: "abc123"\n', "secret", 3, 13)
r("R99", "secret: hashedPassword", 'users:\n  alice:\n    hashedPassword: "$6$abc"\n', "secret", 3, 21)
r("R100", "secret: privateKey block scalar", "keys:\n  privateKey: |\n    -----BEGIN-----\n    x\n", "secret", 2, 15)
r("R101", "secret: initialAdminPassword", 'services:\n  keycloak:\n    initialAdminPassword: "pw"\n', "secret", 3, 27)
r("R102", "secret: token in a list item map", 'l:\n  - token: "t"\n', "secret", 2, 12)
r("R103", "secret: client-token kebab", 'client-token: "t"\n', "secret", 1, 15)
r("R104", "secret: secretKey", 'minio:\n  secretKey: "k"\n', "secret", 2, 14)
r("R105", "document marker inside nested level at column 1", "a:\n  b: 1\n---\n", "document-marker", 3, 1)
r("R106", "indicator ] as value", "a: ]\n", "syntax", 1, 4)
r("R107", "dash and quoted key then junk", "'a'x: 1\n", "syntax", 1, 4)
r("R108", "second flow in value after list start", "a:\n  - x: [1]\n", "flow-collection", 2, 8)
r("R109", "block scalar bad: more spaces on blank line before text", "a: |\n      \n  x\n", "bad-indent", 2, 3)
r("R111", "no final newline", 'a: "x"', "no-final-newline", 1, 7)
r("R112", "no final newline inside a block scalar", "a: |\n  x", "no-final-newline", 2, 4)
r("R113", "block scalar first text line starts with a tab", "a: |\n  \tx\n", "tab", 2, 3)
r("R110", "NUL in comment", b"a: 1 # x\x00y\n", "control-char", 1, 9)
r("R114", "nesting 100 levels deep", "".join(" " * i + f"k{i}:\n" for i in range(100)) + " " * 100 + "v: 1\n", "too-deep", 65, 65)
r("R115", "nesting 100 levels deep, as list of lists", "a:\n" + "".join("  " * (i + 1) + "-\n" for i in range(100)) + "  " * 101 + "- 1\n", "too-deep", 65, 129)
