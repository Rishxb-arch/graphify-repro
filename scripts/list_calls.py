import json,sys
g=json.load(open(sys.argv[1]))
nodes={n['id']:n for n in g['nodes']}
for e in g['links']:
    if e['relation']=='calls':
        s,t=nodes[e['source']],nodes[e['target']]
        print(f"{s.get('source_file')}: {s['label']} ({s['id']}) -> {t['label']} ({t['id']}, {t.get('source_file')} {t.get('source_location')}) [{e.get('confidence')}] @{e.get('source_location')}")
