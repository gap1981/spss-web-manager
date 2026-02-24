import pyreadstat
import json

df, meta = pyreadstat.read_sav('JOVENES CRUDO.sav')

q14_vars = {}
for k, v in meta.column_names_to_labels.items():
    if k.lower().startswith('q14'):
        q14_vars[k] = v

q30_vars = {}
for k, v in meta.column_names_to_labels.items():
    if k.lower().startswith('q30'):
        q30_vars[k] = v

output = {
    'q14': q14_vars,
    'q30': q30_vars
}

with open('inspect_vars.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=4, ensure_ascii=False)
