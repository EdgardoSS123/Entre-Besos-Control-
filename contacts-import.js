/* Reads selected local XLSX/CSV files only. No automatic imports or third-party uploads. */
(function(root){
'use strict';
const node=typeof module!=='undefined'&&module.exports,C=node?require('./contacts-core.js'):root.EBContacts;
const fields=['name','place','city','state','email','phone'],labels={name:'Nombre del contacto',place:'Lugar / empresa',city:'Ciudad (opcional)',state:'Estado (opcional)',email:'Correo',phone:'Teléfono'};
const text=x=>String(x??'').trim(),norm=x=>text(x).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
const aliases={name:['nombre','nombrecontacto','contacto','contact','contactname','buyer','buyername','person','owner','manager','contactperson','nombrecompleto'],place:['lugar','empresa','negocio','establecimiento','company','companyname','account','accountname','customer','customername','business','businessname','store','storename','venue','venuename','restaurant','restaurantname','location'],city:['ciudad','city','town'],state:['estado','state','region'],email:['correo','correoelectronico','email','emailaddress','contactemail','e-mail'],phone:['telefono','tel','phone','phonenumber','telephone','mobile','cell','cellphone','contactphone','contactnumber']};
function detect(rows){let best={header:0,mapping:Object.fromEntries(fields.map(x=>[x,-1])),score:0};rows.slice(0,50).forEach((r,header)=>{const mapping={},seen=new Set();for(const f of fields){const i=r.findIndex(v=>aliases[f].some(a=>norm(a)===norm(v)));mapping[f]=i;if(i>=0)seen.add(i);}const score=seen.size;if(score>best.score)best={header,mapping,score};});return best;}
function csv(raw){const source=String(raw).replace(/^\uFEFF/,'');const first=source.split(/\r?\n/)[0]||'',sep=first.includes('\t')?'\t':(first.split(';').length>first.split(',').length?';':',');let rows=[],r=[],v='',quoted=false;for(let i=0;i<source.length;i++){const c=source[i];if(c==='"'){if(quoted&&source[i+1]==='"'){v+='"';i++;}else quoted=!quoted;}else if(c===sep&&!quoted){r.push(v);v='';}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&source[i+1]==='\n')i++;r.push(v);if(r.some(text))rows.push(r);r=[];v='';}else v+=c;}if(quoted)throw Error('El CSV tiene comillas sin cerrar.');r.push(v);if(r.some(text))rows.push(r);if(rows.length>10001)throw Error('El archivo supera 10,000 filas.');return rows;}
function candidates(rows,header,mapping,country){
 if(!C.COUNTRIES.includes(country))throw Error('Selecciona un país.');if(mapping.name<0&&mapping.place<0)throw Error('Selecciona una columna para nombre o empresa.');
 const selected=fields.map(f=>mapping[f]).filter(x=>x>=0);if(new Set(selected).size!==selected.length)throw Error('Una columna no puede representar dos campos.');
 const out=[];rows.slice(header+1).forEach((r,i)=>{const val=f=>mapping[f]>=0?text(r[mapping[f]]):'';if(!r.some(text))return;const name=val('name')||val('place');if(!name)return;
  if(norm(name)===norm(rows[header]?.[mapping.name>=0?mapping.name:mapping.place]))return;
  const place=[...new Set(['place','city','state'].map(val).filter(Boolean))].join(' · ');
  const item={country,name,place,email:val('email'),phone:val('phone')};let error='';try{C.validate(item);}catch(e){error=e.message;}out.push({row:header+i+2,item,error});
 });if(out.length>2000)throw Error('Importa hasta 2,000 contactos por archivo.');return out;
}
function same(a,b){a=C.view(a);b=C.view(b);if(a.country!==b.country)return false;return norm(a.name)===norm(b.name)&&((norm(a.place)&&norm(a.place)===norm(b.place))||(['place','email','phone'].every(k=>norm(a[k])===norm(b[k]))));}
function plan(data,input){const rows=C.rows(data),added=[],duplicates=[];for(const r of input){if(r.error)continue;if([...rows,...added.map(x=>x.item)].some(x=>same(x,r.item)))duplicates.push(r);else added.push(r);}return{added,duplicates,invalid:input.filter(x=>x.error)};}
function apply(data,input,meta){const p=plan(data,input);let out=data;for(const r of p.added){out=C.change(out,r.item,{id:meta.id(),stamp:meta.stamp});out.contacts[out.contacts.length-1].importSource={file:meta.file,sheet:meta.sheet,row:r.row};}return{data:out,...p};}
const api={detect,csv,candidates,plan,apply,same};if(node){module.exports=api;return;}root.EBContactImport=api;
const $=id=>document.getElementById(id),esc=x=>text(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function xml(bytes){const str=new TextDecoder().decode(bytes);if(/<!DOCTYPE|<!ENTITY/i.test(str))throw Error('El archivo contiene XML no permitido.');const d=new DOMParser().parseFromString(str,'application/xml');if(d.getElementsByTagName('parsererror').length)throw Error('No se pudo leer una hoja de Excel.');return d;}
const all=(d,name)=>Array.from(d.getElementsByTagNameNS('*',name)),first=(d,name)=>all(d,name)[0],value=d=>all(d,'t').map(x=>x.textContent||'').join('');
function column(ref){let n=0;for(const c of ref.toUpperCase())n=n*26+c.charCodeAt(0)-64;return n-1;}
function xlsx(bytes){
 if(!root.fflate)throw Error('No cargó el lector Excel. Recarga la pantalla.');let size=0;
 const needed=name=>/^xl\/(workbook\.xml|_rels\/workbook\.xml\.rels|sharedStrings\.xml|worksheets\/[^/]+\.xml)$/.test(name);
 const z=root.fflate.unzipSync(bytes,{filter:e=>{if(!needed(e.name))return false;size+=e.originalSize;if(e.originalSize>10*1024*1024||size>25*1024*1024)throw Error('El Excel excede el tamaño permitido.');return true;}});
 if(!z['xl/workbook.xml']||!z['xl/_rels/workbook.xml.rels'])throw Error('No es un Excel .xlsx válido.');
 const strings=z['xl/sharedStrings.xml']?all(xml(z['xl/sharedStrings.xml']),'si').map(value):[];
 const relationships=new Map(all(xml(z['xl/_rels/workbook.xml.rels']),'Relationship').filter(x=>x.getAttribute('TargetMode')!=='External').map(x=>[x.getAttribute('Id'),x.getAttribute('Target')]));
 return all(xml(z['xl/workbook.xml']),'sheet').map(s=>{
  const rid=s.getAttribute('r:id')||s.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id'),target=relationships.get(rid)||'';
  const path=target.startsWith('/')?target.slice(1):'xl/'+target.replace(/^\.\//,'');if(!needed(path)||!z[path])return null;
  const rows=[];let count=0;for(const row of all(xml(z[path]),'row')){if(++count>10001)throw Error('La hoja supera 10,000 filas.');const r=[];for(const c of all(row,'c')){const ref=c.getAttribute('r')||'',m=/^([A-Za-z]+)\d+$/.exec(ref),i=m?column(m[1]):r.length;if(i<0||i>=256)continue;const type=c.getAttribute('t');let v=first(c,'v')?.textContent||'';if(type==='s')v=strings[Number(v)]||'';else if(type==='inlineStr')v=value(c);else if(type==='e')v='';if(text(v).length>5000)throw Error('Una celda excede el tamaño permitido.');r[i]=v;}const n=Number(row.getAttribute('r'))||rows.length+1;if(n>10001)throw Error('La hoja supera 10,000 filas.');while(rows.length<n-1)rows.push([]);rows.push(Array.from({length:r.length},(_,i)=>r[i]||''));}
  return{name:s.getAttribute('name')||'Hoja',rows};
 }).filter(Boolean).filter(s=>s.rows.some(r=>r.some(text)));
}
api.xlsx=xlsx;
const style=document.createElement('style');style.textContent='.eb-contact-import{width:min(850px,calc(100vw - 24px));max-height:90dvh;border:1px solid #dde4ee;border-radius:20px;padding:24px;color:#101827;overflow:auto;box-sizing:border-box}.eb-contact-import::backdrop{background:#10182788}.eb-contact-import h2{margin:0 0 10px}.eb-contact-import label{display:block;font-size:13px;font-weight:600}.eb-contact-import input,.eb-contact-import select{width:100%;min-height:44px;margin:6px 0 14px;font-size:16px;box-sizing:border-box}.eb-import-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 14px}.eb-contact-import table{width:100%;border-collapse:collapse;font-size:12px}.eb-contact-import th,.eb-contact-import td{text-align:left;border-bottom:1px solid #dde4ee;padding:9px;max-width:180px;overflow-wrap:anywhere}.eb-import-scroll{overflow-x:auto;margin:14px 0}.eb-import-info{font-size:13px;line-height:1.6;color:#5d6c84}.eb-import-error{color:#a12a44}.eb-import-buttons{display:flex;flex-wrap:wrap;gap:10px;justify-content:flex-end;margin-top:16px}#contact-import-file{margin:12px 0}#contact-import-button{margin-left:8px}@media(max-width:600px){.eb-import-grid{grid-template-columns:1fr}.eb-contact-import{padding:18px}#contact-import-button{margin:8px 0 0}.eb-import-buttons button{width:100%}}';document.head.append(style);
function read(){const raw=localStorage.getItem('eb-v1'),data=JSON.parse(raw||'null');if(!data||!Array.isArray(data.lots)||!Array.isArray(data.moves))throw Error('No se pudo leer la base compartida.');return{raw,data};}
function open(){
 if(root.EBShared?.user?.role!=='editor')return;
 if(root.EBOffice?.dirty){alert('Guarda o cancela el contacto que estás editando antes de importar.');return;}
 if($('eb-contact-import'))return;
 const d=document.createElement('dialog');d.id='eb-contact-import';d.className='eb-contact-import';const current=document.querySelector('[data-country].selected')?.dataset.country;
 d.innerHTML='<h2>Importar contactos</h2><p class="eb-import-info">Selecciona tu Excel. Revisa la vista previa antes de guardar. No se reemplazan contactos existentes ni se modifican lotes.</p><label>País<select id="ci-country">'+C.COUNTRIES.map(c=>'<option '+((current||'USA')===c?'selected':'')+'>'+c+'</option>').join('')+'</select></label><label>Archivo Excel (.xlsx) o CSV<input id="contact-import-file" type="file" accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"></label><div id="ci-error" role="alert" class="eb-import-error"></div><div id="ci-content"></div><div class="eb-import-buttons"><button class="secondary" id="ci-close">Cerrar</button><button class="primary" id="ci-save" disabled>Importar contactos</button></div>';
 document.body.append(d);d.showModal();let sheets=[],selected=0,fileName='',parsed=[],header=0,mapping={},writing=false;
 const error=e=>{$('ci-error').textContent=e?.message||String(e||'');};
 const close=()=>{if(writing)return;d.close();};$('ci-close').onclick=close;d.onclose=()=>{d.remove();root.EBShared?.cancelDraft?.();};d.addEventListener('cancel',e=>{if(writing)e.preventDefault();});
 function preview(){
  try{error('');header=Number($('ci-header').value)-1;if(!Number.isInteger(header)||header<0||header>=sheets[selected].rows.length)throw Error('Revisa la fila de encabezados.');
   mapping=Object.fromEntries(fields.map(f=>[f,Number($('ci-map-'+f).value)]));parsed=candidates(sheets[selected].rows,header,mapping,$('ci-country').value);const p=plan(read().data,parsed);
   $('ci-count').textContent=p.added.length+' nuevos · '+p.duplicates.length+' coincidencias omitidas · '+p.invalid.length+' filas por corregir. Los datos faltantes quedan en blanco.';
   $('ci-preview').innerHTML='<table><thead><tr><th>Fila</th><th>Nombre</th><th>Lugar</th><th>Correo</th><th>Teléfono</th><th>Resultado</th></tr></thead><tbody>'+parsed.slice(0,50).map(r=>'<tr><td>'+r.row+'</td>'+['name','place','email','phone'].map(f=>'<td>'+esc(r.item[f])+'</td>').join('')+'<td>'+esc(r.error||(p.duplicates.includes(r)?'Ya registrado':'Nuevo'))+'</td></tr>').join('')+'</tbody></table>'+(parsed.length>50?'<p>Vista previa de las primeras 50 filas; la importación incluye todas las filas válidas.</p>':'');
   $('ci-save').disabled=!p.added.length;$('ci-save').textContent='Importar '+p.added.length+' contactos';
  }catch(e){$('ci-save').disabled=true;error(e);}
 }
 function columns(){const rows=sheets[selected].rows,hr=Number($('ci-header').value)-1,head=rows[hr]||[],width=Math.min(256,Math.max(head.length,...rows.slice(hr+1,hr+20).map(x=>x.length)));$('ci-mappings').innerHTML=fields.map(f=>'<label>'+labels[f]+'<select id="ci-map-'+f+'"><option value="-1">Sin columna / dejar vacío</option>'+Array.from({length:width},(_,i)=>'<option value="'+i+'" '+(mapping[f]===i?'selected':'')+'>'+esc((i+1)+': '+(head[i]||'Columna sin título'))+'</option>').join('')+'</select></label>').join('');fields.forEach(f=>$('ci-map-'+f).onchange=preview);preview();}
 function sheet(){const guessed=detect(sheets[selected].rows);header=guessed.header;mapping=guessed.mapping;$('ci-header').value=header+1;columns();}
 $('ci-country').onchange=()=>{if(sheets.length)preview();};
 $('contact-import-file').onchange=async()=>{
  try{error('');$('ci-save').disabled=true;const file=$('contact-import-file').files[0];if(!file)return;if(file.size>5*1024*1024)throw Error('Selecciona un archivo de hasta 5 MB.');fileName=file.name;
   sheets=/\.xlsx$/i.test(file.name)?xlsx(new Uint8Array(await file.arrayBuffer())):/\.csv$/i.test(file.name)?[{name:'CSV',rows:csv(await file.text())}]:(()=>{throw Error('Selecciona un archivo .xlsx o .csv.');})();
   if(!sheets.length)throw Error('No encontré hojas con contenido.');selected=sheets.reduce((best,s,i)=>detect(s.rows).score>detect(sheets[best].rows).score?i:best,0);
   $('ci-content').innerHTML='<div class="eb-import-grid"><label>Hoja<select id="ci-sheet">'+sheets.map((s,i)=>'<option value="'+i+'" '+(i===selected?'selected':'')+'>'+esc(s.name)+'</option>').join('')+'</select></label><label>Fila de encabezados<input id="ci-header" type="number" min="1" max="10001"></label></div><details><summary>Revisar columnas</summary><p class="eb-import-info">Si falta el nombre de la persona, se usa el nombre de la empresa del archivo. No se inventan correos ni teléfonos.</p><div id="ci-mappings" class="eb-import-grid"></div></details><p id="ci-count" class="eb-import-info"></p><div id="ci-preview" class="eb-import-scroll"></div>';
   $('ci-sheet').onchange=()=>{selected=Number($('ci-sheet').value);sheet();};$('ci-header').onchange=()=>{mapping=detect([sheets[selected].rows[Number($('ci-header').value)-1]||[]]).mapping;columns();};sheet();
  }catch(e){error(e);$('ci-content').innerHTML='';$('ci-save').disabled=true;}
 };
 $('ci-save').onclick=async()=>{
  if(writing)return;writing=true;const b=$('ci-save');b.disabled=true;$('ci-close').disabled=true;
  try{error('');if(root.EBShared?.pending)throw Error('Hay cambios pendientes de sincronizar. Espera a que diga Actualizado antes de importar.');
   const before=read(),result=apply(before.data,parsed,{id:()=>crypto.randomUUID(),stamp:new Date().toISOString(),file:fileName,sheet:sheets[selected].name});if(!result.added.length)throw Error('No hay contactos nuevos; las coincidencias ya existen.');
   if(localStorage.getItem('eb-v1')!==before.raw)throw Error('La base cambió en otra pestaña. Revisa la vista previa de nuevo.');
   if(!localStorage.getItem('eb-before-contact-import-v1'))localStorage.setItem('eb-before-contact-import-v1',before.raw);
   localStorage.setItem('eb-v1',JSON.stringify(result.data));root.EBShared?.cancelDraft?.();root.EBOffice?.render?.();
   document.querySelector('[data-country="'+$('ci-country').value+'"]')?.click();
   $('ci-content').innerHTML='<p class="eb-import-info">'+result.added.length+' contactos guardados. '+result.duplicates.length+' coincidencias omitidas. Revisa «Actualizado» para confirmar el envío a la base compartida.</p>';
   b.textContent='Guardados';$('contact-import-file').disabled=true;$('ci-country').disabled=true;
   if(root.EBShared?.snapshot){try{const row=await root.EBShared.snapshot();const ids=new Set(result.added.map((_,i)=>result.data.contacts[result.data.contacts.length-result.added.length+i].id));const found=(row.data.contacts||[]).filter(c=>ids.has(c.id)).length;if(found===ids.size)$('ci-content').innerHTML='<p class="eb-import-info"><strong>'+found+' contactos confirmados en la base compartida.</strong> Ya pueden consultarse desde PC y celular. No se modificaron lotes, ventas ni inventarios.</p>';else error('Revisa la sincronización: no se confirmaron todos los contactos.');}catch(e){error('Guardados en este dispositivo; todavía no se confirma la sincronización. '+e.message);}}
  }catch(e){error(e);b.disabled=false;}finally{writing=false;$('ci-close').disabled=false;}
 };
}
function attach(){const n=$('contact-new');if(!n||$('contact-import-button')||root.EBShared?.user?.role!=='editor')return;const b=document.createElement('button');b.id='contact-import-button';b.className='secondary';b.textContent='Importar Excel';b.type='button';b.onclick=open;n.insertAdjacentElement('afterend',b);}
const host=$('office-app');if(host){new MutationObserver(attach).observe(host,{childList:true,subtree:true});attach();}
})(typeof window==='undefined'?globalThis:window);
