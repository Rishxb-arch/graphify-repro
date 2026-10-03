"""Independent check of graphify `calls` edges for `self.x()` calls in Python.
Ground truth comes from the stdlib `ast`. A graph edge is WRONG when the callee node
is a method of a different class than the one that defines/inherits `x` for the caller's class."""
import ast, json, sys, os, collections
root, gjson = sys.argv[1], sys.argv[2]
g = json.load(open(gjson))
nodes = {n['id']: n for n in g['nodes']}
def loc(n):
    s = n.get('source_location') or ''
    return int(s.lstrip('L').split('-')[0]) if s[:1]=='L' and s[1:2].isdigit() else None
# index graph nodes by (relative file, line)
by_loc = {}
for n in g['nodes']:
    if n.get('source_file') and loc(n): by_loc.setdefault((os.path.normpath(n['source_file']), loc(n)), []).append(n)
out_edges = collections.defaultdict(list)
for e in g['links']:
    if e['relation']=='calls': out_edges[e['source']].append(e)
stats = collections.Counter(); wrong = []
for dp, _, fs in os.walk(root):
    if 'graphify-out' in dp or '/tests' in dp: continue
    for f in fs:
        if not f.endswith('.py'): continue
        p = os.path.join(dp, f)
        try: tree = ast.parse(open(p).read())
        except Exception: continue
        rel = os.path.relpath(p, root)
        classes = {}
        for c in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            classes[c.name] = c
        for cname, c in classes.items():
            own = {m.name: m for m in c.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for m in own.values():
                cand = [n for k,v in by_loc.items() if k[1]==m.lineno and (k[0]==rel or k[0].endswith('/'+rel) or rel.endswith(k[0])) for n in v]
                cand = [n for n in cand if n['label'].startswith('.')]
                if not cand: continue
                caller = cand[0]
                for call in [x for x in ast.walk(m) if isinstance(x, ast.Call)]:
                    fn = call.func
                    if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id == 'self':
                        x = fn.attr
                        if x not in own: continue          # inherited / dynamic: not judged here
                        want = own[x].lineno
                        stats['self_calls_to_own_methods'] += 1
                        es = [e for e in out_edges[caller['id']] if nodes[e['target']]['label'] == f'.{x}()']
                        if not es: stats['edge_missing'] += 1; continue
                        for e in es:
                            t = nodes[e['target']]
                            if loc(t) == want: stats['edge_correct'] += 1
                            else:
                                stats['edge_WRONG_class'] += 1
                                wrong.append((rel, cname, m.name, x, call.lineno, t.get('source_file'), t.get('source_location'), e.get('confidence')))
print(json.dumps(stats, indent=1))
for w in wrong[:40]: print('WRONG', w)
