import json

with open(r'Groundtruth\F1accuaracyResult.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, c in enumerate(nb['cells']):
    if c.get('cell_type') == 'code':
        source = ''.join(c.get('source', []))
        if 'fig1, ax1' in source:
            has_7_scales = '2x,2y,2z\t0.833\t0.714' in source and '3x,1y,1z' not in source
            print(f'Cell {i}: has_7_scales={has_7_scales}, has_adjust_saturation={"adjust_saturation" in source}')
