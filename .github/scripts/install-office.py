from pathlib import Path
import re
p=Path('reports-pdf.js');s=p.read_text()
if 'handlesSharedSnapshot:true' not in s:
    s=s.replace("if($('materials-app'))return", "if($('office-app'))return{type:'executive'};\n    if($('materials-app'))return",1)
    s=s.replace("const data=snapshot(),model=window.EBReportData.build(data,ctx,window.EBLedger);", "const row=window.EBShared?.snapshot?await window.EBShared.snapshot():{data:snapshot()};\n    const data=row.data,model=ctx.type==='executive'?window.EBExecutive.build(data,window.EBLedger,row):window.EBReportData.build(data,ctx,window.EBLedger);",1)
    s=s.replace("const gap=10,n=model.metrics.length,cw=(CW-gap*(n-1))/n;room(82);const top=y;", "const gap=10,n=model.metrics.length,cw=(CW-gap*(n-1))/n;doc.setFontSize(7.2);const cardHeight=Math.max(82,...model.metrics.map(m=>65+doc.splitTextToSize(clean(m.note||''),cw-20).length*9));room(cardHeight+8);const top=y;",1)
    s=s.replace("cw,78,6,6,'F'", "cw,cardHeight,6,6,'F'",1).replace("});y+=94;", "});y+=cardHeight+16;",1)
    s=s.replace("paragraph('Sin registros guardados para este apartado.',9);continue;", "paragraph(s.empty||'Sin registros guardados para este apartado.',9);if(s.note)paragraph(s.note,8);continue;",1)
    s=s.replace("y=doc.lastAutoTable.finalY+20;", "y=doc.lastAutoTable.finalY+12;if(s.note)paragraph(s.note,8,MUTED,8);else y+=8;",1)
    s=s.replace("doc.text('ENTRE BESOS  |  Confidencial · Datos locales guardados · No es factura',M,H-21);", "doc.text('ENTRE BESOS | Confidencial | '+(row.revision!==undefined?'Base compartida v'+row.revision:'Datos guardados')+' | No es factura',M,H-21);",1)
    s=s.replace("generate(ctx||context())", "generate(ctx||{type:'executive'})",1)
    s=s.replace("notify('PDF generado con logo y diseño. Solo incluye datos guardados.');return result;", "readyDialog(result,url);notify('PDF listo: puedes descargarlo, abrirlo o compartirlo.');return result;",1)
    at="  async function download(ctx){"
    add="""  function readyDialog(result,url){
    document.getElementById('eb-pdf-ready')?.remove();
    const dialog=document.createElement('dialog');dialog.id='eb-pdf-ready';
    const title=document.createElement('h2');title.textContent='Tu resumen está listo';
    const note=document.createElement('p');note.textContent=result.pages+' páginas con logo y datos guardados. Si no se abrió la descarga, utiliza uno de estos botones.';
    const save=document.createElement('a');save.href=url;save.download=result.name;save.textContent='Descargar PDF';
    const open=document.createElement('a');open.href=url;open.target='_blank';open.rel='noopener';open.textContent='Abrir PDF';
    dialog.append(title,note,save,open);
    const file=new File([result.blob],result.name,{type:'application/pdf'});
    if(navigator.canShare?.({files:[file]})){
      const share=document.createElement('button');share.textContent='Compartir PDF';share.onclick=async()=>{try{await navigator.share({files:[file],title:'Entre Besos · Resumen general'});}catch(e){if(e.name!=='AbortError')note.textContent='No se pudo compartir. Usa Descargar PDF.';}};dialog.append(share);
    }
    const close=document.createElement('button');close.textContent='Volver a la app';close.onclick=()=>dialog.close();dialog.append(close);
    dialog.addEventListener('close',()=>{dialog.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);},{once:true});document.body.append(dialog);dialog.showModal();
  }
"""
    s=s.replace(at,add+at,1)
    s=s.replace("setTimeout(()=>URL.revokeObjectURL(url),120000);readyDialog", "readyDialog",1)
    s=s.replace("window.EBReports={context,generate,download}","window.EBReports={context,generate,download,handlesSharedSnapshot:true}",1)
    s=s.replace("b.title='Descargar reporte PDF con logo';b.setAttribute('aria-label','Descargar reporte PDF con logo')", "b.title='Descargar resumen general con logo';b.setAttribute('aria-label','Descargar resumen general PDF con logo')",1)
    p.write_text(s)
p=Path('shared.js');s=p.read_text()
if 'async function reportSnapshot' not in s:
    s=s.replace("&&!reportPass){", "&&!reportPass&&!window.EBReports?.handlesSharedSnapshot){",1)
    old="window.EBShared={user:null,get revision(){return revision;},flush,get pending(){return!!get(OUT);}};"
    new="""async function reportSnapshot(){
 if(!ready||!who)throw Error('Inicia sesión para generar el reporte.');
 await flush();
 if(get(OUT)||conflict||sending)throw Error('Hay cambios pendientes de guardar. Confirma Actualizado y vuelve a generar el PDF.');
 const row=await api('state');
 if(!row.data)throw Error('Conecta primero la PC con tus datos. No se generará un resumen vacío.');
 return row;
}
window.EBShared={user:null,get revision(){return revision;},flush,snapshot:reportSnapshot,cancelDraft(){touched=false;},get pending(){return!!get(OUT);}};"""
    assert old in s;s=s.replace(old,new,1);p.write_text(s)
for name in ['control.html','materials.html']:
    p=Path(name);s=p.read_text()
    if '/office-nav.js' not in s:
        extra=''
        if name=='materials.html':
            extra=''.join('<script type="application/x-eb-shared" src="/'+x+'?v=office1"></script>' for x in ['commerce-core.js','simple-core.js','corrections-core.js'])
        extra+=''.join('<script type="application/x-eb-shared" src="/'+x+'?v=office1"></script>' for x in ['contacts-core.js','executive-core.js'])
        marker=re.search(r'<script[^>]*src="[^\"]*reports-pdf.js[^>]*>',s)
        assert marker
        s=s[:marker.start()]+extra+s[marker.start():]
        s=s.replace('</head>','<link rel="stylesheet" href="/office.css?v=office1"></head>',1)
        s=s.replace('</body>','<script type="application/x-eb-shared" src="/office-nav.js?v=office1"></script></body>',1)
    for asset in ['reports-pdf.js','shared.js']:
        s=re.sub(re.escape(asset)+r'\?v=[^"\s]+',asset+'?v=office1',s)
    p.write_text(s)
p=Path('index.html');s=p.read_text()
if "if(s==='Reporte socios'||s==='CRM')" not in s:
    s=s.replace('function go(s){',"function go(s){if(s==='Reporte socios'||s==='CRM'){location.href='/office.html?section='+(s==='CRM'?'contacts':'summary');return;}",1)
    s=re.sub(r'shared.js\?v=[^"\s]+','shared.js?v=office1',s);p.write_text(s)
# The legacy page had no explicit head/body. A prior integration inserted its
# shared loader into a report HTML string, prematurely ending the inert script.
p=Path('index.html');s=p.read_text()
if 'id="legacy-shared-loader"' not in s:
    s=re.sub(r'<script src="/shared\.js[^"<>]*" defer></script>','',s)
    s=re.sub(r'<link rel="stylesheet" href="/shared\.css[^"<>]*">','',s)
    s=s.replace('<html lang="es" class="eb-cloud-loading">','<html lang="es" class="eb-cloud-loading"><head>',1)
    assert s.count('<header>')==1
    s=s.replace('<header>','<link rel="stylesheet" href="/shared.css?v=office1"></head><body><header>',1)
    ending='</script></html>'
    assert s.endswith(ending) or s.endswith(ending+'\n')
    s=s.rsplit(ending,1)[0]+'</script><script id="legacy-shared-loader" src="/shared.js?v=office1" defer></script></body></html>\n'
    p.write_text(s)
p=Path('Dockerfile');s=p.read_text()
if 'COPY contacts-core.js executive-core.js' not in s:
    s=s.replace('FROM nginx:alpine AS static','COPY contacts-core.js executive-core.js office-ui.js office-nav.js ./\nCOPY tests/office.cjs ./tests/\nRUN node --check office-ui.js && node --check office-nav.js && node tests/office.cjs\n\nFROM nginx:alpine AS static',1)
    s=s.replace('COPY nginx.conf','COPY office.html office.css office-ui.js office-nav.js contacts-core.js executive-core.js /usr/share/nginx/html/\nCOPY nginx.conf',1)
    s=s.replace('for asset in ','for asset in office.html office.css office-ui.js office-nav.js contacts-core.js executive-core.js ',1)
    p.write_text(s)
print('Integrated global PDF summary, shared snapshot and contacts. No business records changed.')
