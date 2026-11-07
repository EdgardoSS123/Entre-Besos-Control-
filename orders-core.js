/* Partner orders share the existing workspace. Delivery is a stock exit, not a priced sale. */
(function(root){
'use strict';
const PARTNERS=[{id:'edgardo',name:'Edgardo',username:'esalazars'},{id:'ricardo',name:'Ricardo',username:'rsalazarm'},{id:'mario',name:'Mario',username:'msaenzc'}];
const PRODUCTS=['Espadín Capón','Cupreata','Dark Blend'];
const copy=x=>JSON.parse(JSON.stringify(x)),text=x=>String(x??'').trim(),fail=m=>{throw Error(m);};
function rows(d){if(d.partnerOrders===undefined)return[];if(!Array.isArray(d.partnerOrders)||d.partnerOrders.some(x=>!x||typeof x!=='object'||!Array.isArray(x.lines)))fail('No se pudieron leer los pedidos. No se modificó la base.');return d.partnerOrders;}
function today(){return new Date().toLocaleDateString('en-CA',{timeZone:'America/Mexico_City'});}
function date(v){v=text(v);if(!/^\d{4}-\d{2}-\d{2}$/.test(v)||!Number.isFinite(Date.parse(v+'T12:00:00Z'))||new Date(v+'T12:00:00Z').toISOString().slice(0,10)!==v)fail('Selecciona una fecha válida.');return v;}
function totals(list){return list.reduce((s,r)=>s+r.quantity,0);}
function validate(d,input,I){
 const partner=text(input.partner),from=text(input.from),status=text(input.status||'pending');
 if(!PARTNERS.some(x=>x.id===partner))fail('Selecciona Edgardo, Ricardo o Mario.');
 if(!I.locations(d).includes(from))fail('Selecciona la bodega de salida.');
 if(!['pending','delivered'].includes(status))fail('Selecciona entrega pendiente o entregado.');
 if(!Array.isArray(input.lines)||!input.lines.length||input.lines.length>30)fail('Agrega al menos una variedad (máximo 30 renglones).');
 const lines=input.lines.map(r=>{
  const lot=(d.lots||[]).find(l=>l.id===r.lotId);if(!lot)fail('Selecciona un lote existente para cada variedad.');
  if(!Number.isInteger(lot.p)||lot.p<0||lot.p>2||Number(r.product)!==lot.p)fail('La variedad no coincide con el lote seleccionado.');
  if(!['bottle','box'].includes(r.unit))fail('Selecciona botellas o cajas de 6.');
  const quantity=I.quantity(r.amount,r.unit);if(quantity>10000000)fail('Revisa la cantidad del pedido.');
  return{product:lot.p,lotId:lot.id,amount:text(r.amount).replace(',','.'),unit:r.unit,quantity};
 });
 if(!Number.isSafeInteger(totals(lines)))fail('La cantidad del pedido está fuera de rango.');
 const notes=text(input.notes);if(notes.length>1000)fail('Las notas admiten hasta 1,000 caracteres.');
 return{partner,from,date:date(input.date),status,lines,quantity:totals(lines),notes};
}
function signature(r){return JSON.stringify([r.partner,r.from,r.date,r.status,r.lines,r.notes]);}
function activeDebits(d,id){return(d.lotStockAdjustments||[]).filter(a=>a.source==='partner-order'&&a.orderId===id&&a.status!=='cancelled');}
function reverse(next,id,stamp){for(const a of activeDebits(next,id)){a.status='cancelled';a.cancelledAt=stamp;a.cancelReason='Corrección o cancelación desde Pedidos';}}
function debit(next,order,I,meta){
 const partner=PARTNERS.find(p=>p.id===order.partner).name;let index=0;
 for(const line of order.lines){
  if(!I.opening(next,line.lotId)){
   (next.inventoryOpenings=next.inventoryOpenings||[]).push({lotId:line.lotId,asOf:meta.day,rows:[],inputRows:[],complete:false,notes:'Pedido entregado sin conteo inicial. Saldo por cuadrar; no se inventó existencia.',updatedAt:meta.stamp});
  }
  const balance=I.balance(next,line.lotId),candidates=balance.rows.filter(r=>r.location===order.from&&r.commercialQuantity>0).sort((a,b)=>b.commercialQuantity-a.commercialQuantity||String(a.tag).localeCompare(String(b.tag)));
  let remaining=line.quantity;
  function take(tag,n){
   const prev=I.balance(next,line.lotId).rows.find(r=>r.location===order.from&&r.tag===tag)||{quantity:0,sampleQuantity:0};
   (next.lotStockAdjustments=next.lotStockAdjustments||[]).push({id:'order-'+meta.operation+'-'+index++,source:'partner-order',orderId:order.id,orderVersion:order.version,lotId:line.lotId,location:order.from,tag,delta:-n,sampleDelta:0,previousQuantity:prev.quantity,previousSamples:prev.sampleQuantity||0,quantity:prev.quantity-n,samples:prev.sampleQuantity||0,inputAmount:String(n),inputUnit:'bottle',date:meta.day,createdAt:meta.stamp,actor:meta.actor||'',reason:'Pedido '+order.code+' · '+partner+' · entregado',status:'active'});
   remaining-=n;
  }
  for(const row of candidates){if(!remaining)break;take(row.tag,Math.min(remaining,row.commercialQuantity));}
  if(remaining){const tag=candidates[0]?.tag||balance.rows.find(r=>r.location===order.from)?.tag||'Por clasificar';take(tag,remaining);}
 }
}
function warnings(d,I,ids){const out=[];for(const id of [...new Set(ids)])for(const r of I.balance(d,id).rows){if(r.quantity<0||r.commercialQuantity<0)out.push({lotId:id,location:r.location,quantity:r.quantity,commercialQuantity:r.commercialQuantity});}return out;}
function save(d,input,options,I){
 const opts=options||{},stamp=opts.stamp,operation=text(opts.operation),day=date(opts.day||today());
 if(!stamp||!operation||!opts.id)fail('Falta la referencia del pedido.');
 if(d.partnerOrderHistory!==undefined&&!Array.isArray(d.partnerOrderHistory))fail('Historial de pedidos inválido. No se guardó.');
 const source=rows(d),at=source.findIndex(r=>r.id===opts.id),before=at<0?null:source[at];
 const requested=JSON.stringify({id:opts.id,input,action:opts.action||'save'});
 const previous=(d.partnerOrderHistory||[]).find(h=>h.id===operation);
 if(previous){if(previous.request!==requested)fail('Esta referencia ya se utilizó.');return{data:d,unchanged:true,order:before,warnings:[]};}
 if(before&&opts.expected!==JSON.stringify(before))fail('Este pedido cambió en otro dispositivo. Actualiza antes de guardarlo.');
 if(!before&&opts.expected!==undefined)fail('El pedido ya no existe. Actualiza la pantalla.');
 if(before&&['cancelled','deleted'].includes(before.status))fail('Este pedido está cancelado. Crea uno nuevo para volver a solicitar producto.');
 const action=opts.action||'save';if(!['save','cancel','delete'].includes(action))fail('Acción no válida.');
 if(action!=='save'&&!before)fail('No se encontró el pedido.');
 const normalized=action==='save'?validate(d,input,I):{...copy(before),status:action==='cancel'?'cancelled':'deleted'};
 if(before&&signature(before)===signature(normalized))return{data:d,order:before,unchanged:true,warnings:[]};
 const next=copy(d),version=(before?.version||0)+1;
 const after={...(before||{}),...normalized,id:opts.id,code:before?.code||'PED-'+String(source.length+1).padStart(4,'0'),version,createdAt:before?.createdAt||stamp,createdBy:before?.createdBy||opts.actor||'',updatedAt:stamp,updatedBy:opts.actor||'',deliveredAt:normalized.status==='delivered'?(before?.deliveredAt||stamp):null};
 reverse(next,opts.id,stamp);
 if(after.status==='delivered')debit(next,after,I,{operation,stamp,day,actor:opts.actor});
 next.partnerOrders=next.partnerOrders||[];if(at<0)next.partnerOrders.push(after);else next.partnerOrders[at]=after;
 const lotIds=[...(before?.lines||[]),...after.lines].map(r=>r.lotId);
 const issues=warnings(next,I,lotIds);
 (next.partnerOrderHistory=next.partnerOrderHistory||[]).push({id:operation,request:requested,orderId:after.id,at:stamp,actor:opts.actor||'',action:action==='save'?(before?'update':'create'):action,before:copy(before),after:copy(after)});
 return{data:next,order:after,unchanged:false,warnings:issues};
}
function setStatus(d,id,status,options,I){const r=rows(d).find(x=>x.id===id);if(!r)fail('Pedido no encontrado.');return save(d,{...r,status},{...options,id},I);}
function preview(d,input,options,I){return save(d,input,{...options,operation:'preview-only',stamp:options.stamp||new Date().toISOString()},I);}
const api={PARTNERS,PRODUCTS,rows,save,setStatus,preview,validate,activeDebits,today};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBOrders=api;
})(typeof window==='undefined'?globalThis:window);
