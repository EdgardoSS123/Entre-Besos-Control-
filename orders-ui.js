(function(){
'use strict';
const $=id=>document.getElementById(id),O=window.EBOrders,I=window.EBLedger;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=n=>new Intl.NumberFormat('es-MX').format(n),when=v=>v?new Date(v.length>10?v:v+'T12:00:00Z').toLocaleDateString('es-MX',{day:'2-digit',month:'short',year:'numeric',timeZone:'America/Mexico_City'}):'Sin fecha';
const name=id=>O.PARTNERS.find(x=>x.id===id)?.name||id;
const states={pending:'Entrega pendiente',delivered:'Entregado',cancelled:'Cancelado',deleted:'Eliminado'};
let selected=new URLSearchParams(location.search).get('partner')||'',filter='all',fromDate='',toDate='',dialog=null,busy=false,dirty=false,editing=null,lines=[],draftId='';
if(!O.PARTNERS.some(x=>x.id===selected))selected='';
const canEdit=()=>window.EBShared?.user?.role==='editor';
function read(){const raw=localStorage.getItem('eb-v1'),data=JSON.parse(raw||'null');if(!data||!Array.isArray(data.lots)||!Array.isArray(data.moves))throw Error('No se pudo leer la información compartida.');O.rows(data);return{raw,data};}
function say(message,error=false){const t=$('orders-message');if(t){t.textContent=message;t.dataset.error=String(error);}}
function formError(m){const el=$('order-error');if(el)el.textContent=m;else say(m,true);}
function pack(n){return num(n)+' botellas · '+num(Math.floor(n/6))+' cajas'+(n%6?' + '+n%6+' sueltas':'');}
function render(){
 try{
 const all=O.rows(read().data).filter(x=>x.status!=='deleted');
 $('orders-app').innerHTML='<div class="heading"><div><div class="eyebrow">SOLICITUDES Y ENTREGAS</div><h1>Pedidos</h1><p class="muted">Elige al socio. Las existencias se descuentan al entregar.</p></div>'+(canEdit()&&selected?'<button class="primary" id="order-new">+ Nuevo pedido</button>':'')+'</div><div id="orders-message" role="status"></div><section class="order-partners" aria-label="Socio">'+O.PARTNERS.map(p=>{const pending=all.filter(r=>r.partner===p.id&&r.status==='pending');return'<button class="order-partner '+(selected===p.id?'selected':'')+'" data-partner="'+p.id+'"><span class="partner-initial">'+p.name[0]+'</span><strong>'+p.name+'</strong><small>'+pending.length+' pendiente'+(pending.length===1?'':'s')+'</small></button>';}).join('')+'</section>'+(selected?'<section class="orders-controls"><div class="order-state-tabs" aria-label="Estado">'+[['all','Todos'],['pending','Pendientes'],['delivered','Entregados'],['cancelled','Cancelados']].map(([v,l])=>'<button data-order-filter="'+v+'" class="'+(filter===v?'selected':'')+'">'+l+'</button>').join('')+'</div><details class="order-dates"><summary>Filtrar por fecha</summary><div class="fields"><label>Desde<input id="orders-filter-from" type="date" value="'+esc(fromDate)+'"></label><label>Hasta<input id="orders-filter-to" type="date" value="'+esc(toDate)+'"></label></div></details></section><div id="order-count" class="muted"></div><div id="order-list"></div>':'<div class="empty orders-start"><h2>Edgardo · Ricardo · Mario</h2><p>Toca un socio para consultar o registrar sus pedidos.</p></div>');
 document.querySelectorAll('[data-partner]').forEach(b=>b.onclick=()=>{selected=b.dataset.partner;history.replaceState(null,'','?partner='+selected);render();});
 $('order-new')?.addEventListener('click',()=>openForm());
 document.querySelectorAll('[data-order-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.orderFilter;render();});
 if(selected){$('orders-filter-from').onchange=()=>{fromDate=$('orders-filter-from').value;draw();};$('orders-filter-to').onchange=()=>{toDate=$('orders-filter-to').value;draw();};draw();}
 }catch(e){$('orders-app').innerHTML='<div class="alert">'+esc(e.message)+'</div>';}
}
function draw(){
 const data=read().data,records=O.rows(data).filter(r=>r.partner===selected&&r.status!=='deleted'&&(filter==='all'||r.status===filter)&&(!fromDate||r.date>=fromDate)&&(!toDate||r.date<=toDate)).sort((a,b)=>(b.date||'').localeCompare(a.date||'')||(b.createdAt||'').localeCompare(a.createdAt||''));
 $('order-count').textContent=records.length+' pedido'+(records.length===1?'':'s')+' · '+name(selected);
 $('order-list').innerHTML=records.length?records.map(r=>'<article class="order-record" data-order="'+esc(r.id)+'"><div class="order-record-head"><div><small>'+esc(r.code)+'</small><h2>'+esc(when(r.date))+'</h2><p class="order-recipient">Para: <b>'+esc(r.customer||'Destinatario por capturar')+'</b></p><p>Sale de <b>'+esc(r.from)+'</b></p></div><span class="order-status '+r.status+'">'+states[r.status]+'</span></div><div class="order-record-lines">'+r.lines.map(l=>'<div><span><b>'+esc(O.PRODUCTS[l.product])+'</b><small>Lote '+esc(l.lotId)+'</small></span><span><b>'+esc(l.amount)+' '+(l.unit==='box'?'cajas':'botellas')+'</b><small>'+num(l.quantity)+' botellas</small></span></div>').join('')+'</div><div class="order-record-total">'+pack(r.quantity)+'</div>'+(r.notes?'<p class="order-notes">'+esc(r.notes)+'</p>':'')+(r.status==='delivered'?'<p class="order-stock-note">Salida registrada el '+esc(when(r.deliveredAt||''))+'. Ya descontada de la bodega.</p>':'')+(canEdit()&&!['cancelled','deleted'].includes(r.status)?'<div class="order-actions">'+(r.status==='pending'?'<button class="primary" data-deliver="'+esc(r.id)+'">Marcar entregado</button>':'<button class="secondary" data-pending="'+esc(r.id)+'">Volver a pendiente</button>')+'<button class="secondary" data-edit-order="'+esc(r.id)+'">Editar</button><button class="order-cancel" data-cancel-order="'+esc(r.id)+'">Cancelar pedido</button></div>':'')+'<details class="order-history"><summary>Historial del pedido</summary>'+(data.partnerOrderHistory||[]).filter(h=>h.orderId===r.id).slice().reverse().slice(0,20).map(h=>'<p>'+esc(new Date(h.at).toLocaleString('es-MX',{timeZone:'America/Mexico_City'}))+' · '+esc(states[h.after?.status]||h.action)+' · '+esc(h.actor||'Socio')+'</p>').join('')+'</details></article>').join(''):'<div class="empty"><h2>Sin pedidos en esta selección</h2><p>'+esc(canEdit()?'Pulsa «Nuevo pedido» para registrar uno.':'No hay pedidos coincidentes.')+'</p></div>';
 document.querySelectorAll('[data-edit-order]').forEach(b=>b.onclick=()=>openForm(b.dataset.editOrder));
 document.querySelectorAll('[data-deliver]').forEach(b=>b.onclick=()=>transition(b.dataset.deliver,'delivered'));
 document.querySelectorAll('[data-pending]').forEach(b=>b.onclick=()=>transition(b.dataset.pending,'pending'));
 document.querySelectorAll('[data-cancel-order]').forEach(b=>b.onclick=()=>transition(b.dataset.cancelOrder,'cancelled'));
}
function lotOptions(p,chosen,data){const lots=data.lots.filter(l=>l.p===Number(p));return'<option value="">Selecciona el lote</option>'+lots.map(l=>'<option value="'+esc(l.id)+'" '+(l.id===chosen?'selected':'')+'>'+esc(l.id)+' · '+esc(l.ml)+' ml</option>').join('');}
function customerOptions(data){
 const names=(data.contacts||[]).map(c=>window.EBContacts?.view(c)).filter(Boolean).map(c=>c.name+(c.place&&c.place!==c.name?' · '+c.place:''));
 return [...new Set(names.filter(v=>v&&v.length<=240))].sort((a,b)=>a.localeCompare(b,'es')).map(v=>'<option value="'+esc(v)+'"></option>').join('');
}
function captureLines(){if(!$('order-lines'))return;lines=[...document.querySelectorAll('.order-line')].map(r=>({product:Number(r.querySelector('[data-product]').value),lotId:r.querySelector('[data-lot]').value,amount:r.querySelector('[data-amount]').value,unit:r.querySelector('[data-unit]').value}));}
function drawLines(){
 const data=read().data;
 $('order-lines').innerHTML=lines.map((l,i)=>'<div class="order-line" data-line="'+i+'"><div class="order-line-top"><strong>Variedad '+(i+1)+'</strong>'+(lines.length>1?'<button type="button" data-remove-line="'+i+'" aria-label="Quitar variedad '+(i+1)+'">Quitar</button>':'')+'</div><div class="fields"><label>Variedad<select data-product>'+O.PRODUCTS.map((p,n)=>'<option value="'+n+'" '+(n===l.product?'selected':'')+'>'+p+'</option>').join('')+'</select></label><label>Lote<select data-lot required>'+lotOptions(l.product,l.lotId,data)+'</select></label><label>Cantidad<input data-amount type="number" min="0.000001" step="any" inputmode="decimal" required value="'+esc(l.amount)+'" placeholder="Cantidad"></label><label>Unidad<select data-unit><option value="bottle" '+(l.unit==='bottle'?'selected':'')+'>Botellas</option><option value="box" '+(l.unit==='box'?'selected':'')+'>Cajas de 6</option></select></label></div><small data-line-help class="order-stock-note"></small></div>').join('');
 document.querySelectorAll('[data-product]').forEach(el=>el.onchange=()=>{captureLines();const i=Number(el.closest('[data-line]').dataset.line),lots=data.lots.filter(l=>l.p===lines[i].product);lines[i].lotId=lots.length===1?lots[0].id:'';dirty=true;drawLines();});
 document.querySelectorAll('[data-remove-line]').forEach(b=>b.onclick=()=>{captureLines();lines.splice(Number(b.dataset.removeLine),1);dirty=true;drawLines();});
 document.querySelectorAll('.order-line input,.order-line select').forEach(el=>el.addEventListener('input',()=>{dirty=true;captureLines();preview();}));preview();
}
function openForm(id){
 if(!canEdit()||busy)return;const data=read().data,order=id?O.rows(data).find(r=>r.id===id):null;if(id&&!order){say('No se encontró el pedido.',true);return;}
 editing=order?{id:order.id,expected:JSON.stringify(order)}:null;draftId=order?.id||crypto.randomUUID();dirty=false;
 const available=data.lots,defaultProduct=available[0]?.p??0,lots=available.filter(l=>l.p===defaultProduct);
 lines=order?JSON.parse(JSON.stringify(order.lines)):[{product:defaultProduct,lotId:lots.length===1?lots[0].id:'',amount:'',unit:'box'}];
 dialog=document.createElement('dialog');dialog.id='order-dialog';dialog.className='order-dialog';
 dialog.innerHTML='<div class="order-dialog-head"><div><div class="eyebrow">'+esc(name(order?.partner||selected))+'</div><h2>'+ (order?'Editar '+esc(order.code):'Nuevo pedido')+'</h2></div><button type="button" id="order-close" aria-label="Cerrar">×</button></div><form id="order-form"><div id="order-error" role="alert"></div><div class="fields"><label class="wide" for="order-customer">Cliente / para quién es el pedido *<input id="order-customer" type="text" maxlength="240" required list="order-customers" placeholder="Nombre de la persona o empresa" value="'+esc(order?.customer||'')+'" autocomplete="off"><datalist id="order-customers">'+customerOptions(data)+'</datalist></label><label>Fecha de entrega solicitada<input id="order-date" type="date" required value="'+esc(order?.date||O.today())+'"></label><label>Estado<select id="order-status"><option value="pending" '+(order?.status!=='delivered'?'selected':'')+'>Entrega pendiente</option><option value="delivered" '+(order?.status==='delivered'?'selected':'')+'>Entregado</option></select></label><label class="wide">Bodega de salida<select id="order-from" required>'+I.locations(data).map(x=>'<option value="'+esc(x)+'" '+(x===(order?.from||'CDMX')?'selected':'')+'>'+esc(x)+'</option>').join('')+'</select></label></div><div id="order-lines"></div><button type="button" class="secondary" id="order-add-line">+ Otra variedad</button><details class="order-dates"><summary>Notas (opcional)</summary><label>Entrega o referencia<input id="order-notes" maxlength="1000" value="'+esc(order?.notes||'')+'"></label></details><div id="order-preview" class="order-preview" role="status"></div><p class="order-stock-note">1 caja = 6 botellas. La entrega registra una salida; no inventa un precio ni un cobro. No registres otra salida para estas mismas botellas.</p><div class="order-form-actions"><button type="button" class="secondary" id="order-discard">Cancelar</button><button type="submit" class="primary" id="order-save">Guardar pedido</button></div></form>';
 document.body.append(dialog);dialog.showModal();drawLines();
 $('order-add-line').onclick=()=>{if(lines.length>=30)return;captureLines();lines.push({product:defaultProduct,lotId:lots.length===1?lots[0].id:'',amount:'',unit:'box'});dirty=true;drawLines();};
 const close=()=>{if(busy)return;if(dirty&&!confirm('¿Salir sin guardar este pedido?'))return;dialog.close();};$('order-close').onclick=close;$('order-discard').onclick=close;
 dialog.addEventListener('cancel',e=>{e.preventDefault();close();});dialog.onclose=()=>{dialog.remove();dialog=null;editing=null;dirty=false;window.EBShared?.cancelDraft?.();};
 $('order-form').addEventListener('input',()=>{dirty=true;preview();});$('order-form').addEventListener('change',()=>{dirty=true;preview();});$('order-form').onsubmit=e=>{e.preventDefault();saveForm();};
}
function input(){captureLines();return{partner:selected,customer:$('order-customer').value,from:$('order-from').value,date:$('order-date').value,status:$('order-status').value,lines,notes:$('order-notes').value};}
function preview(){
 const box=$('order-preview');if(!box)return;try{const value=input(),d=read().data,r=O.validate(d,value,I);const delivered=r.status==='delivered';let warning='';
  for(const row of document.querySelectorAll('.order-line')){const n=Number(row.dataset.line),l=r.lines[n],b=I.balance(d,l.lotId),q=b.rows.filter(x=>x.location===r.from).reduce((a,x)=>a+x.quantity,0);row.querySelector('[data-line-help]').textContent=num(l.quantity)+' botellas · saldo actual en '+r.from+': '+num(q);}
  if(delivered){const p=O.preview(d,value,{id:draftId,...(editing?{expected:editing.expected}:{}),day:O.today()},I);if(p.warnings.length)warning=' Atención: quedará un saldo negativo por cuadrar. Puedes guardar.';}
  box.textContent=pack(r.quantity)+(delivered?' · Se descontará de '+r.from+'.':' · Pendiente: no modifica existencias.')+warning;box.dataset.warning=String(!!warning);
 }catch(e){box.textContent='Elige la variedad, su lote y la cantidad. Las cajas se convierten automáticamente a botellas.';box.dataset.warning='false';}
}
async function commit(result,before){
 if(result.unchanged){say('El pedido ya estaba guardado; no se volvió a descontar.');return;}
 if(localStorage.getItem('eb-v1')!==before.raw)throw Error('La información cambió en otra pestaña. Actualiza antes de guardar.');
 localStorage.setItem('eb-v1',JSON.stringify(result.data));dirty=false;window.EBShared?.cancelDraft?.();
 if(dialog)dialog.close();render();
 let message='Pedido guardado. '+(result.order.status==='delivered'?'Existencias descontadas una sola vez.':result.order.status==='pending'?'Entrega pendiente.':'Pedido cancelado; se revirtió su salida, cuando correspondía.');
 if(result.warnings.length)message+=' Hay saldo negativo por cuadrar.';say(message);
 try{const row=await window.EBShared.snapshot(),saved=(row.data.partnerOrders||[]).find(x=>x.id===result.order.id);if(saved&&saved.version>=result.order.version)say(message+' Confirmado en la base compartida.');else say('Guardado local; revisa la sincronización.',true);}catch(e){say('Guardado local. La sincronización sigue pendiente: '+e.message,true);}
}
function meta(){return{id:draftId,operation:crypto.randomUUID(),stamp:new Date().toISOString(),day:O.today(),actor:window.EBShared.user.username,...(editing?{expected:editing.expected}:{})};}
async function saveForm(){
 if(busy||!canEdit())return;busy=true;$('order-save').disabled=true;formError('');
 try{if(window.EBShared.pending)throw Error('Termina de sincronizar el cambio anterior antes de guardar otro pedido.');const before=read(),result=O.save(before.data,input(),meta(),I);await commit(result,before);if(result.unchanged&&dialog){dirty=false;dialog.close();render();say('Sin cambios. No se volvió a descontar producto.');}}
 catch(e){formError('No se guardó: '+e.message);}finally{busy=false;if($('order-save'))$('order-save').disabled=false;}
}
async function transition(id,target){
 if(busy||!canEdit())return;const before=read(),r=O.rows(before.data).find(x=>x.id===id);if(!r)return;
 const question=target==='delivered'?'¿Marcar '+r.code+' entregado y descontar '+num(r.quantity)+' botellas de '+r.from+'?':target==='pending'?'¿Volver a pendiente? Se devolverán al saldo las botellas descontadas por este pedido.':'¿Cancelar '+r.code+'? Si estaba entregado, se revertirá su salida de bodega.';
 if(!confirm(question))return;busy=true;
 try{if(window.EBShared.pending)throw Error('Hay un cambio pendiente de sincronizar. Espera a Actualizado.');const opts={id,expected:JSON.stringify(r),operation:crypto.randomUUID(),stamp:new Date().toISOString(),day:O.today(),actor:window.EBShared.user.username};const result=target==='cancelled'?O.save(before.data,null,{...opts,action:'cancel'},I):O.setStatus(before.data,id,target,opts,I);await commit(result,before);}
 catch(e){say('No se modificó: '+e.message,true);}finally{busy=false;}
}
window.EBOrdersUI={render,get dirty(){return dirty;}};
window.addEventListener('storage',e=>{if(e.key!=='eb-v1')return;if(dialog){formError('Hay cambios en otro dispositivo. Tu captura se conserva; se verificará al guardar.');return;}render();});
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
render();
})();
