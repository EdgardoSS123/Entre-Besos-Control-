'use strict';
/* Explicit, reversible corrections. Never mutates input or changes stored data on load. */
(function(root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory;
  else root.EBLedger = factory(root.EBLedger);
})(typeof window === 'undefined' ? globalThis : window, function(I) {
  const copy = x => JSON.parse(JSON.stringify(x));
  const fail = m => { throw Error(m); };
  const alive = x => x.status !== 'cancelled';
  const eq = (a,b) => JSON.stringify(a) === JSON.stringify(b);
  const owns = (x,id) => x && (x.lotId === id || x.lot === id);
  function getLot(d,id) { const l=(d.lots||[]).find(x=>x.id===id); if(!l) fail('El lote ya no existe. Abre Mis lotes.'); return l; }
  function checkToken(record,expected) { if(expected !== undefined && expected !== null && JSON.stringify(record)!==expected) fail('Este registro cambió en otra pestaña. Vuelve a abrirlo antes de corregirlo.'); }
  function date(v,now,optional=false) { if(!v&&optional)return null; if(!/^\d{4}-\d{2}-\d{2}$/.test(v)||isNaN(Date.parse(v))||new Date(v+'T12:00:00Z').toISOString().slice(0,10)!==v||v>now)fail('Revisa la fecha.');return v; }
  function amount(v,positive=false) { const s=String(v??'').trim().replace(',','.');if(!/^\d+(?:\.\d{1,2})?$/.test(s))fail('Revisa el importe: máximo 2 decimales.');const n=Math.round(Number(s)*100);if(!Number.isSafeInteger(n)||n<0||(positive&&n===0))fail('Revisa el importe.');return n; }
  function loc(d,v,optional=false) {if(!v&&optional)return null;if(!I.locations(d).includes(v))fail('Selecciona una ubicación registrada.');return v;}
  function tag(v) {if(!I.LABELS.includes(v))fail('Selecciona una etiqueta válida.');return v;}
  function currency(v) {if(!I.CURRENCIES.includes(v))fail('Selecciona una moneda válida.');return v;}
  function bundle(d,ids) {const b={};for(const [k,arr] of Object.entries(d)){if(k==='editHistory'||!Array.isArray(arr))continue;const chosen=arr.filter(x=>k==='lots'?ids.includes(x.id):ids.some(id=>owns(x,id)));if(chosen.length)b[k]=copy(chosen);}return b;}
  function validate(d,ids) {for(const id of ids)if((d.lots||[]).some(l=>l.id===id)){try{I.balance(d,id);}catch(e){fail('No se guardó: esta corrección dejaría existencias o muestras negativas. Corrige primero la venta o el movimiento relacionado. '+e.message);}for(const s of I.sales(d,id)){const paid=(s.payments||[]).reduce((a,p)=>a+p.amountCents,0);if(!Number.isSafeInteger(paid)||paid<0)fail('Revisa los pagos de la venta.');if(paid>0&&(!Number.isSafeInteger(s.totalCents)||paid>s.totalCents))fail('Los cobros superan el nuevo total. Corrige el pago antes de reducir la venta.');}}}
  function finish(d,next,ids,title,meta={}) {validate(next,ids);const before=bundle(d,ids),after=bundle(next,ids);if(eq(before,after))return next;next.editHistory=next.editHistory||[];const positions={};for(const k of Object.keys(before))positions[k]=(d[k]||[]).map((x,i)=>(k==='lots'?ids.includes(x.id):ids.some(id=>owns(x,id)))?i:-1).filter(i=>i>=0);next.editHistory.push({id:meta.id,at:meta.stamp,lotIds:ids,title,before,after,positions,deleted:!!meta.deleted});return next;}
  function relatedCount(d,id){return Object.entries(bundle(d,[id])).filter(([k])=>k!=='lots'&&!k.toLowerCase().includes('revision')).reduce((s,[,v])=>s+v.length,0);}
  function correctLot(d,id,record,expected,meta) {
    const old=getLot(d,id);checkToken(old,expected);const newId=String(record.id||'').trim();
    if(!newId||newId.length>80)fail('Escribe el código del lote (máximo 80 caracteres).');
    if((d.lots||[]).some(l=>l.id!==id&&String(l.id).toLocaleLowerCase()===newId.toLocaleLowerCase()))fail('Ya existe otro lote con ese código. No se combinaron los registros.');
    if(!Number.isInteger(record.p)||record.p<0||record.p>2||!Number.isSafeInteger(record.bottles)||record.bottles<1||!Number.isFinite(record.unitCost)||record.unitCost<0||!Number.isFinite(record.ml)||record.ml<=0)fail('Revisa los datos y el cálculo del lote.');
    const next=copy(d);if(newId!==id)for(const [k,arr] of Object.entries(next)){if(k==='editHistory'||k==='lots'||!Array.isArray(arr))continue;for(const item of arr){if(item.lotId===id)item.lotId=newId;if(item.lot===id)item.lot=newId;}}
    next.lots[next.lots.findIndex(l=>l.id===id)]={...copy(record),id:newId};
    (next.lotRevisions=next.lotRevisions||[]).push({lotId:newId,replacedAt:meta.stamp,record:copy(old)});
    const initialized=record.originWarehouse?I.initializeOrigin(next,newId,record.originWarehouse,meta.localDate||(meta.stamp||'').slice(0,10),meta.stamp):next;
    return finish(d,initialized,[...new Set([id,newId])],'Editar lote '+id+(id!==newId?' → '+newId:''),meta);
  }
  function removeLot(d,id,expected,meta){checkToken(getLot(d,id),expected);const next=copy(d);for(const [k,arr] of Object.entries(next)){if(k==='editHistory'||!Array.isArray(arr))continue;next[k]=arr.filter(x=>k==='lots'?x.id!==id:!owns(x,id));}return finish(d,next,[id],'Eliminar lote '+id,{...meta,deleted:true});}
  function find(d,id,kind,rid) {getLot(d,id);const map={sale:'lotSales',move:'lotShipments',sample:'lotSampleActions',count:'lotStockAdjustments'};const k=map[kind];if(!k)fail('Tipo de registro desconocido.');const r=(d[k]||[]).find(x=>x.id===rid&&x.lotId===id);if(!r)fail('Registro no encontrado.');return{k,r};}
  function correctSale(d,id,rid,p,expected,meta,now) {
    const {r:s}=find(d,id,'sale',rid);checkToken(s,expected);const next=copy(d),t=next.lotSales.find(x=>x.id===rid&&x.lotId===id);
    const mode=s.shipmentId?'shipment':p.historical?'historical':'direct',historical=mode==='historical';
    const n=I.quantity(p.amount,p.unit),price=String(p.price??'').trim().replace(',','.');
    if(!price&&!historical&&s.priceKnown!==false)fail('Captura el precio de venta.');
    const q=price?I.quote(n,price,p.priceBasis):{priceCents:null,totalCents:null,priceBasis:p.priceBasis||'bottle'};
    const paid=(s.payments||[]).reduce((a,x)=>a+x.amountCents,0);
    if(s.currency!==p.currency&&paid)fail('Esta venta tiene cobros. Corrige o elimina esos pagos antes de cambiar la moneda.');
    const saleDate=date(p.date,now,historical||!!s.inventoryAppliedDate),o=I.opening(d,id);
    if(historical&&saleDate&&o&&saleDate>o.asOf)fail('La venta anterior debe ser previa al conteo; puedes dejar la fecha pendiente.');
    if(!historical&&!s.inventoryAppliedDate&&saleDate&&o&&saleDate<o.asOf)fail('La venta es anterior al conteo. Marca «Ya estaba vendida antes de mi conteo».');
    const due=p.dueDate?date(p.dueDate,'9999-12-31'):'';if(due&&saleDate&&due<saleDate)fail('El vencimiento es anterior a la venta.');
    Object.assign(t,{mode,stockEffect:mode==='direct',from:loc(d,p.from,historical),tag:tag(p.tag),quantity:n,inputAmount:Number(String(p.amount).replace(',','.')),inputUnit:p.unit,...q,priceKnown:!!price,paymentKnown:price?(p.paymentKnown!==false):false,currency:currency(p.currency),customer:String(p.customer||'').trim().slice(0,160)||'Cliente no identificado',date:saleDate,dueDate:due,notes:String(p.notes||'').slice(0,2000),reference:String(p.reference||'').slice(0,160),updatedAt:meta.stamp});
    t.costMXN=Number.isFinite(t.unitCostMXN)?Math.round(n*t.unitCostMXN*100)/100:null;
    if(s.shipmentId){const sh=next.lotShipments.find(x=>x.id===s.shipmentId);if(!sh||!alive(sh))fail('El envío asociado ya no está activo.');Object.assign(sh,{quantity:n,inputAmount:t.inputAmount,inputUnit:p.unit,from:t.from,tag:t.tag,updatedAt:meta.stamp});}
    return finish(d,next,[id],'Editar venta de '+n+' botellas',meta);
  }
  function applySaleStock(d,id,rid,p,expected,meta,now) {
    const {r:s}=find(d,id,'sale',rid);checkToken(s,expected);
    if(!alive(s)||s.stockEffect||s.shipmentId||s.mode!=='historical')fail('Esta venta ya descuenta existencias o tiene una salida vinculada.');
    const from=loc(d,p.from),label=tag(p.tag);date(now,now);
    const available=I.available(d,id,from,label);
    if(s.quantity>available)fail('Solo hay '+available+' botellas comerciales en esta bodega.');
    const next=copy(d),t=next.lotSales.find(x=>x.id===rid&&x.lotId===id);
    Object.assign(t,{mode:'direct',stockEffect:true,from,tag:label,inventoryAppliedDate:now,inventoryAppliedAt:meta.stamp,updatedAt:meta.stamp});
    return finish(d,next,[id],'Descontar venta registrada de '+s.quantity+' botellas en '+from,meta);
  }
  function correctMove(d,id,rid,p,expected,meta,now){
    const {r:s}=find(d,id,'move',rid);checkToken(s,expected);const next=copy(d),t=next.lotShipments.find(x=>x.id===rid&&x.lotId===id);
    const historical=!!p.historical,n=historical&&String(p.amount).trim()===''?null:I.quantity(p.amount,p.unit),from=loc(d,p.from,historical),to=loc(d,p.to);
    if(from===to)fail('El origen y el destino deben ser diferentes.');if(!Object.hasOwn(I.PURPOSES,p.purpose))fail('Selecciona el motivo.');
    if(!['sample','commercial'].includes(p.stockType))fail('Selecciona producto comercial o muestras.');if(p.stockType==='sample'&&p.purpose==='sale')fail('No se registra una muestra como venta.');
    const dt=date(p.date,now,historical),o=I.opening(d,id);if(o&&dt&&(historical?dt>o.asOf:dt<o.asOf))fail('La fecha no corresponde al tipo de movimiento respecto al conteo inicial.');
    if(!['received','transit'].includes(p.status))fail('Selecciona recibido o en tránsito.');
    const rd=!historical&&p.status==='received'?date(p.receivedDate||dt,now):null;if(rd&&rd<dt)fail('La recepción es anterior al envío.');
    const known=String(p.cost??'').trim()!=='';
    Object.assign(t,{from,to,destination:copy(I.locationInfo(d,to)),tag:tag(p.tag),quantity:n,inputAmount:n===null?null:Number(String(p.amount).replace(',','.')),inputUnit:p.unit,purpose:p.purpose,stockType:p.stockType,historical,status:historical?'historical':p.status,date:dt,receivedDate:rd,notes:String(p.notes||'').slice(0,2000),reference:String(p.reference||'').slice(0,160),cost:{known,amount:known?amount(p.cost)/100:null,currency:currency(p.currency),included:!!p.included},updatedAt:meta.stamp});
    if(s.sourceSampleQuantity!==undefined){
      delete t.sourceSampleQuantity;
      if(!historical&&p.purpose==='sample'){
        const r=I.balance(d,id).rows.find(x=>x.location===from&&x.tag===p.tag);
        const restored=s.from===from&&s.tag===p.tag&&!s.historical?s.sourceSampleQuantity:0;
        t.sourceSampleQuantity=Math.min(n,(r?.sampleQuantity||0)+restored);
        t.stockType=t.sourceSampleQuantity===n?'sample':'commercial';
      }
    }
    if(p.purpose==='sample'||p.stockType==='sample')t.sampleAccounting={category:'Muestras y promoción',income:0,receivable:0,unitCostMXN:getLot(d,id).unitCost,paymentStatus:'No aplica'};else delete t.sampleAccounting;
    const linked=(next.lotSales||[]).filter(x=>x.lotId===id&&x.shipmentId===rid&&alive(x));
    if(linked.length&&(p.purpose!=='sale'||n===null))fail('El envío tiene una venta. Elimina esa venta antes de cambiar el motivo.');
    for(const sale of linked){Object.assign(sale,{quantity:n,from,tag:p.tag,inputAmount:t.inputAmount,inputUnit:p.unit,updatedAt:meta.stamp});if(sale.priceCents!==null)Object.assign(sale,I.quote(n,(sale.priceCents/100).toFixed(2),sale.priceBasis));sale.costMXN=Number.isFinite(sale.unitCostMXN)?Math.round(sale.unitCostMXN*n*100)/100:null;}
    return finish(d,next,[id],'Editar movimiento '+from+' → '+to,meta);
  }
  function correctSample(d,id,rid,p,expected,meta,now){const {r}=find(d,id,'sample',rid);checkToken(r,expected);if(!['reserve','release','consume'].includes(p.type))fail('Selecciona la operación.');const next=copy(d),t=next.lotSampleActions.find(x=>x.id===rid&&x.lotId===id);const n=I.quantity(p.amount,p.unit);Object.assign(t,{location:loc(d,p.location),tag:tag(p.tag),quantity:n,type:p.type,date:date(p.date,now),notes:String(p.notes||'').slice(0,2000),income:0,receivable:0,updatedAt:meta.stamp,costMXN:Number.isFinite(t.unitCostMXN)?Math.round(n*t.unitCostMXN*100)/100:null});if(r.sourceSampleQuantity!==undefined){
      delete t.sourceSampleQuantity;
      if(p.type==='consume'){
        const current=I.balance(d,id).rows.find(x=>x.location===p.location&&x.tag===p.tag);
        const restored=r.type==='consume'&&r.location===p.location&&r.tag===p.tag?r.sourceSampleQuantity:0;
        t.sourceSampleQuantity=Math.min(n,(current?.sampleQuantity||0)+restored);t.stockType='any';
      }else t.stockType='sample';
    }
    return finish(d,next,[id],'Editar muestras',meta);}
  function correctPayment(d,id,sid,pid,p,expected,meta,now){const {r:s}=find(d,id,'sale',sid),original=(s.payments||[]).find(x=>x.id===pid);if(!original)fail('Pago no encontrado.');checkToken(original,expected);const next=copy(d),t=next.lotSales.find(x=>x.id===sid&&x.lotId===id).payments.find(x=>x.id===pid);Object.assign(t,{amountCents:amount(p.amount,true),date:date(p.date,now,s.mode==='historical'),reference:String(p.reference||'').slice(0,160),updatedAt:meta.stamp});return finish(d,next,[id],'Editar pago',meta);}
  function removeRecord(d,id,kind,rid,expected,meta,pid){const {k,r}=find(d,id,kind==='payment'?'sale':kind,rid);const next=copy(d);
    if(kind==='payment'){const p=(r.payments||[]).find(x=>x.id===pid);if(!p)fail('Pago no encontrado.');checkToken(p,expected);next[k].find(x=>x.id===rid&&x.lotId===id).payments=r.payments.filter(x=>x.id!==pid);}
    else{checkToken(r,expected);next[k]=next[k].filter(x=>!(x.id===rid&&x.lotId===id));
      if(kind==='sale'&&r.shipmentId)next.lotShipments=(next.lotShipments||[]).filter(x=>x.id!==r.shipmentId);
      if(kind==='move')next.lotSales=(next.lotSales||[]).filter(x=>x.shipmentId!==rid);
    }
    return finish(d,next,[id],'Eliminar '+({sale:'venta',move:'movimiento',sample:'registro de muestras',count:'conteo',payment:'pago'}[kind]),{...meta,deleted:true});
  }
  function correctStock(d,id,p,meta,now){const next=I.countStock(d,id,{...p,id:meta.id,stamp:meta.stamp},now);return finish(d,next,[id],p.remove?'Eliminar existencia de '+p.location:'Corregir existencia de '+p.location,{...meta,deleted:!!p.remove});}
  function undo(d,hid,meta){const h=(d.editHistory||[]).find(x=>x.id===hid&&!x.undoneAt);if(!h)fail('Esta corrección ya no se puede deshacer.');if(!eq(bundle(d,h.lotIds),h.after))fail('Hay cambios posteriores en este lote. Deshaz primero el cambio más reciente para no perder información.');const next=copy(d);for(const k of new Set([...Object.keys(h.before),...Object.keys(h.after)])){const remaining=(next[k]||[]).filter(x=>k==='lots'?!h.lotIds.includes(x.id):!h.lotIds.some(id=>owns(x,id)));copy(h.before[k]||[]).forEach((r,i)=>remaining.splice(Math.min(h.positions?.[k]?.[i]??remaining.length,remaining.length),0,r));next[k]=remaining;}validate(next,h.lotIds);next.editHistory.find(x=>x.id===hid).undoneAt=meta.stamp;return next;}
  return{...I,correctionsVersion:'1.0',correctLot,removeLot,correctSale,applySaleStock,correctMove,correctSample,correctPayment,removeRecord,correctStock,undoCorrection:undo,relatedCount};
});
