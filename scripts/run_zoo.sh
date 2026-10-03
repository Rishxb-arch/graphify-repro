#!/usr/bin/env bash
# usage: scripts/run_zoo.sh [graphify-executable]   (default: `graphify` on PATH)
# Builds a graph (AST only, no LLM, no network) from corpus_zoo/ and lists every `calls` edge.
# Expected for each language: Dog.speak -> Dog.bark. Observed: Dog.speak -> Cat.bark, tagged EXTRACTED.
set -eu; G=${1:-graphify}; HERE="$(cd "$(dirname "$0")/.." && pwd)"; W=$(mktemp -d); cp -r "$HERE/corpus_zoo" "$W/zoo"
"$G" extract "$W/zoo" --code-only >/dev/null 2>&1
python3 "$HERE/scripts/list_calls.py" "$W/zoo/graphify-out/graph.json" | sort
