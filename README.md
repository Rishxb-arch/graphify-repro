# graphify-repro: `self.method()` / `this.method()` calls bind to a different class's same-named method, tagged EXTRACTED

Hands-on test of [Graphify](https://github.com/Graphify-Labs/graphify) (`graphifyy` 0.9.74 from PyPI, and repo `v8` HEAD `0b60d47e6cd9338c51143f39f35b6c45c8453385`, 2026-10-02). Run on 2026-10-03 on a CPU-only Linux x86_64 box, Python 3.12, AST-only (`graphify extract <dir> --code-only`: no LLM, no API key, no network).

## What I was testing

The README says every edge is tagged `EXTRACTED` ("explicit in the source") or `INFERRED`, and that code is parsed deterministically with tree-sitter. I checked that claim for `calls` edges by building graphs and comparing against ground truth.

## Finding

When a file contains two classes that both define a method with the same name, a call like `self.bark()` / `this.bark()` / a bare `bark()` inside class `Dog` is wired to **the last `bark` defined in the file**, which can belong to a different class (`Cat.bark`), and the edge is tagged `EXTRACTED`.

Minimal case (`corpus_zoo/`, one small file per language):

```python
class Dog:
    def speak(self): return self.bark()   # graph: Dog.speak -calls-> Cat.bark  [EXTRACTED]   (should be Dog.bark)
    def bark(self): return "woof"
class Cat:
    def speak(self): return "meow"
    def bark(self): return "hiss"
```

Same result in all 12 languages tried (Python, JavaScript, TypeScript, Java, C#, C++, Go, Rust, Ruby, PHP, Kotlin, Swift): see `logs/zoo_pypi_0.9.74.log` and `logs/zoo_repo_HEAD_0b60d47.log`. Cross-file duplicates were fine in the one case I tried. The effect depends on order: if `Dog` comes after `Cat`, the same call binds correctly. A call inherited from a base class (`class Dog(Base)` calling `self.bark()` defined in `Base`) also binds to an unrelated `Cat.bark` in the same file.

### How common is it in real code?

Python only, independent ground truth from the stdlib `ast` module: for every `self.<m>()` call inside a class that itself defines `<m>`, does the graph's `calls` edge point at that class's `<m>`? (`scripts/verify_python_selfcalls.py`, `logs/real_repos_pypi_0.9.74.log`)

| repo (pinned commit) | self-calls to own methods | edge to the right method | edge to another class's method (all `EXTRACTED`) | no edge |
|---|---|---|---|---|
| encode/httpx `b5addb6` | 95 | 66 | **26** | 3 |
| pallets/click `06b2a67` | 152 | 128 | **22** | 2 |
| pallets/flask `d73fa1c` | 91 | 84 | **4** | 3 |
| psf/requests `611c616` | 63 | 59 | **2** | 2 |
| total | 401 | 337 | **54 (13.5%)** | 10 |

Concrete example, httpx: the sync `Client.get/post/put/patch/delete/head/options` all call `self.request(...)`, but the graph sends all of them to `AsyncClient.request` (14 incoming `calls` edges, 7 of them from sync methods), and `Client.request` ends up with **zero** callers. That is what `graphify affected`, `path` and the god-node ranking then use.

## Root cause (from reading the code, not from a debugger)

`graphify/extractors/engine.py`, call-graph pass (around line 6122): `label_to_nid[normalised] = n["id"]` builds one file-wide map from method name to node id, and later definitions overwrite earlier ones. The `self`/`this`/bare-call branch (around line 6965) resolves with `label_to_nid.get(callee_name)`, which is not scoped to the enclosing class. `CONTRIBUTING.md` asks for fail-closed behaviour over guessed relationships; this path guesses and labels the guess `EXTRACTED`.

## Searched upstream first

I searched the open and closed issues. Related but different: #2810 (same-file symbols collapsing after id normalisation), #3913 (`path` resolving ambiguous endpoints), #543 (cross-file INFERRED resolution), #2299 (C# receiver typing). I did not find an issue for same-class method resolution. Something similar may exist under other words; I could not search PRs exhaustively.

## Limitations (honest)

- The 401-call audit is Python-only. The other 11 languages are covered only by the one-file zoo, so I cannot give a real-world rate for them.
- The audit counts `self.m()` calls to methods the class defines itself; inherited calls, dynamic dispatch and non-`self` receivers were not judged.
- I did not run the semantic (LLM) pass, docs/PDF/image/video extraction, the MCP server, `graphify install`, or the hosted product. Only the local AST path.
- I read `engine.py` only around this code path.

## Reproduce

```bash
uv tool install graphifyy==0.9.74          # or: pip install graphifyy==0.9.74
bash scripts/run_zoo.sh                    # prints Dog.speak -> Cat.bark [EXTRACTED] per language
bash scripts/run_real_repos.sh             # clones 4 repos at pinned commits, prints the table's raw numbers
```

## Patch

A fix is in `patches/0001-fix-extract-resolve-self-this-calls-to-the-enclosing.patch` (commit `139fb224202ca48bf3e6b9cf18ae5673fc565a08` on fork branch `fix/same-class-method-resolution`, based on `v8` / `0b60d47e6cd9338c51143f39f35b6c45c8453385`). It is not merged upstream. No pull request was opened.

Fork branch: https://github.com/Rishxb-arch/graphify/tree/fix/same-class-method-resolution

Compare: https://github.com/Graphify-Labs/graphify/compare/v8...Rishxb-arch:graphify:fix/same-class-method-resolution

### What changed

`graphify/extractors/base.py` indexes existing `method` edges and resolves a callee name against the enclosing class.

`graphify/extractors/engine.py` uses that resolution when the caller is a method and the call is a Ruby bare send, a bare call in Java, C#, Kotlin, Swift, C++, or Scala (implicit this), or a member call whose receiver is `self`, `cls`, `this`, or `$this`. Ruby `self.bark` and PHP `$this->bark()` now record that receiver so they take this path. `super` / `base` / `parent` are not retargeted onto the caller's own override: an ancestor hit is kept, and a hit owned by an unrelated class is dropped. Constructor nodes (`new Foo()` and the other object-creation node types) are not treated as implicit this.

`graphify/extractors/go.py` scopes a selector only when the operand is that method's receiver variable (`func (d Dog)` calling `d.Bark()`).

`graphify/extractors/rust.py` scopes `self.method()` to the enclosing impl. If that impl does not define the method, the call stays unresolved in-file so the existing cross-file Rust resolver can still see it.

`CHANGELOG.md` adds an Unreleased note. `tests/test_same_class_method_resolution.py` is new.

If the enclosing class defines the method, the edge stays `EXTRACTED` to that method. If it does not, a file-wide map hit owned by a different class is dropped. A map hit that is already an ancestor (`inherits` or `mixes_in`) is kept. A module-level function that is the map's survivor still resolves.

### Tests added

15 tests, all passing:

- `test_self_call_binds_to_own_class_not_the_later_class`, parametrized over Python, JavaScript, TypeScript, Java, C#, C++, Go, Rust, Ruby, PHP, Kotlin, and Swift. Dog is declared first and Cat last. `Dog.speak` must be an `EXTRACTED` edge to `Dog.bark`, and must not call `Cat.bark`.
- `test_python_module_level_call_still_resolves`: a module-level `helper()` still resolves.
- `test_python_other_receiver_is_not_pulled_onto_the_caller_class`: `other.bark()` binds to neither `Dog.bark` nor `Cat.bark`.
- `test_inherited_self_call_does_not_bind_to_unrelated_class`: `class Dog(Base)` calling `self.bark()` defined on `Base`, with `Cat.bark` also in the file, must not bind to `Cat.bark`.

### Suite

`uv run pytest tests/ -q` on the untouched commit `0b60d47`: **28 failed, 6135 passed, 102 skipped** (`logs/pytest_baseline_0b60d47.log`, 124.71s).

The same command on the patched tree: **28 failed, 6150 passed, 102 skipped** (`logs/pytest_patched.log`, 123.89s). The extra 15 passes are the new tests. The 28 failures are the same set on both trees: erlang extractor (7), ollama (`ModuleNotFoundError: openai`, 4), R extractor (7), solidity extractor (5), vbnet extractor (5). They are pre-existing on `0b60d47`.

`uv run ruff check` on `base.py`, `engine.py`, `go.py`, `rust.py`, and the new test: all checks passed. Pyright on `graphify/extractors/base.py` and the new test: 0 errors. This note does not claim a clean pyright run of `engine.py`, `go.py`, or `rust.py`.

### Zoo and real repos after the patch

`logs/after_fix_zoo.log`: all 12 languages now print `Dog.speak -> Dog.bark [EXTRACTED]`. The unpatched logs still show `Cat.bark`.

`logs/after_fix_real_repos.log` is `scripts/run_real_repos.sh` against the patched checkout (`graphify extract --code-only`, then `scripts/verify_python_selfcalls.py`). Node counts did not change. Edge counts dropped slightly.

| repo | nodes | edges unpatched | edges patched | wrong unpatched | wrong patched | correct unpatched | correct patched | missing unpatched | missing patched |
|---|---|---|---|---|---|---|---|---|---|
| click/src | 1032 | 2384 | 2345 | 22 | 3 | 128 | 147 | 2 | 2 |
| requests/src | 668 | 1445 | 1444 | 2 | 2 | 59 | 60 | 2 | 1 |
| httpx | 1777 | 3621 | 3610 | 26 | 0 | 66 | 92 | 3 | 3 |
| flask/src | 879 | 1774 | 1771 | 4 | 0 | 84 | 88 | 3 | 3 |

Script-WRONG total: 54 -> 5. httpx's 26 cross-class edges are gone.

The 5 rows the script still prints as WRONG are same-class `@overload` stubs. The graph node is minted at the first overload line; the audit's ground truth is the last `def` line, so the line numbers do not match. They are click `Context.forward -> Context.invoke`, `Command.__call__ -> Command.main`, `Parameter.consume_value -> Parameter.get_default`, and requests `Response.__iter__` and `Response.content -> Response.iter_content`. None of them point at another class.

### Still unresolved

- If the class does not define the method and the file-wide map's survivor belongs to an unrelated class, the edge is dropped. The parent method is not searched for. It is kept only when the map already points at an ancestor. `Dog(Base).speak()` calling `self.bark()` with both `Base.bark` and `Cat.bark` in the file therefore has no `calls` edge. That is the negative test above. Unique `Base.bark`, with no `Cat`, stays `EXTRACTED` to `Base.bark`.
- A receiver-less call whose class does not define the name (Java, C#, Kotlin, Swift, C++, Scala bare name, or a Ruby call with no receiver) can still be attached `INFERRED` by the existing shared unique-candidate pass when exactly one same-named callable exists. `self` / `this` member calls are not sent through that pass.
- Go scopes only the receiver variable (`d.Bark()`). Promoted or embedded methods are not guessed. A call on a different value keeps the old map.
- Rust scopes `self.method()` only. `Self::method` and non-self receivers are unchanged.
- Python bare calls are unchanged. A bare `bark()` can still hit `Cat.bark` when that method overwrote a module-level `bark` in the map. A uniquely named module function still resolves.
- Dynamic receivers (`other.bark()`, `self.store.get()`) are unchanged and still produce no edge.
- `@overload` stubs share one node, at the first overload's line.
- `super()` / `base` keeps an ancestor hit and drops an unrelated class. It does not move the edge onto the caller's override, and it does not walk the base chain when the map points at `Cat`.
- A same-file module function that lost the map to another class's method is not recovered.
