(function () {
  'use strict';
  const KEY='eb-v1', OTHER='__eb_other__', C=window.EBMaterials, $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money=n=>new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(n), number=n=>new Intl.NumberFormat('es-MX').format(n);
  let kind=new URLSearchParams(location.search).get('kind')==='supplies'?'supplies':'marketing', snapshot, editing=null, custom=false, changed=false, busy=false, toastTimer;
  const title=()=>kind==='marketing'?'Material marketing':'Inventario de insumos';
  function read() { const raw=localStorage.getItem(KEY), d=raw===null?{lots:[],moves:[],contacts:[],costs:{}}:JSON.parse(raw); if(!d||!Array.isArray(d.lots)||!Array.isArray(d.moves))throw Error('No se pudieron leer los datos. No se reiniciaron ni borraron.'); C.records(d,kind); return {raw,data:d}; }
  function locations(d) { const base=window.EBLedger?.locations(d)||['Oaxaca','CDMX','USA','Singapur']; return [...new Set([...base,...C.records(d,kind).map(x=>x.loc).filter(x=>typeof x==='string'&&x)])]; }
  function options(values,empty) { return '<option value="">'+esc(empty)+'</option>'+values.map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join(''); }
  function toast(s) { $('materials-toast').textContent=s;$('materials-toast').classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('materials-toast').classList.add('hidden'),4500); }
  function error(s) { const box=$('material-error');box.textContent=s;box.classList.remove('hidden'); }
  function discard() { return !changed||confirm('Hay una captura sin guardar. ¿Salir sin guardarla? Los registros guardados se conservan.'); }
  function open(next) { if(!discard())return;kind=next;editing=null;custom=false;changed=false;history.replaceState(null,'','?kind='+kind);render();window.scrollTo(0,0); }
  function setCustom(active,focus=false){
    custom=active;
    const input=$('material-custom-name'),select=$('material-name');
    input.classList.toggle('hidden',!active);input.required=active;input.disabled=!active;
    $('material-custom-label').classList.toggle('hidden',!active);
    select.disabled=false;select.required=true;
    if(active)select.value=OTHER;else if(select.value===OTHER)select.value='';
    $('material-custom').textContent=active?'Elegir del catálogo':'+ Otro insumo';
    if(focus)(active?input:select).focus();
  }
  function render() {
    document.title='Entre Besos · '+title();$('inventory-crumb').textContent=title();document.querySelectorAll('[data-kind]').forEach(b=>b.classList.toggle('active',b.dataset.kind===kind));
    try {snapshot=read();C.records(snapshot.data,'supplies');}
    catch(e){$('materials-app').innerHTML='<div class="heading"><h1>'+title()+'</h1></div><div class="alert">'+esc(e.message)+' Exporta un respaldo antes de continuar.</div>';return;}
    const supplies=kind==='supplies', names=C.catalog(snapshot.data);
    $('materials-app').innerHTML='<div class="heading"><div><div class="eyebrow">EXISTENCIAS Y COSTOS</div><h1>'+title()+'</h1><p class="muted">'+(supplies?'Elige el insumo; captura cantidad y costo total.':'Escribe el concepto; captura cantidad y costo total.')+'</p></div><button class="secondary" id="material-new">+ Nueva captura</button></div><div class="material-layout"><section class="card material-form"><div class="card-head"><h2 id="material-form-title">Nueva captura</h2></div><div class="card-body"><form id="material-form"><div id="material-error" class="alert material-error hidden" role="alert"></div><div class="fields"><div class="field wide"><label for="material-name">'+(supplies?'Insumo *':'Concepto *')+'</label>'+(supplies?'<select id="material-name" required>'+options(names,'Selecciona un insumo')+'<option value="'+OTHER+'">Otros</option></select><button class="material-add-custom" type="button" id="material-custom">+ Otro insumo</button><label class="hidden" id="material-custom-label" for="material-custom-name">Especifica el concepto *</label><input class="hidden" id="material-custom-name" maxlength="160" aria-label="Nombre del nuevo insumo" placeholder="Escribe el nombre" disabled>':'<input id="material-name" maxlength="160" autocomplete="off" required value="">')+'</div><div class="field wide"><label for="material-location">Bodega / ubicación *</label><select id="material-location" required>'+options(locations(snapshot.data),'Selecciona la bodega')+'</select></div><div class="field wide"><label for="material-presentation">Presentación / capacidad <span class="muted">(opcional)</span></label><input id="material-presentation" maxlength="120" list="material-presentations" value=""><datalist id="material-presentations">'+(supplies?['700 ml','720 ml','Completo','Medio'].map(x=>'<option value="'+x+'">').join(''):'')+'</datalist></div><div class="field"><label for="material-qty">Cantidad en existencia *</label><input id="material-qty" type="number" inputmode="numeric" min="0" max="1000000000000" step="1" required value=""></div><div class="field"><label for="material-cost">Costo total · MXN *</label><input id="material-cost" type="number" inputmode="decimal" min="0" max="1000000000000" step="0.01" required value=""></div></div><div class="material-unit-cost"><div><small>COSTO POR UNIDAD</small><span class="material-hint">Total ÷ cantidad</span></div><strong id="material-unit">—</strong></div><button class="primary material-save" id="material-save" type="submit">Guardar inventario</button><button class="secondary material-cancel hidden" type="button" id="material-cancel">Cancelar edición</button><p class="material-form-note">Captura el costo de toda la cantidad registrada, no el precio unitario. Usa 0 solo cuando realmente no tuvo costo.</p></form></div></section><section aria-label="Inventario registrado"><div class="material-filters"><input id="material-search" type="search" aria-label="Buscar concepto" placeholder="Buscar concepto o presentación"><select id="material-filter" aria-label="Filtrar por bodega">'+options(locations(snapshot.data),'Todas las bodegas')+'</select></div><div id="material-summary" class="material-summary"></div><div id="material-list"></div><p class="material-hint">Existencias capturadas manualmente. No se descuentan al guardar un lote ni cambian sus costos.</p><div id="material-history"></div></section></div>';
    $('material-new').onclick=()=>{if(discard()){editing=null;custom=false;changed=false;render();$('material-name').focus();}};
    $('material-cancel').onclick=()=>{if(discard()){editing=null;custom=false;changed=false;render();}};
    $('material-form').addEventListener('input',()=>{changed=true;preview();});$('material-form').addEventListener('change',()=>{changed=true;preview();});
    if(supplies){
      $('material-custom').onclick=()=>{setCustom(!custom,true);changed=true;};
      $('material-name').onchange=()=>{setCustom($('material-name').value===OTHER,true);changed=true;};
    }
    $('material-form').onsubmit=e=>{e.preventDefault();save();};$('material-search').oninput=draw;$('material-filter').onchange=draw;draw();preview();
  }
  function preview() { const q=$('material-qty').value,c=$('material-cost').value,n=Number(q),total=Number(c);$('material-unit').textContent=q!==''&&c!==''&&Number.isInteger(n)&&n>0&&Number.isFinite(total)&&total>=0?money(total/n):'—'; }
  function draw() {
    const d=snapshot.data, search=$('material-search').value.trim().toLocaleLowerCase('es'), loc=$('material-filter').value;
    const rows=C.records(d,kind).map((r,index)=>({r,index})).filter(({r})=>(!loc||r.loc===loc)&&[r.name,r.presentation].join(' ').toLocaleLowerCase('es').includes(search));
    let total=0,missing=0;rows.forEach(({r})=>{const c=C.cost(r);if(c===null)missing++;else total+=c;});
    $('material-summary').innerHTML='<div><strong>'+rows.length+'</strong><p>registros'+(loc?' · '+esc(loc):'')+'</p></div><div class="material-value"><strong>'+money(total)+'</strong><p>Costo total capturado'+(missing?' · '+missing+' sin costo':'')+'</p></div>';
    $('material-list').innerHTML=rows.length?rows.map(({r,index})=>{const c=C.cost(r),unit=c!==null&&Number(r.qty)>0?c/Number(r.qty):null;return '<article class="material-record" data-record="'+index+'"><h3>'+esc(r.name)+'</h3><p class="muted">'+esc(r.loc||'Ubicación pendiente')+(r.presentation?' · '+esc(r.presentation):'')+'</p><div class="material-record-values"><div><small>CANTIDAD EN EXISTENCIA</small><strong>'+number(Number(r.qty)||0)+'</strong> <span class="muted">'+esc(r.unit||'unidades')+'</span></div><div class="material-value"><small>COSTO TOTAL · MXN</small><strong>'+(c===null?'Sin capturar':money(c))+'</strong></div></div><p class="muted">Costo por unidad: '+(unit===null?'—':money(unit))+'</p><div class="actions"><button class="secondary" data-edit-material="'+index+'">Editar</button><button class="secondary material-delete" data-delete-material="'+index+'">Eliminar</button></div></article>';}).join(''):'<div class="empty"><h2>'+((search||loc)?'Sin coincidencias':'Sin inventario capturado')+'</h2><p>'+((search||loc)?'Cambia la búsqueda o la bodega.':'Agrega tu primer registro. No se han inventado cantidades ni costos.')+'</p></div>';
    document.querySelectorAll('[data-edit-material]').forEach(b=>b.onclick=()=>edit(Number(b.dataset.editMaterial)));document.querySelectorAll('[data-delete-material]').forEach(b=>b.onclick=()=>remove(Number(b.dataset.deleteMaterial)));
    const logs=(Array.isArray(d.materialInventoryHistory)?d.materialInventoryHistory:[]).filter(x=>x.kind===kind).slice(-20).reverse();
    $('material-history').innerHTML=logs.length?'<details class="material-history"><summary>Historial de cambios</summary>'+logs.map(x=>'<p>'+esc(new Date(x.at).toLocaleString('es-MX'))+' · '+({create:'Alta',update:'Edición',delete:'Eliminado'}[x.action]||'Cambio')+' · '+esc((x.after||x.before)?.name||'')+'<br>'+esc((x.after||x.before)?.loc||'')+' · '+esc(x.after?.qty??x.before?.qty??'')+' unidades</p>').join('')+'</details>':'';
  }
  let materialReturn=null;
  function edit(index) {
    if(!discard())return;materialReturn=window.EBEditReturn?.capture();const r=C.records(snapshot.data,kind)[index];if(!r)return;editing={index,expected:JSON.stringify(r)};custom=false;changed=false;$('material-form').reset();
    if($('material-custom-name'))setCustom(false);
    $('material-name').value=r.name;$('material-location').value=r.loc||'';$('material-presentation').value=r.presentation||'';$('material-qty').value=r.qty??'';$('material-cost').value=C.cost(r)??'';
    $('material-form-title').textContent='Editar registro';$('material-save').textContent='Guardar cambios';$('material-cancel').classList.remove('hidden');$('material-error').classList.add('hidden');preview();$('material-form-title').scrollIntoView({block:'start',behavior:'smooth'});$('material-name').focus({preventScroll:true});
  }
  function persist(input,opts) {
    const current=read(), result=C.change(current.data,kind,input,{...opts,id:crypto.randomUUID(),stamp:new Date().toISOString()});
    if(localStorage.getItem(KEY)!==current.raw)throw Error('Los datos cambiaron en otra pestaña. Vuelve a abrir el registro.');
    if(current.raw&&!localStorage.getItem('eb-before-materials-v1'))localStorage.setItem('eb-before-materials-v1',current.raw);
    localStorage.setItem(KEY,JSON.stringify(result));snapshot={data:result,raw:JSON.stringify(result)};
  }
  function save() {
    if(busy)return;busy=true;$('material-save').disabled=true;$('material-error').classList.add('hidden');
    try {
      const selected=$('material-location').value;if(!locations(read().data).includes(selected))throw Error('Selecciona una bodega válida.');
      persist({name:custom?$('material-custom-name').value:$('material-name').value,custom,loc:selected,presentation:$('material-presentation').value,qty:$('material-qty').value,totalCost:$('material-cost').value,unit:'unidades'},editing||{});
      const back=editing?materialReturn:null;editing=null;custom=false;changed=false;render();window.EBEditReturn?.restore(back);window.EBShared?.cancelDraft?.();materialReturn=null;toast('Inventario guardado. Cantidad y costo total registrados.');
    } catch(e) {error('No se guardó. '+e.message);} finally{busy=false;if($('material-save'))$('material-save').disabled=false;}
  }
  function remove(index) {
    if(!discard())return;const record=C.records(snapshot.data,kind)[index];if(!record||!confirm('¿Eliminar «'+record.name+'» de '+record.loc+'? Este cambio no afecta tus lotes.'))return;
    try{persist(null,{index,expected:JSON.stringify(record),remove:true});editing=null;custom=false;changed=false;render();toast('Registro eliminado. El cambio quedó en el historial.');}catch(e){error('No se eliminó. '+e.message);}
  }
  function backup(){try{const raw=localStorage.getItem(KEY)||JSON.stringify(read().data),url=URL.createObjectURL(new Blob([raw],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='Entre-Besos-respaldo-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}catch(e){toast('No se pudo exportar. '+e.message);}}
  document.querySelectorAll('[data-kind]').forEach(b=>b.onclick=()=>open(b.dataset.kind));document.querySelectorAll('[data-lots]').forEach(b=>b.onclick=()=>{if(discard())location.href='./';});document.querySelectorAll('[data-backup]').forEach(b=>b.onclick=backup);
  document.querySelectorAll('a').forEach(a=>a.addEventListener('click',e=>{if(!discard())e.preventDefault();}));
  window.addEventListener('beforeunload',e=>{if(changed){e.preventDefault();e.returnValue='';}});
  window.addEventListener('storage',e=>{if(e.key!==KEY)return;if(changed||editing){error('Los datos cambiaron en otra pestaña. Tu captura sigue aquí; se verificará antes de guardar.');return;}render();});
  render();
})();
