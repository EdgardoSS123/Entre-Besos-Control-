from pathlib import Path
import re
for name in ['control.html','materials.html','index.html']:
    p=Path(name);s=p.read_text()
    if 'shared.js?v=' not in s:
        s=re.sub(r'<script(\s|>)',r'<script type="application/x-eb-shared"\1',s)
        s=s.replace('<html lang="es">','<html lang="es" class="eb-cloud-loading">',1)
        s=s.replace('</head>','<link rel="stylesheet" href="/shared.css?v=shared1"></head>',1)
        s=s.replace('</body>','<script src="/shared.js?v=shared1" defer></script></body>',1)
        p.write_text(s)
p=Path('pwa.js');s=p.read_text()
s=s.replace('Protege tus datos antes de instalar.','La misma información en PC y celular.')
s=s.replace('Los registros se guardan en este navegador. El acceso instalado puede tener almacenamiento separado; todavía no hay sincronización entre dispositivos. Guarda un respaldo antes de instalar o cambiar de acceso.','Inicia sesión con tu usuario de socio. Los datos guardados se comparten con la PC y los demás accesos autorizados. La primera vez, conecta la PC donde capturaste tus registros. Respaldo sigue disponible como copia adicional.')
s=s.replace('¿La app instalada aparece vacía?','¿Todavía no aparecen tus datos?')
s=s.replace('Recupera el archivo JSON generado con Respaldo. Solo se permite en un dispositivo vacío: nunca reemplaza registros existentes ni combina bases.','Entra primero desde la PC con tus datos y pulsa «Usar estos datos como base compartida». Después entra con tu usuario en el iPhone. No necesitas importar un respaldo en cada dispositivo.')
if "document.querySelector('.eb-app-recovery')?.querySelectorAll" not in s:
    s=s.replace('function bind(){', "function bind(){\n    document.querySelector('.eb-app-recovery')?.querySelectorAll('input,label,#eb-restore-preview').forEach(x=>x.hidden=true);",1)
p.write_text(s)
p=Path('reports-pdf.js');s=p.read_text().replace('Información guardada en este navegador al generar el documento.','Información guardada en la base compartida al generar el documento.');p.write_text(s)
p=Path('shared.js');s=p.read_text()
if 'seenSignature' not in s:
    s=s.replace("let shell,timer,reportPass=false", "let seenSignature=null;\nlet shell,timer,reportPass=false",1)
    s=s.replace('Storage.prototype.setItem=function(k,v){', "Storage.prototype.getItem=function(k){const raw=nativeGet.call(this,k);if(this===localStorage&&String(k)===KEY&&raw)seenSignature=signature(raw);return raw;};\nStorage.prototype.setItem=function(k,v){",1)
    s=s.replace("checkData(raw);\n const previous=get(OUT)", "checkData(raw);\n if(seenSignature&&get(KEY)&&seenSignature!==signature(get(KEY)))throw Error('Otra pestaña cambió los datos. Conserva tu captura y actualiza antes de guardar.');\n const previous=get(OUT)",1)
    s=s.replace("touched=false;status('Guardado local", "seenSignature=signature(raw);touched=false;status('Guardado local",1)
    s=s.replace("const row=await api('state?since='+revision);if(row.unchanged)", "const row=await api('state?since='+revision);if(get(OUT)||sending)return;if(row.unchanged)",1)
    s=s.replace("await api('session');await poll(true);", "await api('session');await poll();",1)
    p.write_text(s)
p=Path('Dockerfile');s=p.read_text()
if 'server.cjs' not in s:
    s=s.replace('FROM nginx:alpine','COPY server.cjs shared.js ./\nCOPY tests/shared-server.cjs ./tests/\nRUN node --check server.cjs && node --check shared.js && node --experimental-sqlite tests/shared-server.cjs\n\nFROM nginx:alpine AS static',1)
    s+='\nFROM node:22-alpine AS shared\nWORKDIR /app\nCOPY --from=static /usr/share/nginx/html/ ./public/\nCOPY server.cjs ./server.cjs\nCOPY shared.js shared.css ./public/\nENV PORT=80\nEXPOSE 80\nCMD ["node", "--experimental-sqlite", "server.cjs"]\n'
    p.write_text(s)
print('Shared storage integrated without migrating or modifying any business records.')
