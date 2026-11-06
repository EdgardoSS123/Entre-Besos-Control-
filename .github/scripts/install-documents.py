from pathlib import Path
import re,hashlib
# All migrations below change source only. They never open production data.
expected={'server.cjs':'efca1e8ed9c99ba4944b8ed9a195a1683607a668a74b7ed63d51bf4811a394fd','office-nav.js':'5331ef135837dcd9ba59a30777b6963b2fd31679142b123c0476adb9febf9c1e','office.html':'6c00c0d3cd884ab32f2aae4710709b65d2924282dd1eefaac46219c9f60fd372','control.html':'4936d96959be379b06cf70d31034a6a42efbf6086aade7e07d8026bed15adcf5','materials.html':'30c3b1b43352268a78cab1f8ea6ea45f038bb08acdf9a018dc18fd9036f1e782','index.html':'0bb2a3d5639203de6d285b470244a2a5f0c549c521ce2dabd7f674d899646f1a','Dockerfile':'0dd7455e25ea6e597a6b62a5dea530c9b4b4ed79e5d5eb81f112143a25976e70'}
if Path('documents.html').exists():
    assert "createDocuments" in Path('server.cjs').read_text()
    print('Document integration already present.')
    raise SystemExit(0)
for name,sha in expected.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,'Stale source: '+name
p=Path('server.cjs');s=p.read_text()
s=s.replace('const body=async(req)=>','const body=async(req,limit=MAX)=>').replace("if(size>MAX)throw error(413,'El respaldo supera 12 MB; no se guardó.')","if(size>limit)throw error(413,'El archivo supera el límite permitido; no se guardó.')")
marker=' const handler=async(req,res)=>{try{'
s=s.replace(marker," const documents=require('./documents-store.cjs').createDocuments({db,auth,csrf,json,body});\n"+marker)
s=s.replace("  if(route.startsWith('/api/'))throw","  if(await documents(req,res,url))return;\n  if(route.startsWith('/api/'))throw")
p.write_text(s)
s=Path('office.html').read_text()
s=re.sub(r'<style id="eb-import-responsive">.*?</style>','',s)
s=s.replace('Entre Besos · Resumen y contactos','Entre Besos · Documentos').replace('id="office-app"','id="documents-app"')
s=s.replace('</head>','<link rel="stylesheet" href="/documents.css?v=documents1"></head>')
s=s[:s.index('<script type="application/x-eb-shared"')]+'<script type="application/x-eb-shared" src="/documents-ui.js?v=documents1"></script><script type="application/x-eb-shared" src="/office-nav.js?v=documents1"></script><script type="application/x-eb-shared" src="/pwa.js?v=office1"></script><script src="/shared.js?v=office1" defer></script></body></html>\n'
s=s.replace('Resumen y contactos compartidos entre PC y celular.','Documentos compartidos entre PC y celular.')
Path('documents.html').write_text(s)
p=Path('office-nav.js');s=p.read_text();s=s.replace("location.href='/office.html?section='+section;","location.href=section==='documents'?'/documents.html':'/office.html?section='+section;")
s=s.replace("add(side,'contacts','Contactos','♧');","add(side,'contacts','Contactos','♧');add(side,'documents','Documentos','▱');")
s=s.replace("add(mobile,'contacts','Contactos','♧');","add(mobile,'contacts','Contactos','♧');add(mobile,'documents','Docs','▱');mobile.style.setProperty('grid-template-columns','repeat('+mobile.children.length+',minmax(0,1fr))','important');")
s=s.replace("location.pathname==='/office.html'&&b.dataset.office===current","(location.pathname==='/office.html'&&b.dataset.office===current)||(location.pathname==='/documents.html'&&b.dataset.office==='documents')")
p.write_text(s)
for name in ['control.html','materials.html','office.html']:
    p=Path(name);p.write_text(p.read_text().replace('office-nav.js?v=office1','office-nav.js?v=documents1'))
p=Path('index.html');s=p.read_text().replace("function go(s){","function go(s){if(s==='Documentos'){location.href='/documents.html';return;}",1);p.write_text(s)
p=Path('Dockerfile');s=p.read_text().replace('COPY server.cjs shared.js ./','COPY server.cjs shared.js documents-store.cjs ./').replace('COPY server.cjs ./server.cjs','COPY server.cjs documents-store.cjs ./')
s=s.replace('FROM nginx:alpine AS static','COPY tests/documents.cjs ./tests/\nRUN node --check documents-store.cjs && node --experimental-sqlite tests/documents.cjs\n\nFROM nginx:alpine AS static')
s=s.replace('COPY nginx.conf','COPY documents.html documents-ui.js documents.css /usr/share/nginx/html/\nCOPY nginx.conf').replace('for asset in ','for asset in documents.html documents-ui.js documents.css ');p.write_text(s)
print('Integrated five document categories, private file storage and shared navigation. No business data read or changed.')
