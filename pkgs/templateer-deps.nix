# templateer's dependency closure, for the parts nixpkgs cannot supply.
#
# WHY THIS FILE EXISTS. templateer is a pydantic-ai caller, and this nixpkgs carries
# pydantic-ai 1.107.0 while templateer's own metadata says `pydantic-ai-slim>=2,<3`.
# That is a major version apart, so the whole pydantic-ai 2.x line and the parts of its
# tree that moved with it are pinned here instead. `minijinja` nixpkgs does not carry at
# all. Each entry below states which of the two it is.
#
# EVERY ENTRY IS A LIABILITY. An entry is correct only while nixpkgs is behind; once
# nixpkgs carries a version that satisfies the consumer, delete the entry and let the
# dep table resolve to nixpkgs again. `reason` is what makes that check possible without
# re-deriving the whole tree — read it before assuming an entry is still needed.
#
# Measured 2026-09-08 against templateer 0.4.0 and the shared shelf venv, which resolved
# exactly these versions. Nothing here is a guess at what uv would pick.
# It is an OVERLAY (`packageOverrides`), not a set of standalone derivations. A standalone
# pin produces two copies of a distribution the moment anything else in the closure still
# resolves the nixpkgs one, and buildPythonPackage refuses that closure — measured here on
# `idna`. Overriding the set rebuilds every dependent against the pin instead.
{ pkgs, mkPypiWheel }:

self: super:

let
  py = self;
  wheel = mkPypiWheel self;
in
{
  # httpx 2.x renamed itself; the pydantic-ai 2.x line takes the new name. nixpkgs has
  # httpcore2/httpx2 at 2.3.0, and openai 3.8 requires httpx2>=2.7.0.
  idna = wheel {
    pname = "idna";
    version = "3.18";
    filename = "idna-3.18-py3-none-any.whl";
    hash = "7f952cbe720b688055e3f87de14f5c3e5fdaa8bc3928985c4077ca689de849a2";
    reason = "nixpkgs has 3.13; httpx2 2.7.0 requires idna>=3.18";
  };

  httpcore2 = wheel {
    pname = "httpcore2";
    version = "2.7.0";
    filename = "httpcore2-2.7.0-py3-none-any.whl";
    hash = "1452f589fe23f55b44546cd884294c41a29330af902bc0b71a761fd52d18f92b";
    dependencies = [ py.h11 py.truststore ];
    reason = "nixpkgs has 2.3.0; httpx2 2.7.0 pins httpcore2==2.7.0";
  };

  httpx2 = wheel {
    pname = "httpx2";
    version = "2.7.0";
    filename = "httpx2-2.7.0-py3-none-any.whl";
    hash = "ed2a2719c696789e09493bd8e2bec3d8bd925cc6e26b68389ec25ade132f7bf4";
    dependencies = [ py.anyio self.httpcore2 self.idna py.truststore ];
    reason = "nixpkgs has 2.3.0; openai 3.8.0 requires httpx2>=2.7.0";
  };

  jiter = wheel {
    pname = "jiter";
    version = "0.16.0";
    filename = "jiter-0.16.0-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl";
    hash = "c682bea068a90b764577bdb78a60a4c1d1606daf9cd4c893832a37c7cc9d9026";
    reason = "nixpkgs has 0.12.0; openai 3.8.0 requires jiter>=0.16.0. Native (Rust), taken as the published manylinux wheel rather than rebuilt.";
  };

  genai-prices = wheel {
    pname = "genai_prices";
    version = "0.1.6";
    filename = "genai_prices-0.1.6-py3-none-any.whl";
    hash = "35ac8043dbcf2958488129413bfecba7304fe12a68ad4a78c5b0d15281e82814";
    dependencies = [ self.httpx2 py.pydantic ];
    reason = "nixpkgs has 0.0.66; pydantic-ai-slim 2.40.0 requires genai-prices>=0.1.6";
  };

  pydantic-graph = wheel {
    pname = "pydantic_graph";
    version = "2.40.0";
    filename = "pydantic_graph-2.40.0-py3-none-any.whl";
    hash = "e2db5b8694b44b5f5e01e37d2ca1ef3b2e9bf104c7d0a8f13028b914a296905e";
    dependencies = [ py.anyio py.logfire-api py.pydantic py.typing-inspection ];
    reason = "nixpkgs has 1.107.0; pydantic-ai-slim 2.40.0 pins pydantic-graph==2.40.0";
  };

  openai = wheel {
    pname = "openai";
    version = "3.8.0";
    filename = "openai-3.8.0-py3-none-any.whl";
    hash = "514736aa1e4ef1033c1209ad53897392845ccd4f2c4fae6413b2cf5f91c2c926";
    dependencies = [ py.anyio self.httpx2 self.jiter py.pydantic py.sniffio py.typing-extensions ];
    reason = "nixpkgs has 2.33.0; pydantic-ai-slim 2.40.0's `openai` extra requires openai>=3.8.0";
  };

  # The `[openai]` extra is taken here, not left to the extras syntax: `mkPythonCli`
  # resolves a PEP 508 head and drops the extra, so the extra's own dependencies —
  # openai and tiktoken — are named as ordinary dependencies of this entry instead.
  # tiktoken comes from nixpkgs (0.12.0 satisfies >=0.12.0).
  pydantic-ai-slim = wheel {
    pname = "pydantic_ai_slim";
    version = "2.40.0";
    filename = "pydantic_ai_slim-2.40.0-py3-none-any.whl";
    hash = "c943543939a6a8ad490c8dd48429957cb6b2d6479f0a47332253b6f8fbc5d993";
    dependencies = [
      py.anyio
      self.genai-prices
      py.griffelib
      self.httpx2
      py.opentelemetry-api
      self.pydantic-graph
      py.pydantic
      py.typing-inspection
      # the [openai] extra
      self.openai
      py.tiktoken
    ];
    reason = "nixpkgs has 1.107.0; templateer requires pydantic-ai-slim>=2,<3 — a major version apart";
  };

  minijinja = wheel {
    pname = "minijinja";
    version = "2.24.0";
    filename = "minijinja-2.24.0-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl";
    hash = "b5a4dbd73f2c02ab6d0ab0b62b68a7d2557e5d45723d3b4e423b7c3877f31cad";
    reason = "nixpkgs carries no minijinja at all. Native (Rust/PyO3), taken as the published abi3 manylinux wheel — the same artifact shape this repo vends for pyjutsu.";
  };
}
