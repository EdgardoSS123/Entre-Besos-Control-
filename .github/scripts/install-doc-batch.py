from pathlib import Path
import re
old="['Certificados','Análisis de laboratorio','Asambleas','Acta constitutiva','IMPI']"
new="['Certificados','Análisis de laboratorio','Asambleas','Acta constitutiva','IMPI','COMERCAM','AMMA','FDA','COFEPRIS','Contratos']"
for name in ['documents-ui.js','documents-store.cjs']:
 p=Path(name);s=p.read_text()
 if old in s:s=s.replace(old,new,1)
 else:assert new in s,name
 if name=='documents-ui.js':
  s=s.replace("'Marca y propiedad industrial'];","'Marca y propiedad industrial','Documentación COMERCAM','Documentación AMMA','Documentación FDA','Documentación COFEPRIS','Contratos y convenios'];",1)
  s=s.replace("+icons[i]+'</svg>'","+(icons[i]||icons[0])+'</svg>'",1)
  s=s.replace("if(!r.ok)throw Error(data.error||'No se pudo completar la operación.');", "if(!r.ok)throw Object.assign(Error(data.error||'No se pudo completar la operación.'),{status:r.status});",1)
  s=s.replace("fetch('/api/session',{credentials:'same-origin',cache:'no-store'})","fetch('/api/session',{credentials:'same-origin',cache:'no-store',signal:controller.signal})",1)
  if 'EBDocBatch.open' not in s:
   marker='function open(doc){\n'
   insert="""function open(doc){
 if(!doc&&window.EBDocBatch){let lots=[];try{lots=JSON.parse(localStorage.getItem('eb-v1')).lots.map(l=>l.id);}catch{}return window.EBDocBatch.open({categories,selected,lots,editor,api,dirty:v=>{dirty=v;},saving:v=>{saving=v;},saved:async(category,count,back)=>{selected=category;trash=false;filter='';$('docs-status').value='';await load();window.EBEditReturn?.restore(back);message(count+' archivo'+(count===1?' guardado':'s guardados')+' y confirmado'+(count===1?'':'s')+' en la base compartida.');}});}
"""
   assert s.count(marker)==1;s=s.replace(marker,insert,1)
 p.write_text(s)
p=Path('documents.html');s=p.read_text()
if '/documents-batch.js' not in s:s=s.replace('</body>','<script type="application/x-eb-shared" src="/documents-batch.js?v=batch1"></script></body>',1).replace('</head>','<link rel="stylesheet" href="/documents-batch.css?v=batch1"></head>',1)
s=re.sub(r'documents-ui.js\?v=[^"\s]+','documents-ui.js?v=batch1',s);p.write_text(s)
p=Path('Dockerfile');s=p.read_text()
if 'COPY documents-batch.js' not in s:
 s=s.replace('FROM nginx:alpine AS static','COPY documents-batch.js ./\nRUN node --check documents-batch.js\n\nFROM nginx:alpine AS static',1)
 s=s.replace('COPY nginx.conf','COPY documents-batch.js documents-batch.css /usr/share/nginx/html/\nCOPY nginx.conf',1)
 s=s.replace('for asset in ','for asset in documents-batch.js documents-batch.css ',1);p.write_text(s)
p=Path('tests/browser-documents.py');s=p.read_text().replace('to_have_count(5)','to_have_count(10)').replace('five categories','ten categories');p.write_text(s)
print('Added ten document categories and private multi-file uploads. Existing documents and business records unchanged.')
