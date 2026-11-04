'use strict';
/* Internal commercial ledger. No tax calculation or official accounting entries.
   Prior data is never migrated or reclassified without an explicit save. */
(function(root,factory){
  if(typeof module!=='undefined'&&module.exports)module.exports=factory;
  else root.EBLedger=factory(root.EBLedger);
})(typeof window==='undefined'?globalThis:window,function(base){
  const copy=x=>JSON.parse(JSON.stringify(x)),fail=m=>{throw Error(m);};
  const key=(l,t)=>JSON.stringify([l,t]);
  const lot=(d,id)=>{const l=(d.lots||[]).find(x=>x.id===id);if(!l)fail('Guarda el lote primero.');return l;};
  const active=s=>s.status!=='cancelled';
  const sales=(d,id)=>(d.lotSales||[]).filter(x=>x.lotId===id&&active(x));
  const actions=(d,id)=>(d.lotSampleActions||[]).filter(x=>x.lotId===id&&active(x));
  const priceCost=l=>Number.isFinite(l.unitCost)&&l.unitCost>=0?l.unitCost:null;
  function dateOK(s){return typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&!isNaN(Date.parse(s))&&new Date(s+'T12:00:00Z').toISOString().slice(0,10)===s;}
  function cents(v,zero=true){
    if(v===null||v===undefined||String(v).trim()===''||!/^\d+(?:\.\d{1,2})?$/.test(String(v).trim()))fail('Captura un importe válido con hasta 2 decimales.');
    const n=Math.round(Number(v)*100);if(!Number.isSafeInteger(n)||n<0||(!zero&&n===0))fail('El precio de venta debe ser mayor que cero. Para entrega gratuita utiliza Muestra.');return n;
  }
  function validateDate(date,now){if(!dateOK(date)||date>now)fail('Revisa la fecha; no puede estar en el futuro.');}
  function lastMovement(d,id){return [...base.shipments(d,id).filter(s=>!s.historical&&active(s)).map(s=>s.receivedDate||s.date),...sales(d,id).filter(s=>s.stockEffect).map(s=>s.date),...actions(d,id).map(x=>x.date)].filter(Boolean).sort().pop();}
  function afterCut(d,id,date,now){
    validateDate(date,now);const o=base.opening(d,id);if(!o)fail('Primero guarda el inventario inicial.');
    if(date<o.asOf)fail('La operación es anterior al inventario inicial. Usa la opción de venta histórica sin descuento.');
    const last=lastMovement(d,id);if(last&&date<last)fail('Registra los movimientos en orden de fecha.');
  }
  function unique(d,id){if(!id||[...(d.lotSales||[]),...(d.lotSampleActions||[]),...(d.lotShipments||[])].some(x=>x.id===id))fail('Esta operación ya fue registrada.');}
  function balance(d,id){
    const b=base.balance(d,id),map=new Map(b.rows.map(r=>[key(r.location,r.tag),{...r,sampleQuantity:0}]));
    const row=(where,tag)=>{const k=key(where,tag);if(!map.has(k))map.set(k,{location:where,tag,quantity:0,sampleQuantity:0});return map.get(k);};
    if(b.opening)for(const r of b.opening.rows)row(r.location,r.tag).sampleQuantity+=Number(r.sampleQuantity||0);
    let sampleTransit=0,samplesUsed=0,directSales=0;
    for(const s of base.shipments(d,id).filter(s=>!s.historical&&active(s))){
      if(s.stockType==='sample')row(s.from,s.tag).sampleQuantity-=s.quantity;
      if(base.purposeOf(s)==='sample'||s.stockType==='sample'){
        if(s.status==='received'&&base.purposeOf(s)!=='sale')row(s.to,s.tag).sampleQuantity+=s.quantity;
        else if(s.status==='transit')sampleTransit+=s.quantity;
      }
    }
    for(const a of actions(d,id)){
      const r=row(a.location,a.tag);
      if(a.type==='reserve')r.sampleQuantity+=a.quantity;
      else if(a.type==='release')r.sampleQuantity-=a.quantity;
      else if(a.type==='consume'){r.quantity-=a.quantity;r.sampleQuantity-=a.quantity;samplesUsed+=a.quantity;}
    }
    for(const s of sales(d,id))if(s.stockEffect){row(s.from,s.tag).quantity-=s.quantity;directSales+=s.quantity;}
    const rows=[...map.values()].map(r=>({...r,commercialQuantity:r.quantity-r.sampleQuantity}));
    if(rows.some(r=>!Number.isSafeInteger(r.quantity)||!Number.isSafeInteger(r.sampleQuantity)||r.quantity<0||r.sampleQuantity<0||r.sampleQuantity>r.quantity))fail('La operación deja inventario comercial o muestras insuficientes. No se guardó.');
    const total=rows.reduce((n,r)=>n+r.quantity,0),sampleTotal=rows.reduce((n,r)=>n+r.sampleQuantity,0);
    return {...b,rows,total,knownTotal:total+b.transit,atThirdParties:rows.filter(r=>base.locationInfo(d,r.location).kind!=='warehouse').reduce((n,r)=>n+r.quantity,0),deliveredSales:b.deliveredSales+directSales,sampleTotal,sampleTransit,samplesUsed,commercialTotal:total-sampleTotal};
  }
  function available(d,id,where,tag,type='commercial'){const r=balance(d,id).rows.find(r=>r.location===where&&r.tag===tag);return r?(type==='sample'?r.sampleQuantity:r.commercialQuantity):0;}
  function saveOpening(d,id,input,now){
    if(sales(d,id).some(s=>s.stockEffect)||actions(d,id).length)fail('Ya hay ventas o clasificación de muestras desde este corte. No reemplaces el inventario inicial.');
    const next=base.saveOpening(d,id,input,now),o=base.opening(next,id),samples=new Map();
    input.rows.forEach((r,i)=>{o.inputRows[i].isSample=r.isSample===true;if(r.isSample===true){const k=key(r.location,r.tag);samples.set(k,(samples.get(k)||0)+base.quantity(r.amount,r.unit,true));}});
    o.rows.forEach(r=>r.sampleQuantity=samples.get(key(r.location,r.tag))||0);
    o.sampleAccounting={category:'Muestras y promoción',income:0,receivable:0,unitCostMXN:priceCost(lot(d,id)),note:'Existencias destinadas a muestra, no consumo confirmado.'};
    balance(next,id);return next;
  }
  function saveShipment(d,id,input,now){
    const purpose=input.purpose||'transfer',stockType=input.stockType||'commercial';
    if(!['commercial','sample'].includes(stockType))fail('Selecciona inventario comercial o muestras.');
    if(stockType==='sample'&&purpose==='sale')fail('Las muestras no se venden. Reclasifica expresamente a inventario comercial antes de vender.');
    if(!input.historical){afterCut(d,id,input.date,now);const n=base.quantity(input.amount,input.unit),a=available(d,id,input.from,input.tag,stockType);if(n>a)fail('Solo hay '+a+' botellas '+(stockType==='sample'?'de muestra':'comerciales')+' disponibles en '+input.from+'.');}
    const next=base.saveShipment(d,id,input,now),s=next.lotShipments.find(x=>x.id===input.id);s.stockType=stockType;
    if(purpose==='sample'||stockType==='sample')s.sampleAccounting={category:'Muestras y promoción',income:0,receivable:0,unitCostMXN:priceCost(lot(d,id)),paymentStatus:'No aplica',note:'Traslado de muestras; no representa venta ni consumo.'};
    balance(next,id);return next;
  }
  function receive(d,id,sid,date,now,stamp){afterCut(d,id,date,now);const next=base.receive(d,id,sid,date,now,stamp);balance(next,id);return next;}
  function sampleAction(d,id,input,now){
    const l=lot(d,id);unique(d,input.id);afterCut(d,id,input.date,now);
    if(!['reserve','release','consume'].includes(input.type))fail('Selecciona la operación de muestras.');
    if(!base.locations(d).includes(input.location)||!base.LABELS.includes(input.tag))fail('Selecciona ubicación y etiqueta.');
    const n=base.quantity(input.amount,input.unit),source=input.type==='reserve'?'commercial':'sample',a=available(d,id,input.location,input.tag,source);
    if(n>a)fail('Solo hay '+a+' botellas '+(source==='sample'?'de muestra':'comerciales')+' disponibles.');
    const notes=String(input.notes||'').trim();if(input.type!=='reserve'&&!notes)fail('Indica el motivo o destinatario para conservar el historial.');
    const next=copy(d),unitCostMXN=priceCost(l);
    (next.lotSampleActions=next.lotSampleActions||[]).push({id:input.id,lotId:id,type:input.type,location:input.location,tag:input.tag,quantity:n,date:input.date,notes:notes.slice(0,2000),createdAt:input.stamp,category:'Muestras y promoción',income:0,receivable:0,unitCostMXN,costMXN:unitCostMXN===null?null:Math.round(n*unitCostMXN*100)/100});
    balance(next,id);return next;
  }
  function quote(n,price,basis){if(!['bottle','box'].includes(basis))fail('El precio debe ser por botella o por caja de 6.');const value=cents(price,false),totalCents=Math.round(n*value/(basis==='box'?6:1));if(!Number.isSafeInteger(totalCents)||totalCents<=0)fail('Revisa el total de la venta.');return{priceCents:value,priceBasis:basis,totalCents};}
  function status(s,now){const paidCents=(s.payments||[]).reduce((n,p)=>n+p.amountCents,0),pendingCents=s.totalCents-paidCents;return{paidCents,pendingCents,status:pendingCents===0?'Pagada':paidCents>0?'Pago parcial':'Pendiente',overdue:pendingCents>0&&!!s.dueDate&&s.dueDate<now};}
  function saveSale(d,id,input,now){
    const l=lot(d,id);unique(d,input.id);validateDate(input.date,now);
    const mode=input.mode||'direct';if(!['direct','shipment','historical'].includes(mode))fail('Selecciona cómo registrar la venta.');
    let n,from,tag,customer,shipmentId=null;
    if(mode==='shipment'){
      const s=base.shipments(d,id).find(s=>s.id===input.shipmentId&&active(s));
      if(!s||base.purposeOf(s)!=='sale'||!Number.isSafeInteger(s.quantity)||s.quantity<=0)fail('Selecciona un envío por venta con cantidad conocida.');
      if(sales(d,id).some(x=>x.shipmentId===s.id))fail('Este envío ya tiene venta y precio registrados.');
      n=s.quantity;from=s.from;tag=s.tag;customer=s.to;shipmentId=s.id;
    }else{
      n=base.quantity(input.amount,input.unit);from=input.from;tag=input.tag;customer=String(input.customer||'').trim();
      if(!base.locations(d).includes(from)||!base.LABELS.includes(tag))fail('Selecciona ubicación de salida y etiqueta.');
      if(mode==='direct'){afterCut(d,id,input.date,now);const a=available(d,id,from,tag);if(n>a)fail('Solo hay '+a+' botellas comerciales; las muestras no están disponibles para venta.');}
      else{const o=base.opening(d,id);if(!o)fail('Primero guarda el inventario inicial.');if(input.date>o.asOf)fail('La venta histórica debe ser anterior o igual al corte inicial.');if(n>Number(l.bottles))fail('La cantidad supera la producción declarada del lote.');}
    }
    if(!customer||customer.length>160)fail('Captura el nombre del cliente (máximo 160 caracteres).');
    if(!base.CURRENCIES.includes(input.currency))fail('Selecciona la moneda de la venta.');
    const q=quote(n,input.price,input.priceBasis),dueDate=input.dueDate||'';if(dueDate&&(!dateOK(dueDate)||dueDate<input.date))fail('El vencimiento debe ser igual o posterior a la venta.');
    const paid=cents(input.paidAmount??0);if(paid>q.totalCents)fail('El cobro no puede superar el total de la venta.');
    if(paid)validateDate(input.paymentDate||input.date,now);
    const unitCostMXN=priceCost(l),record={id:input.id,lotId:id,mode,stockEffect:mode==='direct',shipmentId,from,tag,customer,quantity:n,inputAmount:mode==='shipment'?n:Number(input.amount),inputUnit:mode==='shipment'?'bottle':input.unit,...q,currency:input.currency,date:input.date,dueDate,reference:String(input.reference||'').slice(0,160),notes:String(input.notes||'').slice(0,2000),createdAt:input.stamp,unitCostMXN,costMXN:unitCostMXN===null?null:Math.round(n*unitCostMXN*100)/100,payments:paid?[{id:input.id+'-initial',amountCents:paid,date:input.paymentDate||input.date,reference:'Cobro capturado al registrar la venta',createdAt:input.stamp}]:[]};
    const next=copy(d);(next.lotSales=next.lotSales||[]).push(record);next.saleCustomers=next.saleCustomers||[];
    if(!next.saleCustomers.some(c=>c.name.toLocaleLowerCase()===customer.toLocaleLowerCase()))next.saleCustomers.push({name:customer});
    balance(next,id);return next;
  }
  function addPayment(d,id,sid,input,now){
    const s=sales(d,id).find(s=>s.id===sid);if(!s)fail('Venta no encontrada.');
    if(!input.id||(s.payments||[]).some(p=>p.id===input.id))fail('Este pago ya se registró.');
    validateDate(input.date,now);const amountCents=cents(input.amount,false),pending=status(s,now).pendingCents;
    if(amountCents>pending)fail('El pago supera el saldo pendiente.');
    const next=copy(d),target=next.lotSales.find(x=>x.id===sid);(target.payments=target.payments||[]).push({id:input.id,amountCents,date:input.date,reference:String(input.reference||'').slice(0,160),createdAt:input.stamp});return next;
  }
  function summary(d,id,now){
    const byCurrency={};for(const s of sales(d,id)){const b=byCurrency[s.currency]||(byCurrency[s.currency]={totalCents:0,paidCents:0,pendingCents:0}),p=status(s,now);b.totalCents+=s.totalCents;b.paidCents+=p.paidCents;b.pendingCents+=p.pendingCents;}
    const b=balance(d,id),l=lot(d,id),used=actions(d,id).filter(x=>x.type==='consume');
    return{byCurrency,balance:b,samples:{quantity:b.sampleTotal,inTransit:b.sampleTransit,income:0,receivable:0,referenceCostMXN:priceCost(l)===null?null:Math.round(b.sampleTotal*l.unitCost*100)/100,used:b.samplesUsed,consumedCostMXN:used.some(x=>x.costMXN===null)?null:used.reduce((n,x)=>n+x.costMXN,0)},unpricedShipments:base.shipments(d,id).filter(s=>active(s)&&base.purposeOf(s)==='sale'&&!sales(d,id).some(x=>x.shipmentId===s.id))};
  }
  base.PURPOSES.sample='Muestra sin cargo · ingreso $0';
  return {...base,commerceVersion:'1.0',balance,available,saveOpening,saveShipment,receive,sampleAction,sales,sampleActions:actions,quote,saleStatus:status,saveSale,addPayment,commercialSummary:summary};
});
