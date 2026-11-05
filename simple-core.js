'use strict';
(function(root,factory){
  if(typeof module!=='undefined'&&module.exports)module.exports=factory;
  else root.EBLedger=factory(root.EBLedger);
})(typeof window==='undefined'?globalThis:window,function(I){
  const copy=x=>JSON.parse(JSON.stringify(x)),fail=m=>{throw Error(m);};
  const active=x=>x.status!=='cancelled';
  function lot(d,id){const l=(d.lots||[]).find(x=>x.id===id);if(!l)fail('Guarda primero el lote.');return l;}
  function unique(d,id){if(!id||[...(d.lotStockAdjustments||[]),...(d.lotSales||[]),...(d.lotShipments||[])].some(x=>x.id===id))fail('Esta operación ya se guardó.');}
  function validDate(v,now){if(!/^\d{4}-\d{2}-\d{2}$/.test(v)||isNaN(Date.parse(v))||new Date(v+'T12:00:00Z').toISOString().slice(0,10)!==v||v>now)fail('Revisa la fecha.');}
  function bucket(d,id,where,tag){return I.balance(d,id).rows.find(x=>x.location===where&&x.tag===tag)||{quantity:0,sampleQuantity:0,commercialQuantity:0};}
  function countStock(d,id,input,now){
    lot(d,id);unique(d,input.id);
    if(!I.locations(d).includes(input.location)||!I.LABELS.includes(input.tag))fail('Selecciona una ubicación válida.');
    const n=I.quantity(input.amount,input.unit,true),s=input.allSamples?n:I.quantity(input.samples??0,'bottle',true);
    if(s>n)fail('Las muestras incluidas no pueden superar la existencia.');
    const prev=bucket(d,id,input.location,input.tag);
    if(input.expected&&JSON.stringify([prev.quantity,prev.sampleQuantity])!==JSON.stringify(input.expected))fail('Las existencias cambiaron. Abre de nuevo este conteo para no sobrescribir otro movimiento.');
    const next=copy(d);
    if(!I.opening(next,id))(next.inventoryOpenings=next.inventoryOpenings||[]).push({lotId:id,asOf:now,rows:[],inputRows:[],complete:false,notes:'Inicio por conteo simple. No reconstruye el pasado.',updatedAt:input.stamp});
    (next.lotStockAdjustments=next.lotStockAdjustments||[]).push({id:input.id,lotId:id,location:input.location,tag:input.tag,delta:n-prev.quantity,sampleDelta:s-prev.sampleQuantity,previousQuantity:prev.quantity,previousSamples:prev.sampleQuantity,quantity:n,samples:s,inputAmount:String(input.amount),inputUnit:input.unit,date:now,createdAt:input.stamp,reason:'Conteo actual declarado; diferencia sin clasificar',status:'active'});
    I.balance(next,id);return next;
  }
  function packCounts(n) {
    if(!Number.isSafeInteger(n))fail('Cantidad de botellas inválida.');
    return {bottles:n,...(n<0?{sign:-1}:{}),fullCases:Math.floor(Math.abs(n)/6),looseBottles:Math.abs(n)%6,caseSize:6,equivalentCases:n/6};
  }
  function initializeOrigin(d,id,where,now,stamp) {
    const l=lot(d,id);if(!I.locations(d).includes(where))fail('Selecciona una bodega origen válida.');
    // An origin is metadata on an established lot. It never relocates or duplicates stock.
    const hasActivity=I.opening(d,id)||['lotStockAdjustments','lotShipments','lotSales','lotSampleActions'].some(k=>(d[k]||[]).some(x=>x.lotId===id));
    if(hasActivity||l.originSeeded)return d;
    const next=I.saveOpening(d,id,{asOf:now,complete:true,rows:[{location:where,tag:'Por clasificar',amount:l.bottles,unit:'bottle',isSample:!!l.originSamples}],notes:'Producción inicial en bodega origen.',stamp},now);
    Object.assign(next.lots.find(x=>x.id===id),{originSeeded:true,originWarehouse:where,originQuantity:l.bottles});
    return next;
  }
  function deliverSamples(d,id,input,now) {
    const stockType=input.stockType||'any';
    return I.sampleAction(d,id,{...input,type:'consume',stockType,date:now,location:input.from,notes:String(input.notes||'').trim()||'Muestras entregadas sin cargo.'},now);
  }
  function knownSale(d,id,input,now){
    const l=lot(d,id);unique(d,input.id);const n=I.quantity(input.amount,input.unit);
    const o=I.opening(d,id);if(!o)fail('Primero registra lo que tienes hoy.');
    const date=input.date||null;if(date){validDate(date,now);if(date>o.asOf)fail('Esta opción es para ventas anteriores al primer conteo. Deja la fecha vacía si no la recuerdas.');}
    if(input.from&&!I.locations(d).includes(input.from))fail('Ubicación no reconocida.');
    const known=String(input.price??'').trim()!=='';
    const q=known?I.quote(n,input.price,input.priceBasis):{priceCents:null,totalCents:null,priceBasis:input.priceBasis||'bottle'};
    if(!I.CURRENCIES.includes(input.currency))fail('Selecciona la moneda.');
    const customer=String(input.customer||'').trim().slice(0,160)||'Cliente no identificado';
    if(!['unknown','pending','paid'].includes(input.payment))fail('Revisa el estado de pago.');
    if(!known&&input.payment!=='unknown')fail('Para indicar el pago, captura el precio o deja «No recuerdo».');
    const record={id:input.id,lotId:id,mode:'historical',stockEffect:false,shipmentId:null,from:input.from||null,tag:input.tag||'Por clasificar',customer,quantity:n,inputAmount:Number(String(input.amount).replace(',','.')),inputUnit:input.unit,...q,priceKnown:known,paymentKnown:input.payment!=='unknown',currency:input.currency,date,dueDate:'',reference:'',notes:'Venta anterior al conteo. No vuelve a descontar existencias.',unitCostMXN:Number.isFinite(l.unitCost)?l.unitCost:null,costMXN:Number.isFinite(l.unitCost)?Math.round(n*l.unitCost*100)/100:null,createdAt:input.stamp,payments:known&&input.payment==='paid'?[{id:input.id+'-initial',amountCents:q.totalCents,date:date||null,createdAt:input.stamp,reference:'Cobro informado; fecha '+(date?'indicada':'no recordada')}]:[]};
    const next=copy(d);(next.lotSales=next.lotSales||[]).push(record);return next;
  }
  function reconciliation(d,id){
    const l=lot(d,id),b=I.balance(d,id),ss=I.sales(d,id),linked=new Set(ss.map(s=>s.shipmentId).filter(Boolean));
    const historical=ss.filter(s=>s.mode==='historical').reduce((n,s)=>n+s.quantity,0);
    const legacy=I.shipments(d,id).filter(s=>active(s)&&s.historical&&I.purposeOf(s)==='sale'&&!linked.has(s.id)&&Number.isSafeInteger(s.quantity)).reduce((n,s)=>n+s.quantity,0);
    const linkedHistorical=ss.filter(s=>s.shipmentId&&I.shipments(d,id).some(x=>x.id===s.shipmentId&&x.historical)).reduce((n,s)=>n+s.quantity,0);
    const sold=b.deliveredSales+historical+legacy+linkedHistorical;
    const used=b.samplesUsed||0,produced=Number(l.bottles)||0,unexplained=produced-b.knownTotal-sold-used;
    return{...b,produced,sold,used,unexplained,accounted:b.knownTotal+sold+used};
  }
  function moveStock(d,id,input,now){
    if(input.from===input.to)fail('Elige un destino distinto al origen.');
    return I.saveShipment(d,id,{id:input.id,from:input.from,to:input.to,tag:input.tag,amount:String(input.amount).replace(',','.'),unit:input.unit,date:now,received:true,historical:false,purpose:I.locationInfo(d,input.to).kind==='warehouse'?'transfer':'consignment',stockType:input.stockType||'commercial',isSample:input.isSample===true,costKnown:String(input.cost??'').trim()!=='',costAmount:input.cost,currency:input.currency||'MXN',included:false,notes:'Movimiento simple confirmado. Sigue siendo producto de Entre Besos.',reference:'',stamp:input.stamp},now);
  }
  function sellStock(d,id,input,now){
    return I.saveSale(d,id,{...input,amount:String(input.amount).replace(',','.'),mode:'direct',date:now,customer:String(input.customer||'').trim()||'Cliente no identificado',paidAmount:input.payment==='paid'?(I.quote(I.quantity(input.amount,input.unit),input.price,input.priceBasis).totalCents/100).toFixed(2):'0',paymentDate:now,notes:input.notes||'',reference:'',dueDate:''},now);
  }
  return{...I,simpleVersion:'1.1-stock',countStock,knownSale,reconciliation,moveStock,sellStock,packCounts,initializeOrigin,deliverSamples};
});
