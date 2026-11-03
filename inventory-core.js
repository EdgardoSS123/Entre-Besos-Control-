'use strict';
/* Opening balances are a cut-over, never a fabricated history. */
(function(root){
  const VERSION='3.4',BOX=6,PALLET=480,HALF=240;
  const LOCATIONS=['Oaxaca','CDMX','USA','Singapur'];
  const LABELS=['Nacional','Exportación','Sin etiquetar','Por clasificar'];
  const CURRENCIES=['MXN','USD','SGD'];
  const KINDS={warehouse:'Bodega',distributor:'Distribuidor',client:'Cliente'};
  const PURPOSES={transfer:'Traslado de inventario propio',consignment:'Consignación',sale:'Entrega por venta'};
  const clone=x=>JSON.parse(JSON.stringify(x)),total=rows=>rows.reduce((s,r)=>s+r.quantity,0);
  const positiveInt=n=>Number.isSafeInteger(Number(n))&&Number(n)>0;
  function dateOK(s){return typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&!isNaN(Date.parse(s))&&new Date(s+'T12:00:00Z').toISOString().slice(0,10)===s;}
  function fail(s){throw new Error(s);}
  function pack(n,halves=false){
    if(!Number.isSafeInteger(n)||n<0)fail('La cantidad debe ser un número entero de botellas.');
    const full=Math.floor(n/PALLET);let rest=n%PALLET;
    const half=halves?Math.floor(rest/HALF):0;rest-=half*HALF;
    return{full,half,boxes:Math.floor(rest/BOX),bottles:rest%BOX,total:n,boxSize:BOX,palletSize:PALLET};
  }
  function quantity(v,unit,allowZero=false){
    const factors={bottle:1,box:BOX,pallet:PALLET,half:HALF};
    if(v===''||v===null||v===undefined||!Object.hasOwn(factors,unit)||(!positiveInt(v)&&!(allowZero&&Number(v)===0)))fail('Captura una cantidad entera válida y su unidad.');
    const n=Number(v)*factors[unit];if(!Number.isSafeInteger(n))fail('Cantidad fuera de rango.');return n;
  }
  function lotById(d,id){const lot=(d.lots||[]).find(l=>l.id===id);if(!lot)fail('No se encontró el lote. Guarda sus costos primero.');return lot;}
  function opening(d,id){return(d.inventoryOpenings||[]).find(x=>x.lotId===id)||null;}
  function locations(d){return [...new Set([...LOCATIONS,...(d.warehouses||[]).map(x=>x.name)])];}
  function locationInfo(d,name){
    const record=(d.warehouses||[]).find(x=>x.name===name);
    return{name,kind:record?.kind||'warehouse',address:record?.address||'',contact:record?.contact||''};
  }
  // Physical dispatch, delivery and ownership are separate. A sale is removed
  // from owned stock on confirmed delivery, not counted in the customer's depot.
  function purposeOf(s){return s.purpose||'transfer';}
  function shipments(d,id){return(d.lotShipments||[]).filter(x=>x.lotId===id);}
  function balance(d,id){
    const start=opening(d,id),map=new Map();
    const add=(where,tag,n)=>{const key=JSON.stringify([where,tag]);let row=map.get(key)||{location:where,tag,quantity:0};row.quantity+=n;map.set(key,row);};
    if(start)start.rows.forEach(r=>add(r.location,r.tag,r.quantity));
    let transit=0,deliveredSales=0;
    const active=shipments(d,id).filter(s=>!s.historical&&s.status!=='cancelled');
    if(start)active.forEach(s=>{
      add(s.from,s.tag,-s.quantity);
      if(s.status==='received'){
        if(purposeOf(s)==='sale')deliveredSales+=s.quantity;
        else add(s.to,s.tag,s.quantity);
      }else transit+=s.quantity;
    });
    const rows=[...map.values()];
    if(rows.some(r=>r.quantity<0))fail('El historial genera existencias negativas. No se modificó la información.');
    const atThirdParties=total(rows.filter(r=>locationInfo(d,r.location).kind!=='warehouse'));
    return{configured:!!start,complete:!!start?.complete,asOf:start?.asOf||null,rows,total:total(rows),transit,knownTotal:total(rows)+transit,atThirdParties,deliveredSales,opening:start};
  }
  function costTotals(d,id){
    const byCurrency={},included={},list=shipments(d,id).filter(s=>s.status!=='cancelled');let unknown=0;
    list.forEach(s=>{if(!s.cost||!s.cost.known){unknown++;return;}const bucket=s.cost.included?included:byCurrency;bucket[s.cost.currency]=(bucket[s.cost.currency]||0)+s.cost.amount;});
    for(const bucket of [byCurrency,included])Object.keys(bucket).forEach(k=>bucket[k]=Math.round(bucket[k]*100)/100);
    return{byCurrency,included,unknown};
  }
  function saveOpening(d,id,input,now){
    const lot=lotById(d,id),previous=opening(d,id);
    if(!Number.isSafeInteger(Number(lot.bottles))||Number(lot.bottles)<0)fail('Completa la producción de este lote antes de capturar existencias.');
    if(!dateOK(input.asOf)||input.asOf>now)fail('La fecha del inventario debe ser válida y no estar en el futuro.');
    if(shipments(d,id).some(s=>!s.historical&&s.status!=='cancelled'))fail('Ya hay envíos desde este corte. No reemplaces el inventario inicial.');
    if(!Array.isArray(input.rows))fail('Revisa las existencias por bodega.');
    const rows=[],inputRows=[],grouped=new Map();
    input.rows.forEach(r=>{
      if(!locations(d).includes(r.location))fail('La bodega no está registrada.');
      if(!LABELS.includes(r.tag))fail('Selecciona el tipo de etiqueta.');
      const n=quantity(r.amount,r.unit,true),key=JSON.stringify([r.location,r.tag]);
      inputRows.push({location:r.location,tag:r.tag,amount:Number(r.amount),unit:r.unit});
      if(grouped.has(key))grouped.get(key).quantity+=n;
      else{const item={location:r.location,tag:r.tag,quantity:n};rows.push(item);grouped.set(key,item);}
    });
    if(total(rows)>Number(lot.bottles))fail('El inventario inicial supera las botellas calculadas de este lote. Revisa la producción o el conteo.');
    if(!rows.length&&!input.complete)fail('Agrega una existencia o confirma el conteo completo en cero.');
    const next=clone(d),record={lotId:id,asOf:input.asOf,rows,inputRows,complete:!!input.complete,notes:String(input.notes||'').slice(0,2000),updatedAt:input.stamp};
    next.inventoryOpenings=next.inventoryOpenings||[];
    const at=next.inventoryOpenings.findIndex(x=>x.lotId===id);
    if(previous){next.inventoryOpeningRevisions=next.inventoryOpeningRevisions||[];next.inventoryOpeningRevisions.push({lotId:id,replacedAt:input.stamp,record:previous});next.inventoryOpenings[at]=record;}
    else next.inventoryOpenings.push(record);
    return next;
  }
  function saveShipment(d,id,input,now){
    lotById(d,id);const start=opening(d,id),historical=!!input.historical;
    if(!start&&!historical)fail('Primero registra el inventario inicial de este lote.');
    if(!locations(d).includes(input.to))fail('Selecciona la bodega, distribuidor o cliente de destino.');
    const destination=locationInfo(d,input.to),purpose=input.purpose||'transfer';
    if(!Object.hasOwn(PURPOSES,purpose))fail('Selecciona el motivo del envío.');
    if(destination.kind!=='warehouse'&&purpose==='transfer')fail('Para un distribuidor o cliente indica consignación o entrega por venta.');
    if(!historical&&!locations(d).includes(input.from))fail('Selecciona la bodega de origen.');
    if(input.from&&input.from===input.to)fail('El origen y destino deben ser diferentes.');
    if(!LABELS.includes(input.tag))fail('Selecciona el tipo de etiqueta.');
    const n=historical&&input.amount===''?null:quantity(input.amount,input.unit);
    if(!historical||input.date){if(!dateOK(input.date)||input.date>now)fail('Revisa la fecha del envío.');}
    if(!historical&&input.date<start.asOf)fail('El envío es anterior al corte. Regístralo como referencia histórica sin mover existencias.');
    if(historical&&start&&input.date&&input.date>start.asOf)fail('Las referencias históricas deben ser anteriores o iguales al corte inicial.');
    if(!historical){
      const latest=shipments(d,id).filter(x=>!x.historical&&x.status!=='cancelled').map(x=>x.receivedDate||x.date).sort().pop();
      if(latest&&input.date<latest)fail('Registra los movimientos en orden de fecha para conservar las existencias.');
      const available=balance(d,id).rows.find(r=>r.location===input.from&&r.tag===input.tag)?.quantity||0;
      if(n>available)fail('Solo hay '+available+' botellas de este lote y etiqueta en '+input.from+'.');
    }
    const known=!!input.costKnown,amount=known?Number(input.costAmount):null;
    if(known&&(input.costAmount===''||!Number.isFinite(amount)||amount<0||!CURRENCIES.includes(input.currency)))fail('Revisa importe y moneda del envío.');
    if(!input.id||(d.lotShipments||[]).some(s=>s.id===input.id))fail('Este envío ya se registró.');
    const next=clone(d),record={id:input.id,lotId:id,from:input.from||null,to:input.to,destination:clone(destination),purpose,inputAmount:n===null?null:Number(input.amount),inputUnit:input.unit,tag:input.tag,quantity:n,date:input.date||null,historical,status:historical?'historical':input.received?'received':'transit',receivedDate:!historical&&input.received?input.date:null,cost:{known,amount:known?Math.round(amount*100)/100:null,currency:input.currency||'MXN',included:known&&!!input.included},notes:String(input.notes||'').slice(0,2000),reference:String(input.reference||'').slice(0,120),createdAt:input.stamp};
    next.lotShipments=next.lotShipments||[];next.lotShipments.push(record);balance(next,id);return next;
  }
  function receive(d,id,shipmentId,date,now,stamp){
    const s=shipments(d,id).find(x=>x.id===shipmentId);if(!s||s.status!=='transit')fail('Este envío no está pendiente de recepción.');
    if(!dateOK(date)||date<s.date||date>now)fail('Revisa la fecha de recepción.');
    const latest=shipments(d,id).filter(x=>!x.historical&&x.status!=='cancelled').map(x=>x.receivedDate||x.date).sort().pop();
    if(latest&&date<latest)fail('La recepción no puede anteceder al último movimiento.');
    const next=clone(d),target=next.lotShipments.find(x=>x.id===shipmentId);target.status='received';target.receivedDate=date;target.receivedAt=stamp;balance(next,id);return next;
  }
  function addLocation(d,name,details={}){
    name=String(name||'').trim();if(name.length<2||name.length>100)fail('Escribe un nombre de destino de 2 a 100 caracteres.');
    const kind=details.kind||'warehouse';
    if(!Object.hasOwn(KINDS,kind))fail('Selecciona bodega, distribuidor o cliente.');
    if(locations(d).some(s=>s.toLocaleLowerCase()===name.toLocaleLowerCase()))fail('Este destino ya existe. Usa un nombre distinto para cada sucursal.');
    const next=clone(d);next.warehouses=next.warehouses||[];
    next.warehouses.push({name,kind,address:String(details.address||'').trim().slice(0,400),contact:String(details.contact||'').trim().slice(0,160)});
    return next;
  }
  const api={VERSION,BOX,PALLET,HALF,LOCATIONS,LABELS,CURRENCIES,KINDS,PURPOSES,locationInfo,purposeOf,pack,quantity,opening,locations,shipments,balance,costTotals,saveOpening,saveShipment,receive,addLocation};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBLedger=api;
})(typeof window==='undefined'?globalThis:window);
