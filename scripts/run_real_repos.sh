#!/usr/bin/env bash
# usage: scripts/run_real_repos.sh [graphify-executable]
# Clones four popular Python libraries at pinned commits, builds an AST-only graph for each, and uses the stdlib `ast`
# module as independent ground truth for every `self.<m>()` call where the calling class defines `<m>` itself.
set -eu; G=${1:-graphify}; HERE="$(cd "$(dirname "$0")/.." && pwd)"; W=${WORKDIR:-$(mktemp -d)}; cd "$W"
clone(){ git clone -q "https://github.com/$1" "$2" && git -C "$2" checkout -q "$3"; }
clone pallets/click click 06b2a678741131fd577ce170e23e5ca0aeba0309
clone psf/requests requests 611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60
clone encode/httpx httpx b5addb64f0161ff6bfe94c124ef76f6a1fba5254
clone pallets/flask flask d73fa1cdcbd8b1465c151db8924ba58b1dd14e35
for r in click/src requests/src httpx flask/src; do [ -d "$r" ] || r=${r%/src}; echo "=== $r"; "$G" extract "$r" --code-only >/dev/null 2>&1
  python3 "$HERE/scripts/verify_python_selfcalls.py" "$r" "$r/graphify-out/graph.json"; done
