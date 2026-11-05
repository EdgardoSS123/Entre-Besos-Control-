from pathlib import Path
import json,re
from PIL import Image,ImageChops

def replace(path,old,new):
    p=Path(path);s=p.read_text()
    if new in s:return
    assert s.count(old)==1,(path,old[:100],s.count(old))
    p.write_text(s.replace(old,new,1))

# The brand artwork is preserved, only resized and padded for launcher icons.
source=Image.open('EB logo.jpg').convert('RGB')
mask=ImageChops.difference(source,Image.new('RGB',source.size,'white')).convert('L').point(lambda v:255 if v>30 else 0)
box=mask.getbbox();art=source.crop(box) if box else source
Path('icons').mkdir(exist_ok=True)
for size,padding,name in [(180,.12,'eb-180.png'),(192,.12,'eb-192.png'),(512,.12,'eb-512.png'),(512,.19,'eb-maskable-512.png')]:
    icon=Image.new('RGB',(size,size),'white');copy=art.copy();limit=round(size*(1-2*padding));copy.thumbnail((limit,limit),Image.Resampling.LANCZOS)
    icon.paste(copy,((size-copy.width)//2,(size-copy.height)//2));icon.save(Path('icons')/name,optimize=True)
manifest={'id':'/','name':'Entre Besos Control','short_name':'Entre Besos','description':'Control interno de lotes, bodegas, ventas, insumos y marketing.','lang':'es-MX','start_url':'/','scope':'/','display':'standalone','background_color':'#f4f5f9','theme_color':'#ffffff','icons':[{'src':'/icons/eb-192.png','sizes':'192x192','type':'image/png','purpose':'any'},{'src':'/icons/eb-512.png','sizes':'512x512','type':'image/png','purpose':'any'},{'src':'/icons/eb-maskable-512.png','sizes':'512x512','type':'image/png','purpose':'maskable'}]}
Path('app.webmanifest').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
head='<link rel="manifest" href="/app.webmanifest"><link rel="apple-touch-icon" sizes="180x180" href="/icons/eb-180.png"><link rel="icon" type="image/png" sizes="192x192" href="/icons/eb-192.png"><meta name="apple-mobile-web-app-title" content="Entre Besos"><meta name="apple-mobile-web-app-status-bar-style" content="default"><meta name="mobile-web-app-capable" content="yes"><link rel="stylesheet" href="/pwa.css?v=iphone-pack1">'
for name in ['control.html','materials.html']:
    p=Path(name);s=p.read_text()
    if '/app.webmanifest' not in s:
        s=s.replace('</head>',head+'</head>',1)
        if 'name="apple-mobile-web-app-capable"' not in s:s=s.replace('</head>','<meta name="apple-mobile-web-app-capable" content="yes"></head>',1)
        s=s.replace('</body>','<script src="/device-backup.js?v=iphone-pack1" defer></script><script src="/pwa.js?v=iphone-pack1" defer></script></body>',1)
        s=s.replace('<script src="./inventory-core.js','<script src="/packaging.js?v=iphone-pack1" defer></script><script src="./inventory-core.js',1)
        p.write_text(s)
landing='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#ffffff"><meta name="apple-mobile-web-app-capable" content="yes"><title>Entre Besos Control · Instalar</title><meta name="description" content="Instala Entre Besos Control con su logo en tu iPhone y comparte el acceso a la app."><meta property="og:title" content="Entre Besos Control"><meta property="og:description" content="Instala el acceso de Entre Besos en la pantalla de inicio."><meta property="og:type" content="website"><meta property="og:image" content="https://entre-besos-web-production.up.railway.app/icons/eb-512.png">'+head+'</head><body class="eb-install-page"><main id="eb-install-content"><h1>Entre Besos</h1><p>Cargando opciones de instalación…</p><a href="/">Abrir app</a></main><noscript>Activa JavaScript para mostrar las opciones. En Safari puedes usar Compartir → Agregar a pantalla de inicio.</noscript><script src="/device-backup.js?v=iphone-pack1" defer></script><script src="/pwa.js?v=iphone-pack1" defer></script></body></html>'
Path('instalar.html').write_text(landing+'\n')

# All conversions are presentational; no inventory/save/ledger functions are changed.
p=Path('simple-lot.js');s=p.read_text()
if 'const cases=n=>window.EBPackages.describe(n);' not in s:
    s,count=re.subn(r'  const cases=n=>\{[^\n]+\};','  const cases=n=>window.EBPackages.describe(n);',s,count=1);assert count==1
    old="cases(n)+' · '+num(n/480)+' pallets'";assert s.count(old)==1;s=s.replace(old,'cases(n)',1)
    s=s.replace('Corrugado = caja de 6 botellas. Las sueltas se muestran aparte; no es inventario de cartón vacío.','1 caja = 6 botellas · 1 pallet = 80 cajas. El desglose muestra pallets completos, cajas fuera de los pallets y botellas sueltas. No incluye cartón vacío.')
    p.write_text(s)
p=Path('lot-operations.js');s=p.read_text()
if 'return window.EBPackages.describe(n);' not in s:
    s,count=re.subn(r'  function lotCardCases\(n\)\{.*?\n  \}', '  function lotCardCases(n){return window.EBPackages.describe(n);\n  }',s,count=1,flags=re.S);assert count==1
    old="(n<0?'−':'')+number(Math.floor(Math.abs(n)/6))+' corrugados'+(Math.abs(n)%6?' + '+number(Math.abs(n)%6)+' botellas sueltas':'')+' · '+number(n/480)+' pallets</p>'"
    assert s.count(old)==1,('warehouse packaging',s.count(old))
    s=s.replace(old,"window.EBPackages.describe(n)+'</p>'",1);p.write_text(s)
p=Path('reports-data.js');s=p.read_text()
if 'const packages=' not in s:
    s=s.replace("  const names=", "  const packages=typeof module!=='undefined'&&module.exports?require('./packaging.js'):root.EBPackages;\n  const names=",1)
    s,count=re.subn(r'  function cases\(n\)\{[^\n]+\}', '  function cases(n){return packages.describe(n,true);}',s,count=1);assert count==1
    s=s.replace('1 corrugado equivale a 6 botellas; las botellas sueltas se muestran aparte. No es inventario de cajas vacías.','1 caja (corrugado) = 6 botellas; 1 pallet = 80 cajas (480 botellas). Las cajas del desglose están fuera de los pallets; las sueltas están fuera de las cajas. No es inventario de cartón vacío.')
    p.write_text(s)
# Bust changed display scripts; existing data keys, origin and URLs remain intact.
for name in ['control.html','materials.html']:
    p=Path(name);s=p.read_text()
    for asset in ['simple-lot.js','lot-operations.js','reports-data.js']:
        s=re.sub(re.escape(asset)+r'\?v=[^"\s]+',asset+'?v=iphone-pack1',s)
    p.write_text(s)
p=Path('nginx.conf');s=p.read_text()
if 'location = /app.webmanifest' not in s:
    s=s.replace('    location / {','    location = /app.webmanifest {\n        default_type application/manifest+json;\n        add_header Cache-Control "no-cache";\n        try_files $uri =404;\n    }\n    location / {',1);p.write_text(s)
p=Path('Dockerfile');s=p.read_text()
if 'COPY packaging.js device-backup.js pwa.js' not in s:
    s=s.replace('FROM nginx:alpine','COPY packaging.js device-backup.js pwa.js ./\nCOPY tests/device-packaging.cjs ./tests/\nRUN node --check packaging.js && node --check pwa.js && node --check device-backup.js && node tests/device-packaging.cjs\n\nFROM nginx:alpine',1)
    s=s.replace('COPY nginx.conf','COPY app.webmanifest instalar.html packaging.js device-backup.js pwa.js pwa.css /usr/share/nginx/html/\nCOPY icons/ /usr/share/nginx/html/icons/\nCOPY nginx.conf',1)
    s=s.replace('for asset in ','for asset in app.webmanifest instalar.html packaging.js device-backup.js pwa.js pwa.css icons/eb-180.png icons/eb-192.png icons/eb-512.png icons/eb-maskable-512.png ',1);p.write_text(s)
print('Integrated original-logo installation, share, empty-device recovery and exact pack displays. No business data migration.')
