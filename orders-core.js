/* Partner orders share the existing workspace. Delivery posts one stock exit and one linked sale per lot. Unknown prices stay unknown. */
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
  if(r.tag!==undefined&&!I.LABELS.includes(r.tag))fail('Selecciona una etiqueta válida.');
  return{product:lot.p,lotId:lot.id,...(r.tag!==undefined?{tag:r.tag}:{}),amount:text(r.amount).replace(',','.'),unit:r.unit,quantity};
 });
 if(!Number.isSafeInteger(totals(lines)))fail('La cantidad del pedido está fuera de rango.');
 const customer=text(input.customer);if(customer.length>240)fail('El nombre del cliente admite hasta 240 caracteres.');
 const notes=text(input.notes);if(notes.length>1000)fail('Las notas admiten hasta 1,000 caracteres.');
 return{partner,customer,from,date:date(input.date),status,lines,quantity:totals(lines),notes};
}
function signature(r){return JSON.stringify([r.partner,text(r.customer),r.from,r.date,r.status,r.lines,r.notes]);}
function stockSignature(r){return JSON.stringify([r.from,r.status,r.lines.map(l=>[l.lotId,l.quantity,l.tag||null])]);}
function activeDebits(d,id){return(d.lotStockAdjustments||[]).filter(a=>a.source==='partner-order'&&a.orderId===id&&a.status!=='cancelled');}
function reverse(next,id,stamp){for(const a of activeDebits(next,id)){a.status='cancelled';a.cancelledAt=stamp;a.cancelReason='Corrección o cancelación desde Pedidos';}}
function debit(next,order,I,meta){
 const partner=PARTNERS.find(p=>p.id===order.partner).name;let index=0;
 for(const line of order.lines){
  if(!I.opening(next,line.lotId)){
   (next.inventoryOpenings=next.inventoryOpenings||[]).push({lotId:line.lotId,asOf:meta.day,rows:[],inputRows:[],complete:false,notes:'Pedido entregado sin conteo inicial. Saldo por cuadrar; no se inventó existencia.',updatedAt:meta.stamp});
  }
  const balance=I.balance(next,line.lotId),candidates=balance.rows.filter(r=>r.location===order.from&&r.commercialQuantity>0&&(!line.tag||r.tag===line.tag)).sort((a,b)=>b.commercialQuantity-a.commercialQuantity||String(a.tag).localeCompare(String(b.tag)));
  let remaining=line.quantity;
  function take(tag,n){
   const prev=I.balance(next,line.lotId).rows.find(r=>r.location===order.from&&r.tag===tag)||{quantity:0,sampleQuantity:0};
   (next.lotStockAdjustments=next.lotStockAdjustments||[]).push({id:'order-'+meta.operation+'-'+index++,source:'partner-order',orderId:order.id,orderVersion:order.version,lotId:line.lotId,location:order.from,tag,delta:-n,sampleDelta:0,previousQuantity:prev.quantity,previousSamples:prev.sampleQuantity||0,quantity:prev.quantity-n,samples:prev.sampleQuantity||0,inputAmount:String(n),inputUnit:'bottle',date:meta.day,createdAt:meta.stamp,actor:meta.actor||'',reason:'Pedido '+order.code+' · '+partner+' · entregado',status:'active'});
   remaining-=n;
  }
  for(const row of candidates){if(!remaining)break;take(row.tag,Math.min(remaining,row.commercialQuantity));}
  if(remaining){const tag=line.tag||candidates[0]?.tag||balance.rows.find(r=>r.location===order.from)?.tag||'Por clasificar';take(tag,remaining);}
 }
}

// Commercial entries point back to the existing order debit. Never debit twice.
function deliveryDate(order){
 const d=new Date(order.deliveredAt||order.updatedAt||order.createdAt);
 if(!Number.isFinite(d.getTime()))return order.date;
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d);
 const v=k=>parts.find(p=>p.type===k).value;return v('year')+'-'+v('month')+'-'+v('day');
}
function syncSalesInPlace(next,I,onlyOrderId=null){
 const records=next.lotSales||[],wanted=new Set();
 for(const order of rows(next)){
  if(onlyOrderId&&order.id!==onlyOrderId)continue;
  if(order.status!=='delivered')continue;
  const lots=new Map();for(const line of order.lines){const g=lots.get(line.lotId)||{quantity:0,product:line.product};g.quantity+=line.quantity;lots.set(line.lotId,g);}
  for(const [lotId,g] of lots){
   const old=records.find(s=>s.source==='partner-order'&&s.orderId===order.id&&s.lotId===lotId);
   const id=old?.id||'order-sale-'+order.id+'-'+encodeURIComponent(lotId);wanted.add(id);
   if(!old&&records.some(s=>s.id===id))fail('La referencia de venta ya existe. No se duplicó el pedido.');
   const lot=(next.lots||[]).find(l=>l.id===lotId);if(!lot)fail('Falta el lote del pedido entregado: '+lotId);
   const exits=activeDebits(next,order.id).filter(a=>a.lotId===lotId),labels=[...new Set(exits.map(a=>a.tag))];
   if(exits.reduce((n,a)=>n-a.delta,0)!==g.quantity||exits.some(a=>a.location!==order.from))fail('El pedido '+order.code+' no coincide con su salida de bodega. Revisa la entrega antes de crear su venta.');
   const known=old?.priceKnown!==false&&Number.isSafeInteger(old?.priceCents)&&old.priceCents>0;
   const price=known?I.quote(g.quantity,(old.priceCents/100).toFixed(2),old.priceBasis||'bottle'):{priceCents:null,totalCents:null,priceBasis:'bottle'};
   const paid=(old?.payments||[]).reduce((n,p)=>n+p.amountCents,0);
   if(paid&&(!known||paid>price.totalCents))fail('Los cobros de '+order.code+' superan el nuevo total. Corrige primero los pagos en Ventas.');
   const unitCostMXN=old?.unitCostMXN??(Number.isFinite(lot.unitCost)?lot.unitCost:null);
   const record={...(old||{}),id,lotId,source:'partner-order',mode:'order',stockEffect:false,shipmentId:null,
    orderId:order.id,orderCode:order.code,orderPartner:order.partner,orderVersion:order.version,
    from:order.from,tag:labels.length===1?labels[0]:(old?.tag||'Por clasificar'),stockTags:labels,
    customer:order.customer||'Cliente no identificado',quantity:g.quantity,inputAmount:g.quantity,inputUnit:'bottle',
    ...price,priceKnown:known,paymentKnown:known?(old?.paymentKnown??false):false,currency:old?.currency||'MXN',
    date:old?.date||deliveryDate(order),dueDate:old?.dueDate||'',reference:old?.reference||order.code,
    notes:old?.notes??order.notes??'',unitCostMXN,costMXN:unitCostMXN===null?null:Math.round(g.quantity*unitCostMXN*100)/100,
    createdAt:old?.createdAt||order.deliveredAt||order.updatedAt,updatedAt:order.updatedAt,
    payments:old?.payments||[],status:'active'};
   delete record.cancelledAt;delete record.cancelReason;
   if(old)Object.assign(old,record);else records.push(record);
  }
 }
 for(const sale of records)if(sale.source==='partner-order'&&(!onlyOrderId||sale.orderId===onlyOrderId)&&!wanted.has(sale.id)&&sale.status!=='cancelled'){
  const order=rows(next).find(o=>o.id===sale.orderId);if(!order)fail('Hay una venta sin su pedido vinculado. No se borró.');
  sale.status='cancelled';sale.cancelledAt=order.updatedAt;sale.cancelReason='Pedido pendiente, cancelado o renglón retirado';
 }
 if(records.length||next.lotSales)next.lotSales=records;
 return next;
}
function assertLinkedSales(d){
 const all=d.lotSales||[],linked=all.filter(s=>s.source==='partner-order'),active=linked.filter(s=>s.status!=='cancelled');
 const expected=new Map();
 for(const o of rows(d))if(o.status==='delivered')for(const l of o.lines){const key=JSON.stringify([o.id,l.lotId]),row=expected.get(key)||{order:o,quantity:0};row.quantity+=l.quantity;expected.set(key,row);}
 const seen=new Set();
 for(const s of active){
  const key=JSON.stringify([s.orderId,s.lotId]),e=expected.get(key);
  if(!e||seen.has(key)||s.stockEffect!==false||s.mode!=='order'||s.shipmentId||s.quantity!==e.quantity||s.from!==e.order.from||s.orderPartner!==e.order.partner||s.customer!==(e.order.customer||'Cliente no identificado'))fail('El pedido y su venta vinculada no coinciden. Recarga la app para usar la versión actual; no se guardó ni se duplicó la salida.');
  seen.add(key);
  const debits=activeDebits(d,s.orderId).filter(a=>a.lotId===s.lotId);
  if(debits.reduce((n,a)=>n-a.delta,0)!==s.quantity||debits.some(a=>a.location!==s.from))fail('El descuento de bodega no coincide con la venta del pedido. No se guardó.');
 }
 if(d.orderSalesVersion===1&&seen.size!==expected.size)fail('Falta la venta de un pedido entregado. Recarga la app antes de volver a guardar.');
}
function synchronizeSales(d,I){const next=copy(d);syncSalesInPlace(next,I);next.orderSalesVersion=1;return JSON.stringify(next)===JSON.stringify(d)?d:next;}

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
 if(before?.status==='deleted'&&opts.action!=='restore')fail('Restaura este pedido desde Papelera antes de editarlo.');
 if(before?.status==='cancelled'&&!['delete','restore'].includes(opts.action))fail('Devuelve el pedido a pendiente antes de editarlo.');
 const action=opts.action||'save';if(!['save','cancel','delete','restore'].includes(action))fail('Acción no válida.');
 if(action!=='save'&&!before)fail('No se encontró el pedido.');
 const normalized=action==='save'?validate(d,input,I):{...copy(before),status:action==='restore'?'pending':action==='cancel'?'cancelled':'deleted'};
 if(action==='save'&&!normalized.customer&&(!before||text(before.customer)))fail('Indica para quién es el pedido.');
 if(before&&signature(before)===signature(normalized))return{data:d,order:before,unchanged:true,warnings:[]};
 const next=copy(d),version=(before?.version||0)+1;
 const after={...(before||{}),...normalized,id:opts.id,code:before?.code||'PED-'+String(source.length+1).padStart(4,'0'),version,createdAt:before?.createdAt||stamp,createdBy:before?.createdBy||opts.actor||'',updatedAt:stamp,updatedBy:opts.actor||'',deliveredAt:normalized.status==='delivered'?(before?.deliveredAt||stamp):null};
 // A recipient-only edit must preserve the original stock exits byte for byte.
 if(!before||stockSignature(before)!==stockSignature(after)){
  reverse(next,opts.id,stamp);
  if(after.status==='delivered')debit(next,after,I,{operation,stamp,day,actor:opts.actor});
 }
 next.partnerOrders=next.partnerOrders||[];if(at<0)next.partnerOrders.push(after);else next.partnerOrders[at]=after;
 const lotIds=[...(before?.lines||[]),...after.lines].map(r=>r.lotId);
 syncSalesInPlace(next,I,after.id);
 const issues=warnings(next,I,lotIds);
 (next.partnerOrderHistory=next.partnerOrderHistory||[]).push({id:operation,request:requested,orderId:after.id,at:stamp,actor:opts.actor||'',action:action==='save'?(before?'update':'create'):action,before:copy(before),after:copy(after)});
 return{data:next,order:after,unchanged:false,warnings:issues};
}
function setStatus(d,id,status,options,I){const r=rows(d).find(x=>x.id===id);if(!r)fail('Pedido no encontrado.');return save(d,{...r,status},{...options,id},I);}
function preview(d,input,options,I){return save(d,input,{...options,operation:'preview-only',stamp:options.stamp||new Date().toISOString()},I);}
const api={PARTNERS,PRODUCTS,rows,save,setStatus,preview,validate,activeDebits,today,synchronizeSales,assertLinkedSales};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBOrders=api;
})(typeof window==='undefined'?globalThis:window);
