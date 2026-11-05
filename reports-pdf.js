(function(){
  'use strict';
  const $=id=>document.getElementById(id), INK=[16,24,39], PINK=[217,0,116], MUTED=[93,108,132], LINE=[221,228,238];
  let busy=false,logoPromise=null;
  const clean=s=>String(s??'').replace(/\u2192/g,' > ').replace(/[\u2013\u2014\u2212]/g,'-').replace(/[\u2018\u2019]/g,"'").replace(/[\u201c\u201d]/g,'"').replace(/\u2026/g,'...').replace(/\u00a0/g,' ');
  function notify(message,error=false){
    let el=$('eb-pdf-status');if(!el){el=document.createElement('div');el.id='eb-pdf-status';el.setAttribute('role','status');el.style.cssText='position:fixed;bottom:100px;left:50%;transform:translateX(-50%);z-index:9999;background:#101827;color:white;padding:14px 18px;border-radius:12px;max-width:90vw;font:14px system-ui;box-shadow:0 8px 24px #0003';document.body.append(el);}
    el.textContent=message;el.hidden=false;el.setAttribute('role',error?'alert':'status');clearTimeout(el._timer);el._timer=setTimeout(()=>{el.hidden=true;},error?14000:6500);
  }
  function snapshot(){const raw=localStorage.getItem('eb-v1');const d=raw===null?{lots:[],moves:[]}:JSON.parse(raw);if(!d||!Array.isArray(d.lots)||!Array.isArray(d.moves))throw Error('No se pudieron leer los registros guardados.');return d;}
  function context(){
    if($('materials-app'))return{type:new URLSearchParams(location.search).get('kind')==='supplies'?'supplies':'marketing',location:$('material-filter')?.value||'',search:$('material-search')?.value.trim()||''};
    if($('warehouse-filter'))return{type:'warehouse',location:$('warehouse-filter').value};
    if($('simple-produced'))return{type:'lot',lotId:document.querySelector('#app .heading h1')?.textContent.trim(),historyLocation:$('history-warehouse')?.value||''};
    if($('lot-id'))return{type:'lot',lotId:$('lot-id').value.trim()};
    return{type:'general',search:$('search-lots')?.value.trim()||''};
  }
  function logo(){
    if(!logoPromise)logoPromise=fetch('./EB%20logo.jpg',{cache:'force-cache'}).then(r=>{if(!r.ok)throw Error('No se pudo cargar el logo. Recarga la app y vuelve a generar el PDF.');return r.arrayBuffer();}).then(b=>new Uint8Array(b)).catch(e=>{logoPromise=null;throw e;});
    return logoPromise;
  }
  async function generate(ctx){
    const data=snapshot(),model=window.EBReportData.build(data,ctx,window.EBLedger);
    if(!window.jspdf?.jsPDF)throw Error('No se cargó el generador PDF. Recarga esta pantalla.');
    const image=await logo(),{jsPDF}=window.jspdf,doc=new jsPDF({orientation:'portrait',unit:'pt',format:'letter',compress:true});
    if(typeof doc.autoTable!=='function')throw Error('No se cargaron las tablas PDF. Recarga esta pantalla.');
    const W=612,H=792,M=40,CW=W-2*M,TOP=110,BOTTOM=H-48;
    const generated=new Date(),date=generated.toLocaleString('es-MX',{timeZone:'America/Mexico_City',dateStyle:'medium',timeStyle:'short'});
    const img=doc.getImageProperties(image);const ratio=img.width/img.height,iw=Math.min(84,58*ratio),ih=iw/ratio;
    doc.setProperties({title:'Entre Besos | '+clean(model.title),subject:clean(model.scope),author:'SAGAV Cuatro - Entre Besos',creator:'Entre Besos Control'});
    doc.setLineHeightFactor(1.3);let y=TOP;
    function room(height){if(y+height>BOTTOM){doc.addPage();y=TOP;}}
    function paragraph(value,size=9,color=MUTED){
      doc.setFont('helvetica','normal');doc.setFontSize(size);doc.setTextColor(...color);const lines=doc.splitTextToSize(clean(value),CW);
      for(const line of lines){room(size*1.35+3);doc.text(line,M,y+size);y+=size*1.35;}y+=8;
    }
    doc.setFont('helvetica','bold');doc.setFontSize(13);doc.setTextColor(...INK);const sub=doc.splitTextToSize(clean(model.subtitle),CW);doc.text(sub,M,y+13);y+=sub.length*17+5;
    paragraph('Alcance: '+model.scope,9);
    if(model.metrics.length){
      const gap=10,n=model.metrics.length,cw=(CW-gap*(n-1))/n;room(82);const top=y;
      model.metrics.forEach((m,i)=>{
        const x=M+i*(cw+gap);doc.setFillColor(245,247,251);doc.roundedRect(x,top,cw,78,6,6,'F');doc.setFillColor(...PINK);doc.roundedRect(x,top+12,3,20,1,1,'F');
        doc.setFont('helvetica','normal');doc.setFontSize(7.2);doc.setTextColor(...MUTED);doc.text(doc.splitTextToSize(clean(m.label),cw-20),x+10,top+14);
        let fs=21;doc.setFont('helvetica','bold');doc.setFontSize(fs);while(doc.getTextWidth(clean(m.value))>cw-20&&fs>10){doc.setFontSize(--fs);}doc.setTextColor(...INK);doc.text(clean(m.value),x+10,top+43);
        doc.setFont('helvetica','normal');doc.setFontSize(7.2);doc.setTextColor(...MUTED);doc.text(doc.splitTextToSize(clean(m.note||''),cw-20),x+10,top+59);
      });y+=94;
    }
    for(const s of model.sections){
      room(64);doc.setFont('helvetica','bold');doc.setFontSize(12);doc.setTextColor(...INK);doc.text(clean(s.title),M,y+12);y+=21;
      if(!s.body.length){paragraph('Sin registros guardados para este apartado.',9);continue;}
      const styles={};(s.right||[]).forEach(i=>styles[i]={halign:'right'});
      doc.autoTable({startY:y,head:[s.head.map(clean)],body:s.body.map(r=>r.map(clean)),margin:{top:TOP,right:M,bottom:48,left:M},tableWidth:CW,theme:'striped',showHead:'everyPage',rowPageBreak:'avoid',
        styles:{font:'helvetica',fontSize:8.5,cellPadding:6,textColor:INK,lineColor:LINE,lineWidth:0.3,overflow:'linebreak',valign:'middle'},
        headStyles:{fillColor:INK,textColor:[255,255,255],fontStyle:'bold',fontSize:8.2,lineWidth:0},alternateRowStyles:{fillColor:[247,249,252]},columnStyles:styles});
      y=doc.lastAutoTable.finalY+20;
    }
    room(50);doc.setDrawColor(...LINE);doc.line(M,y,W-M,y);y+=12;
    for(const note of model.notes)paragraph(note,8);
    paragraph('Información guardada en este navegador al generar el documento. No incluye capturas sin guardar. Control interno; no es una factura ni un conteo físico certificado.',8);
    const count=doc.getNumberOfPages();
    for(let p=1;p<=count;p++){
      doc.setPage(p);doc.addImage(image,'JPEG',M+(84-iw)/2,24+(58-ih)/2,iw,ih,'eb-logo');
      doc.setTextColor(...PINK);doc.setFont('helvetica','bold');doc.setFontSize(8);doc.text('SAGAV CUATRO  /  CONTROL INTERNO',140,31);
      doc.setTextColor(...INK);doc.setFontSize(21);doc.text(clean(model.title),140,56);
      doc.setFont('helvetica','normal');doc.setTextColor(...MUTED);doc.setFontSize(8.5);doc.text(clean('Generado: '+date+' · CDMX'),140,74);
      doc.setDrawColor(...PINK);doc.setLineWidth(1.5);doc.line(M,94,W-M,94);
      doc.setLineWidth(.5);doc.setDrawColor(...LINE);doc.line(M,H-35,W-M,H-35);
      doc.setFontSize(7.5);doc.setTextColor(...MUTED);doc.text('ENTRE BESOS  |  Confidencial · Uso de socios',M,H-21);doc.text('Página '+p+' de '+count,W-M,H-21,{align:'right'});
    }
    const slug=clean(model.file).normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^A-Za-z0-9_-]/g,'-').slice(0,80);
    const localDate=generated.toLocaleDateString('en-CA',{timeZone:'America/Mexico_City'});
    return{blob:doc.output('blob'),name:'Entre-Besos-'+slug+'-'+localDate+'.pdf',model,pages:count};
  }
  async function download(ctx){
    if(busy)return;busy=true;const button=$('eb-report-pdf');if(button){button.disabled=true;button.textContent='PDF...';}
    try{
      const result=await generate(ctx||context()),url=URL.createObjectURL(result.blob),a=document.createElement('a');a.href=url;a.download=result.name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),120000);notify('PDF generado con logo y diseño. Solo incluye datos guardados.');return result;
    }catch(e){notify('No se generó el PDF. '+e.message,true);return null;}
    finally{busy=false;if(button){button.disabled=false;button.textContent='PDF';}}
  }
  const controls=document.querySelector('.topbar .controls-row');
  if(controls&&!$('eb-report-pdf')){const b=document.createElement('button');b.className='secondary';b.id='eb-report-pdf';b.type='button';if(b.textContent!=='PDF')b.textContent='PDF';b.title='Descargar reporte PDF con logo';b.setAttribute('aria-label','Descargar reporte PDF con logo');b.onclick=()=>download();controls.prepend(b);}
  document.addEventListener('click',e=>{
    const b=e.target instanceof Element?e.target.closest('#simple-print,[data-print],#print-stock'):null;if(!b)return;
    e.preventDefault();e.stopImmediatePropagation();download(b.dataset.print?{type:'lot',lotId:b.dataset.print}:context());
  },true);
  const rename=()=>{document.querySelectorAll('#simple-print,#print-stock').forEach(b=>{if(b.textContent!=='PDF')b.textContent='PDF';b.title='Descargar reporte PDF con logo';});};
  const app=$('app');if(app){const observer=new MutationObserver(rename);observer.observe(app,{childList:true,subtree:true});rename();}
  window.EBReports={context,generate,download};
})();
