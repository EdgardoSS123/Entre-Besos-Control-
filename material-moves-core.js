/* Reversible, idempotent supply/marketing movements. Never modifies bottle lots or sales. */
(function(root){
'use strict';
const copy=x=>JSON.parse(JSON.stringify(x)),text=x=>String(x??'').trim(),norm=x=>text(x).toLocaleLowerCase('es');
const field=k=>{if(k==='supplies')return'supplies';if(k==='marketing')return'materials';throw Error('Inventario no válido.');};
const fail=m=>{throw Error(m);},safe=(n,label)=>{if(!Number.isSafeInteger(n))fail('Importe o cantidad fuera de rango: '+label);return n;};
function rows(d,k){const a=d[field(k)]??[];if(!Array.isArray(a)||a.some(r=>!r||typeof r!=='object'))fail('Inventario inválido; no se modificó.');return a;}
function moves(d){const a=d.materialMovements??[];if(!Array.isArray(a))fail('Historial de movimientos inválido.');return a;}
function quantity(v){if(!['number','string'].includes(typeof v)||text(v)==='')fail('Escribe la cantidad.');const n=Number(v);if(!Number.isSafeInteger(n)||n<=0||n>1e12)fail('La cantidad debe ser un número entero mayor que cero.');return n;}
function date(v){v=text(v);if(!/^\d{4}-\d{2}-\d{2}$/.test(v)||!Number.isFinite(Date.parse(v+'T12:00:00Z'))||new Date(v+'T12:00:00Z').toISOString().slice(0,10)!==v)fail('Selecciona una fecha válida.');return v;}
function cents(v){const n=Number(v);return safe(Math.round(n*100),'costo');}
function basis(r){
 const q=safe(Number(r.qty),'existencias'),b=r.materialValue;
 if(b&&b.quantity===q&&Number.isSafeInteger(b.knownCents)&&Number.isSafeInteger(b.unknownQuantity)&&((b.unknownQuantity!==0&&r.totalCost===null)||(b.unknownQuantity===0&&r.totalCost===b.knownCents/100)))return{...b};
 const known=r.totalCost!==null&&r.totalCost!==undefined&&r.totalCost!==''&&Number.isFinite(Number(r.totalCost));
 return{quantity:q,knownCents:known?cents(r.totalCost):0,unknownQuantity:known?0:q};
}
function ratio(n,a,b){if(b<=0)fail('Base de reparto inválida.');const sign=n<0?-1n:1n;return safe(Number(sign*((BigInt(Math.abs(n))*BigInt(a)+BigInt(b)/2n)/BigInt(b))),'reparto');}
function allocation(r,n){const b=basis(r);if(b.quantity<=0)return{knownCents:0,unknownQuantity:n};const unknown=b.unknownQuantity?Math.max(0,Math.min(n,ratio(b.unknownQuantity,n,b.quantity))):0,knownQty=b.quantity-b.unknownQuantity;
 return{knownCents:knownQty>0?ratio(b.knownCents,n-unknown,knownQty):0,unknownQuantity:unknown};}
function applyEffect(d,k,e,sign,stamp){
 let r=rows(d,k).find(x=>x.id===e.recordId);if(!r)fail('El insumo asociado ya no existe. No se cambió el inventario.');
 const b=basis(r),q=safe(b.quantity+sign*e.quantity,'existencias'),cost=safe(b.knownCents+sign*e.knownCents,'costo'),u=safe(b.unknownQuantity+sign*e.unknownQuantity,'costo pendiente');
 r.qty=q;r.totalCost=u===0?cost/100:null;r.materialValue={quantity:q,knownCents:cost,unknownQuantity:u};r.updatedAt=stamp;
}
function identity(r){return[norm(r.name),norm(r.presentation),norm(r.unit||'unidades'),r.currency||'MXN'].join('|');}
function active(m){return m.status!=='cancelled';}
function change(data,kind,input,opts){
 field(kind);const options=opts||{},id=text(options.id),operation=text(options.operation),stamp=text(options.stamp);
 if(!id||!operation||!stamp)fail('Falta la referencia del movimiento.');
 const original=moves(data),old=original.find(x=>x.id===id),action=options.action||'save';
 const logs=data.materialMovementHistory??[];if(!Array.isArray(logs))fail('Historial de cambios inválido.');
 const request=JSON.stringify({id,kind,input,action}),prior=logs.find(x=>x.id===operation);
 if(prior){if(prior.request!==request)fail('Referencia de guardado ya utilizada.');return{data,record:old,unchanged:true,warnings:[]};}
 if(old&&(old.kind!==kind||JSON.stringify(old)!==options.expected))fail('Otro socio modificó este movimiento. Vuelve a abrirlo.');
 if(!old&&options.expected!==undefined)fail('El movimiento ya no existe.');
 if(!['save','cancel','restore'].includes(action))fail('Acción no válida.');
 if(action!=='save'&&!old)fail('No se encontró el movimiento.');
 if(action==='cancel'&&old.status==='cancelled')return{data,record:old,unchanged:true,warnings:[]};
 if(action==='save'&&old?.status==='cancelled')fail('Restaura el movimiento antes de editarlo.');
 if(action==='restore'&&old.status!=='cancelled')return{data,record:old,unchanged:true,warnings:[]};
 const next=copy(data);next[field(kind)]=copy(rows(data,kind));
 const inputValue=action==='save'?input:old;
 if(!inputValue)fail('Completa el movimiento.');
 const n=quantity(inputValue.quantity),type=inputValue.type;
 if(!['transfer','use'].includes(type))fail('Selecciona Mover o Registrar uso.');
 const status=action==='cancel'?'cancelled':action==='restore'?old.previousStatus:type==='use'?'used':inputValue.status;
 if(!['transit','received','used','cancelled'].includes(status)||(type==='transfer'&&status==='used'))fail('Estado no válido.');
 const purpose=text(inputValue.purpose),place=text(inputValue.to),notes=text(inputValue.notes),lotId=text(inputValue.lotId);
 if(!purpose||purpose.length>200)fail('Escribe para qué se mueve o utiliza (hasta 200 caracteres).');
 if(!place||place.length>160)fail('Indica el destino o lugar del uso (hasta 160 caracteres).');
 if(notes.length>1000)fail('Las notas admiten hasta 1,000 caracteres.');
 if(lotId&&!(data.lots||[]).some(l=>l.id===lotId)&&lotId!==old?.lotId)fail('Selecciona un lote existente.');
 const day=date(inputValue.date);
 let source=old?rows(next,kind).find(r=>r.id===old.sourceId):rows(next,kind)[options.index];
 if(!source)fail('Selecciona el insumo de origen.');
 if(!old&&JSON.stringify(source)!==options.expectedSource)fail('Las existencias cambiaron. Vuelve a abrir el movimiento.');
 if(type==='transfer'&&norm(source.loc)===norm(place))fail('El destino debe ser distinto de la bodega de origen.');
 if(!source.id)source.id='material-'+id;
 const sameStock=old&&old.type===type&&old.quantity===n&&norm(old.to)===norm(place)&&old.status===status;
 const equivalent=sameStock&&old.date===day&&old.purpose===purpose&&old.notes===notes&&old.lotId===lotId;
 if(equivalent)return{data,record:old,unchanged:true,warnings:[]};
 // Metadata edits do not recalculate or reapply a previously posted deduction.
 if(old&&active(old)&&!sameStock)for(const e of old.effects)applyEffect(next,kind,e,-1,stamp);
 let effects=sameStock?copy(old.effects):[],destinationId=sameStock?old.destinationId:null;
 let value=sameStock?{knownCents:old.knownCostCents,unknownQuantity:old.unknownCostQuantity}:null;
 if(status!=='cancelled'&&!sameStock){
  if(action==='restore'){
   effects=copy(old.effects);destinationId=old.destinationId;value={knownCents:old.knownCostCents,unknownQuantity:old.unknownCostQuantity};
   for(const e of effects)applyEffect(next,kind,e,1,stamp);
  }else{
   value=old&&old.type===type&&old.quantity===n&&norm(old.to)===norm(place)?{knownCents:old.knownCostCents,unknownQuantity:old.unknownCostQuantity}:allocation(source,n);
   effects.push({recordId:source.id,quantity:-n,knownCents:-value.knownCents,unknownQuantity:-value.unknownQuantity});
   if(type==='transfer'&&status==='received'){
    let dest=rows(next,kind).find(r=>norm(r.loc)===norm(place)&&identity(r)===identity(source));
    if(!dest){dest={id:'destination-'+id,name:source.name,loc:place,presentation:source.presentation||'',unit:source.unit||'unidades',currency:source.currency||'MXN',qty:0,totalCost:0,createdAt:stamp,updatedAt:stamp};next[field(kind)].push(dest);}
    if(!dest.id)dest.id='destination-'+id;
    destinationId=dest.id;effects.push({recordId:dest.id,quantity:n,knownCents:value.knownCents,unknownQuantity:value.unknownQuantity});
   }
   for(const e of effects)applyEffect(next,kind,e,1,stamp);
  }
 }
 if(status==='cancelled'){effects=copy(old.effects);destinationId=old.destinationId;value={knownCents:old.knownCostCents,unknownQuantity:old.unknownCostQuantity};}
 const record={...(old||{}),id,kind,type,status,previousStatus:status==='cancelled'?old.status:null,sourceId:source.id,destinationId:destinationId||null,name:source.name,presentation:source.presentation||'',unit:source.unit||'unidades',from:source.loc,to:place,quantity:n,date:day,purpose,notes,lotId,currency:source.currency||'MXN',knownCostCents:value.knownCents,unknownCostQuantity:value.unknownQuantity,costCents:value.unknownQuantity===0?value.knownCents:null,effects,version:(old?.version||0)+1,createdAt:old?.createdAt||stamp,updatedAt:stamp,actor:options.actor||''};
 next.materialMovements=copy(original);const i=next.materialMovements.findIndex(x=>x.id===id);if(i<0)next.materialMovements.push(record);else next.materialMovements[i]=record;
 next.materialMovementHistory=[...logs,{id:operation,kind,request,at:stamp,actor:options.actor||'',before:copy(old||null),after:copy(record),action:action==='save'?(old?'edit':'create'):action}];
 const touched=new Set([...(old?.effects||[]),...effects].map(e=>e.recordId));
 const warnings=rows(next,kind).filter(r=>touched.has(r.id)&&(r.qty<0||Number(r.totalCost)<0||basis(r).unknownQuantity<0)).map(r=>({name:r.name,loc:r.loc,qty:r.qty}));
 return{data:next,record,unchanged:false,warnings};
}
function summary(d,k){const result={transit:[],used:[]};for(const m of moves(d).filter(m=>m.kind===k&&active(m))){if(m.status==='transit')result.transit.push(m);if(m.type==='use')result.used.push(m);}return result;}
const api={change,rows,moves,summary,basis,allocation,identity};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBMaterialMoves=api;
})(typeof window==='undefined'?globalThis:window);
