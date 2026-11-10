(function(){
'use strict';
const O=window.EBMaterialMoves,$=id=>document.getElementById(id),KEY='eb-v1';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=n=>new Intl.NumberFormat('es-MX').format(n),money=(n,c='MXN')=>new Intl.NumberFormat('es-MX',{style:'currency',currency:c}).format(n);
const labels={used:'Utilizado',received:'Recibido',transit:'En tránsito',cancelled:'Anulado'};
const today=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const editor=()=>window.EBShared?.user?.role==='editor';
let context=null,dialog=null,busy=false,dirty=false,pending=null;
function read(){const raw=localStorage.getItem(KEY),data=JSON.parse(raw||'null');if(!data||!Array.isArray(data.lots)||!Array.isArray(data.moves))throw Error('No se pudo leer la información compartida. No se borraron datos.');return{raw,data};}
function message(s,bad=false){const el=$('material-move-message');if(el){el.textContent=s;el.dataset.error=String(bad);}}
function issue(s){const el=$('mm-error');if(el){el.textContent=s;el.hidden=!s;if(s)el.scrollIntoView({block:'nearest'});}else message(s,true);}
function mount(ctx){
 context=ctx;const host=$('material-movement-history');if(!host)return;
 document.querySelectorAll('.material-record').forEach(card=>{
  const index=Number(card.dataset.record),bar=card.querySelector('.actions');
  if(!bar||!editor()||bar.querySelector('[data-material-move]'))return;
  const controls=document.createElement('div');controls.className='material-operation-actions';controls.innerHTML='<button type="button" class="primary" data-material-move="'+index+'">Mover</button><button type="button" class="secondary" data-material-use="'+index+'">Registrar uso</button>';
  bar.before(controls);controls.querySelector('[data-material-move]').onclick=()=>open(index,'transfer');controls.querySelector('[data-material-use]').onclick=()=>open(index,'use');
 });
 const all=O.moves(ctx.data).filter(m=>m.kind===ctx.kind),q=(ctx.search||'').trim().toLocaleLowerCase('es'),loc=ctx.location;
 const list=all.filter(m=>(!loc||m.from===loc||m.to===loc)&&(!q||[m.name,m.presentation,m.purpose,m.lotId,m.from,m.to].join(' ').toLocaleLowerCase('es').includes(q))).slice().sort((a,b)=>(b.date||'').localeCompare(a.date||'')||(b.createdAt||'').localeCompare(a.createdAt||''));
 const transit=list.filter(m=>m.status==='transit');
 host.innerHTML='<div id="material-move-message" role="status"></div><div class="mm-history-heading"><h2>Movimientos y usos</h2><small>'+list.length+' registros</small></div>'+(transit.length?'<div class="mm-in-transit"><b>En tránsito — pendiente de recepción</b>'+transit.map(m=>'<p>'+esc(m.name)+(m.presentation?' · '+esc(m.presentation):'')+': '+number(m.quantity)+' '+esc(m.unit)+' · '+esc(m.from)+' → '+esc(m.to)+'</p>').join('')+'<small>Ya salió del origen. Se suma al destino al marcar Recibido.</small></div>':'')+(list.length?list.map(m=>'<article class="mm-history-record" data-movement="'+esc(m.id)+'"><div class="mm-history-head"><div><b>'+esc(m.name)+'</b><small>'+esc(m.date)+' · '+esc(m.presentation)+'</small></div><span class="mm-status '+m.status+'">'+labels[m.status]+'</span></div><p><strong>'+number(m.quantity)+' '+esc(m.unit)+'</strong> · '+(m.type==='use'?'Uso':'Traslado')+'</p><p>'+esc(m.from)+' → '+esc(m.to)+'</p><p>'+esc(m.purpose)+(m.lotId?' · Lote '+esc(m.lotId):'')+'</p>'+(m.notes?'<p class="mm-note">'+esc(m.notes)+'</p>':'')+'<small>Costo del '+(m.type==='use'?'uso':'producto trasladado')+': '+(m.costCents===null?'Sin costo completo capturado':money(m.costCents/100,m.currency))+'</small>'+(editor()?'<div class="mm-history-actions">'+(m.status==='cancelled'?'<button class="secondary" data-mm-restore="'+esc(m.id)+'">Restaurar</button>':(m.status==='transit'?'<button class="primary" data-mm-receive="'+esc(m.id)+'">Marcar recibido</button>':'')+'<button class="secondary" data-mm-edit="'+esc(m.id)+'">Editar</button><button class="secondary material-delete" data-mm-cancel="'+esc(m.id)+'">Eliminar / anular</button>')+'</div>':'')+'</article>').join(''):'<div class="empty mm-empty">Sin movimientos en esta selección. Usa Mover o Registrar uso en el insumo correspondiente.</div>');
 document.querySelectorAll('[data-mm-edit]').forEach(b=>b.onclick=()=>edit(b.dataset.mmEdit));
 document.querySelectorAll('[data-mm-receive]').forEach(b=>b.onclick=()=>edit(b.dataset.mmReceive,true));
 document.querySelectorAll('[data-mm-cancel]').forEach(b=>b.onclick=()=>action(b.dataset.mmCancel,'cancel'));
 document.querySelectorAll('[data-mm-restore]').forEach(b=>b.onclick=()=>action(b.dataset.mmRestore,'restore'));
}
function edit(id,received=false){const d=read().data,m=O.moves(d).find(x=>x.id===id);if(!m)return;const index=O.rows(d,m.kind).findIndex(r=>r.id===m.sourceId);open(index,m.type,m,received);}
function open(index,type,record=null,received=false){
 if(!editor()||dialog||busy||!context.mayLeave())return;
 const before=read(),source=O.rows(before.data,context.kind)[index];if(!source){message('El insumo ya no está en esa ubicación. Actualiza el listado.',true);return;}
 const expectedSource=JSON.stringify(source),back=window.EBEditReturn?.capture(),kind=context.kind,id=record?.id||crypto.randomUUID();let expected=record?JSON.stringify(record):undefined;
 pending=null;dirty=false;dialog=document.createElement('dialog');dialog.id='material-move-dialog';dialog.className='mm-dialog';
 const locations=[...new Set([...context.locations,record?.to,source.loc].filter(Boolean))];
 let destination=record?.to||(type==='use'?source.loc:locations.find(x=>x!==source.loc)||'');
 const purposes=type==='use'?['Retaponado','Envasado','Promoción / muestras','Merma','Otro']:['Traslado de bodega','Para retaponado','Para envasado','Material para evento','Otro'];
 const selectedPurpose=record?.purpose||'',basePurpose=purposes.includes(selectedPurpose)?selectedPurpose:selectedPurpose?'Otro':'';
 dialog.innerHTML='<div class="mm-dialog-title"><div><div class="eyebrow">'+(record?'EDITAR MOVIMIENTO':'INVENTARIO DE '+(kind==='supplies'?'INSUMOS':'MARKETING'))+'</div><h2>'+ (type==='use'?'Registrar uso':'Mover mercancía')+'</h2><p><b>'+esc(source.name)+'</b>'+(source.presentation?' · '+esc(source.presentation):'')+'</p><p>Origen: <b>'+esc(source.loc)+'</b> · Saldo actual: <b>'+number(source.qty)+'</b></p></div><button type="button" id="mm-close" aria-label="Cerrar">×</button></div><form id="mm-form" novalidate><div class="mm-fields"><label>Cantidad *<input id="mm-qty" type="number" min="1" step="1" inputmode="numeric" value="'+esc(record?.quantity??'')+'" placeholder="Unidades"></label><label>Fecha *<input id="mm-date" type="date" value="'+esc(record?.date||today())+'"></label><label>'+ (type==='use'?'Lugar donde se utiliza *':'Destino *')+'<select id="mm-to">'+locations.map(l=>'<option '+(l===destination?'selected':'')+'>'+esc(l)+'</option>').join('')+'<option value="__new__">+ Otro lugar</option></select><input id="mm-new-location" placeholder="Escribe el lugar" maxlength="160" hidden></label>'+(type==='transfer'?'<label>Estado<select id="mm-status"><option value="received" '+((received||record?.status!=='transit')?'selected':'')+'>Recibido en destino</option><option value="transit" '+(!received&&record?.status==='transit'?'selected':'')+'>En tránsito</option></select></label>':'')+'<label>Motivo / para qué *<select id="mm-purpose"><option value="">Selecciona un motivo</option>'+purposes.map(p=>'<option '+(p===basePurpose?'selected':'')+'>'+esc(p)+'</option>').join('')+'</select><input id="mm-custom-purpose" maxlength="200" placeholder="Describe el motivo" '+(basePurpose==='Otro'?'':'hidden')+' value="'+esc(basePurpose==='Otro'?selectedPurpose:'')+'"></label></div><details class="mm-optional" '+(record?.lotId||record?.notes?'open':'')+'><summary>Lote y notas (opcional)</summary><label>Lote relacionado<select id="mm-lot"><option value="">Sin lote</option>'+(before.data.lots||[]).map(l=>'<option value="'+esc(l.id)+'" '+(record?.lotId===l.id?'selected':'')+'>'+esc(l.id)+' · '+esc(['Espadín Capón','Cupreata','Dark Blend'][l.p]||'')+'</option>').join('')+'</select></label><label>Notas<textarea id="mm-notes" maxlength="1000" rows="2">'+esc(record?.notes||'')+'</textarea></label></details><div id="mm-preview" class="mm-preview"></div><p class="mm-note">'+(type==='use'?'Descuenta del origen y registra el uso indicado. No crea existencias en el destino ni botellas producidas. No registres otra salida por el mismo uso.':'Descuenta del origen y suma al destino al recibirlo. No registra consumo ni venta.')+' Los costos de los lotes no se modifican.</p><div id="mm-error" role="alert" hidden></div><div class="mm-form-actions"><button type="button" id="mm-cancel" class="secondary">Cancelar</button><button type="submit" id="mm-save" class="primary">Guardar '+(type==='use'?'uso':'movimiento')+'</button></div></form>';
 document.body.append(dialog);dialog.showModal();
 function input(){return{type,quantity:$('mm-qty').value,date:$('mm-date').value,to:$('mm-to').value==='__new__'?$('mm-new-location').value:$('mm-to').value,status:type==='use'?'used':$('mm-status').value,purpose:$('mm-purpose').value==='Otro'?$('mm-custom-purpose').value:$('mm-purpose').value,lotId:$('mm-lot').value,notes:$('mm-notes').value};}
 function opts(){return{id,operation:crypto.randomUUID(),stamp:new Date().toISOString(),actor:window.EBShared.user.username,index,expectedSource,...(expected?{expected}:{})};}
 function preview(){try{const r=O.change(read().data,kind,input(),opts()),row=O.rows(r.data,kind).find(x=>x.id===r.record.sourceId);$('mm-preview').textContent='Saldo en '+row.loc+': '+number(row.qty)+' '+esc(source.unit||'unidades')+(type==='use'?' · Utilizadas: '+number(r.record.quantity):r.record.status==='transit'?' · En tránsito: '+number(r.record.quantity):' · Se reciben '+number(r.record.quantity)+' en '+r.record.to)+(r.warnings.length?' · Atención: hay saldo negativo por cuadrar.':'');$('mm-preview').dataset.warning=String(!!r.warnings.length);}catch(e){$('mm-preview').textContent='Completa cantidad, fecha, destino y motivo para ver el saldo resultante.';}}
 const close=()=>{if(busy)return;if(dirty&&!confirm('¿Cerrar esta captura? Lo guardado localmente se conserva.'))return;dialog.close();};
 $('mm-close').onclick=close;$('mm-cancel').onclick=close;dialog.oncancel=e=>{e.preventDefault();close();};dialog.onclose=()=>{dialog.remove();dialog=null;dirty=false;window.EBShared.cancelDraft();};
 $('mm-to').onchange=()=>{$('mm-new-location').hidden=$('mm-to').value!=='__new__';};$('mm-purpose').onchange=()=>{$('mm-custom-purpose').hidden=$('mm-purpose').value!=='Otro';};
 $('mm-form').oninput=()=>{dirty=true;preview();};$('mm-form').onchange=()=>{dirty=true;preview();};preview();
 $('mm-form').onsubmit=async e=>{
  e.preventDefault();if(busy)return;busy=true;issue('');setBusy(true);let local=false;
  try{
   if(!pending){const current=read(),r=O.change(current.data,kind,input(),opts());if(localStorage.getItem(KEY)!==current.raw)throw Error('Otra pestaña cambió las existencias. Vuelve a abrir el movimiento.');if(!r.unchanged)localStorage.setItem(KEY,JSON.stringify(r.data));pending=r;expected=JSON.stringify(r.record);}
   local=true;const cloud=await window.EBShared.snapshot(),saved=(cloud.data.materialMovements||[]).find(m=>m.id===id);
   if(!saved||JSON.stringify(saved)!==JSON.stringify(pending.record))throw Error('No coincide con la versión compartida. Revisa si otro socio modificó el movimiento.');
   const warning=pending.warnings.length,unchanged=pending.unchanged;dirty=false;const d=dialog;d.close();context.refresh();window.EBEditReturn?.restore(back);message((unchanged?'Movimiento confirmado.':'Guardado en la base compartida. Inventario actualizado.')+(warning?' Hay saldo negativo por cuadrar.':''));pending=null;
  }catch(e){issue((local?'La captura quedó en este dispositivo. Pulsa Guardar para confirmar el mismo movimiento, sin duplicarlo. ':'No se guardó: ')+e.message);}finally{busy=false;setBusy(false);}
 };
}
function setBusy(on){
 if(!dialog)return;for(const el of dialog.querySelectorAll('input,select,textarea,button')){el.disabled=on||!!pending&&!['mm-save','mm-close','mm-cancel'].includes(el.id);}
 if($('mm-save'))$('mm-save').textContent=on?'Guardando…':pending?'Reintentar guardado':'Guardar';
}
async function action(id,action){
 if(!editor()||busy)return;const old=O.moves(read().data).find(m=>m.id===id);if(!old)return;
 if(!confirm(action==='cancel'?'¿Anular este movimiento? Se revierten sus cantidades y costo; el registro queda en el historial.':'¿Restaurar el movimiento y aplicar nuevamente sus cantidades?'))return;
 busy=true;let saved=false;
 try{const before=read(),result=O.change(before.data,old.kind,null,{id,operation:crypto.randomUUID(),stamp:new Date().toISOString(),expected:JSON.stringify(old),action,actor:window.EBShared.user.username});if(localStorage.getItem(KEY)!==before.raw)throw Error('Cambió la información. Actualiza.');if(!result.unchanged)localStorage.setItem(KEY,JSON.stringify(result.data));saved=true;const cloud=await window.EBShared.snapshot(),remote=(cloud.data.materialMovements||[]).find(m=>m.id===id);if(JSON.stringify(remote)!==JSON.stringify(result.record))throw Error('No se confirmó el cambio.');const back=window.EBEditReturn?.capture();context.refresh();window.EBEditReturn?.restore(back);window.EBShared.cancelDraft();message(action==='cancel'?'Movimiento anulado. Se revirtieron sus cantidades y costo.':'Movimiento restaurado. Inventario actualizado.');}
 catch(e){context.refresh();message((saved?'Cambio guardado localmente; pendiente de confirmar. No hagas un ajuste manual adicional. ':'No se modificó: ')+e.message,true);}finally{busy=false;}
}
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
window.EBMaterialMovesUI={mount,get dirty(){return dirty||!!dialog;}};
})();
