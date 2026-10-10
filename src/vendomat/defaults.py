"""Values that one Vendomat release carries (``MACH-018``).

Each release tests one plain ``github:NixOS/nixpkgs`` revision. ``sync`` writes it as the
``nixpkgs`` input of a devenv fragment when the registry names none. The flake of this repository
pins the same revision, and a check compares the two.
"""

from __future__ import annotations

DEFAULT_NIXPKGS_REV = "e7439b6b14ad3cc35d05608ebca9bce01a25f5f8"
DEFAULT_NIXPKGS_URL = f"github:NixOS/nixpkgs/{DEFAULT_NIXPKGS_REV}"
