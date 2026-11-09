from pathlib import Path
import re

def replace(path,old,new):
    p=Path(path);s=p.read_text()
    if new in s:return
    assert s.count(old)==1,(path,old[:80],s.count(old))
    p.write_text(s.replace(old,new,1))

# Reuse the authenticated application shell and current styling.
s=Path('office.html').read_text()
s=re.sub(r'<title>.*?</title>','<title>Entre Besos · Proveedores</title>',s,count=1)
s=s.replace('id="office-app"','id="suppliers-app"').replace('Resumen y contactos compartidos entre PC y celular.','Proveedores e insumos en una misma base compartida.')
s=re.sub(r'<style id="eb-import-responsive">.*?</style>','',s,flags=re.S)
for asset in ['contacts-import.js','vendor/fflate.js']:
    s=re.sub(r'<script[^>]+src="/'+re.escape(asset)+r'[^>]+></script>','',s)
new='<script type="application/x-eb-shared" src="/materials-core.js?v=suppliers1"></script><script type="application/x-eb-shared" src="/suppliers-core.js?v=suppliers1"></script><script type="application/x-eb-shared" src="/suppliers-ui.js?v=suppliers1"></script>'
s=re.sub(r'<script[^>]+src="/office-ui.js[^>]+></script>',new,s)
s=s.replace('</head>','<link rel="stylesheet" href="/suppliers.css?v=suppliers1"></head>',1)
Path('suppliers.html').write_text(s)
p=Path('office-nav.js');s=p.read_text()
if "section==='suppliers'" not in s:
    s=s.replace("location.href=section==='orders'?","location.href=section==='suppliers'?'/suppliers.html':section==='orders'?",1)
    s=s.replace("add(side,'orders','Pedidos','▣');","add(side,'orders','Pedidos','▣');add(side,'suppliers','Proveedores','▦');",1)
    s=s.replace("add(mobile,'orders','Pedidos','▣');","add(mobile,'orders','Pedidos','▣');add(mobile,'suppliers','Proveedores','▦');",1)
    s=s.replace("(location.pathname==='/orders.html'&&b.dataset.office==='orders')","(location.pathname==='/orders.html'&&b.dataset.office==='orders')||(location.pathname==='/suppliers.html'&&b.dataset.office==='suppliers')",1)
    p.write_text(s)
replace('edit-return.js','#orders-app,#documents-app','#orders-app,#documents-app,#suppliers-app')
replace('edit-return.js',"'orders-filter-to'];","'orders-filter-to','supplier-search','supplier-filter'];")
replace('edit-return.js',"'data-edit-order','data-edit'","'data-edit-order','data-supplier-edit','data-edit'")
replace('shared.js','/edit-return.js?v=save-return1','/edit-return.js?v=suppliers1')
p=Path('index.html');s=p.read_text()
if "if(s==='Proveedores')" not in s:
    s=s.replace('function go(s){',"function go(s){if(s==='Proveedores'){location.href='/suppliers.html';return;}",1);p.write_text(s)
for p in Path('.').glob('*.html'):
    s=p.read_text()
    for asset in ['office-nav.js','shared.js']:
        s=re.sub(re.escape(asset)+r'\?v=[^"\s]+',asset+'?v=suppliers1',s)
    p.write_text(s)
p=Path('Dockerfile');s=p.read_text()
if 'COPY suppliers-core.js suppliers-ui.js ./' not in s:
    s=s.replace('FROM nginx:alpine AS static','COPY suppliers-core.js suppliers-ui.js ./\nCOPY tests/suppliers.cjs ./tests/\nRUN node --check suppliers-core.js && node --check suppliers-ui.js && node tests/suppliers.cjs\n\nFROM nginx:alpine AS static',1)
    s=s.replace('COPY nginx.conf','COPY suppliers.html suppliers-core.js suppliers-ui.js suppliers.css /usr/share/nginx/html/\nCOPY nginx.conf',1)
    s=s.replace('for asset in ','for asset in suppliers.html suppliers-core.js suppliers-ui.js suppliers.css ',1);p.write_text(s)
print('Suppliers integrated; original inventory, contacts, costs, documents, sales and orders unchanged.')
