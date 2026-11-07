/* Read-only executive report. Unknowns remain unknown; currencies never mixed. */
(function(root){
'use strict';
const node=typeof module!=='undefined'&&module.exports;
const P=node?require('./packaging.js'):root.EBPackages,C=node?require('./contacts-core.js'):root.EBContacts;
const products=['Espadín Capón','Cupreata','Dark Blend'],valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const num=n=>new Intl.NumberFormat('es-MX',{maximumFractionDigits:2}).format(n);
const money=(v,c='MXN')=>valid(v)?new Intl.NumberFormat('es-MX',{style:'currency',currency:/^[A-Z]{3}$/.test(c)?c:'MXN'}).format(Number(v))+' '+c:'Sin capturar';
const qty=n=>num(n)+' bot.\n'+P.describe(n,true);
function arr(d,k){if(d[k]===undefined)return[];if(!Array.isArray(d[k]))throw Error('Formato no válido en '+k+'. No se modificaron datos.');return d[k];}
const section=(title,head,body,right=[],extra={})=>({title,head,body,right,...extra});
function build(d,I,opts={}){
 if(!d||!Array.isArray(d.lots)||!Array.isArray(d.moves)||!I?.reconciliation)throw Error('No se pudo leer el inventario para el resumen.');
 const model={title:'Resumen general',subtitle:'Dónde estamos parados',file:'resumen-general',scope:'Todos los lotes, bodegas y registros guardados',metrics:[],sections:[],notes:[]};
 const balances=d.lots.map(l=>({l,b:I.reconciliation(d,l.id)}));
 const totals={produced:0,sold:0,samples:0,stock:0,commercial:0,reserved:0,transit:0,productionCost:0,stockCost:0,sampleCost:0,missingCount:0,missingStockCost:0,missingProductionCost:0};
 const locations=new Map(),diff=[];
 balances.forEach(({l,b})=>{
  totals.produced+=b.produced;totals.sold+=b.sold;totals.samples+=b.used;totals.transit+=b.transit;
  if(b.configured){totals.stock+=b.total;totals.commercial+=b.commercialTotal;totals.reserved+=b.sampleTotal;}else totals.missingCount++;
  if(valid(l.totalCost))totals.productionCost+=Number(l.totalCost);else totals.missingProductionCost++;
  if(valid(l.unitCost)){if(b.configured)totals.stockCost+=b.total*Number(l.unitCost);totals.sampleCost+=b.used*Number(l.unitCost);}else totals.missingStockCost++;
  for(const r of b.rows){const z=locations.get(r.location)||{quantity:0,commercial:0,samples:0,cost:0,missing:0};z.quantity+=r.quantity;z.commercial+=r.commercialQuantity||0;z.samples+=r.sampleQuantity||0;if(valid(l.unitCost))z.cost+=r.quantity*Number(l.unitCost);else z.missing++;locations.set(r.location,z);}
  if(b.unexplained)diff.push([l.id,num(Math.abs(b.unexplained))+' botellas',b.unexplained<0?'Registradas de más':'Por ubicar o explicar']);
 });
 const finance=new Map();
 for(const {l} of balances)for(const s of I.sales(d,l.id)){
  const c=s.currency||'MXN',f=finance.get(c)||{sales:0,paid:0,pending:0,unknownPayment:0,unknownPrice:0,count:0};f.count++;
  const priced=s.priceKnown!==false&&valid(s.totalCents),st=I.saleStatus(s,new Date().toISOString().slice(0,10));
  if(priced){f.sales+=Number(s.totalCents);if(valid(st.paidCents)&&valid(st.pendingCents)){f.paid+=Number(st.paidCents);f.pending+=Number(st.pendingCents);}else f.unknownPayment+=Number(s.totalCents);}else f.unknownPrice++;
  finance.set(c,f);
 }
 const stockNote=totals.missingCount?totals.missingCount+' lote(s) sin conteo':'En todas las ubicaciones';
 model.metrics=[{label:'SALDO EN BODEGAS',value:num(totals.stock),note:stockNote},{label:'VENDIDAS',value:num(totals.sold),note:'Botellas registradas'},{label:'MUESTRAS ENTREGADAS',value:num(totals.samples),note:'Botellas · ingreso $0'},{label:'LOTES REGISTRADOS',value:num(balances.length),note:num(totals.produced)+' botellas producidas'}];
 // Partner-facing sales are aggregated only: no buyer list or collection details.
 model.sections.push(section('Ventas',['Moneda','Ventas'],[...finance].map(([c,f])=>[c,money(f.sales/100,c)]),[1]));
 model.sections.push(section('Lo que tenemos y lo que ha costado',['Concepto','Importe registrado','Lectura'],[
 ['Producción de los lotes',money(totals.productionCost),totals.missingProductionCost?totals.missingProductionCost+' lote(s) sin costo total':'Costo de producción; no equivale a dinero disponible'],
 ['Producto en bodegas, a costo',money(totals.stockCost),totals.missingStockCost?totals.missingStockCost+' lote(s) sin costo por botella':'Saldo por lote × su costo por botella'],
 ['Muestras entregadas, a costo',money(totals.sampleCost),'Costo del producto entregado; ingreso $0'],
 ],[1],{note:'No se suman estos tres importes: el producto disponible y las muestras provienen de la producción. El saldo bancario no se puede deducir de estos registros.'}));
 model.sections.push(section('Dónde está el producto',['Bodega / ubicación','Saldo en botellas y empaque','Para venta','Muestras en bodega','Valor a costo · MXN'],[...locations].map(([loc,z])=>[loc,qty(z.quantity),num(z.commercial),num(z.samples),money(z.cost)+(z.missing?'\nCosto parcial':'')]),[1,2,3,4]));
 model.sections.push(section('Cada lote: producción, salidas y saldo',['Lote / variedad','Producidas','Vendidas','Muestras entregadas','Saldo actual','Costo por botella'],balances.map(({l,b})=>[l.id+'\n'+(products[l.p]||'Producto'),num(b.produced),num(b.sold),num(b.used),b.configured?qty(b.total):'Conteo pendiente',money(l.unitCost)]),[1,2,3,4,5]));
 const orderExits=balances.filter(({b})=>b.orderDelivered);if(orderExits.length)model.sections.push(section('Salidas por pedidos',['Lote','Botellas entregadas','Equivalencia'],orderExits.map(({l,b})=>[l.id,num(b.orderDelivered),P.describe(b.orderDelivered,true)]),[1],{note:'Estas entregas ya están descontadas del saldo. Se muestran aparte de ventas y muestras; no generan ingresos ni cobros automáticamente.'}));
 model.sections.push(section('Diferencias que requieren revisión',['Lote','Botellas','Situación'],diff,[1],{empty:'Sin diferencias calculadas en los lotes registrados. No sustituye un conteo físico.'}));
 if(totals.transit)model.sections.push(section('Producto en tránsito',['Estado','Cantidad'],[['Fuera de bodega, pendiente de recepción',qty(totals.transit)]],[1]));
 const materials={};
 for(const [key,label] of [['materials','Material de marketing'],['supplies','Insumos']]){
  const rows=arr(d,key),costs=new Map();let missing=0;
  for(const r of rows){if(valid(r.totalCost)){const c=r.currency||'MXN';costs.set(c,(costs.get(c)||0)+Number(r.totalCost));}else missing++;}
  materials[key]={count:rows.length,costs:Object.fromEntries(costs),missing};
  model.sections.push(section(label+' · existencias y costo',['Concepto / presentación','Ubicación','Cantidad','Costo total','Costo por unidad'],rows.map(r=>[String(r.name||'Sin concepto')+(r.presentation?'\n'+r.presentation:''),r.loc||'Sin ubicación',valid(r.qty)?num(Number(r.qty))+' '+(r.unit||'unidades'):'Sin capturar',money(r.totalCost,r.currency||'MXN'),valid(r.totalCost)&&Number(r.qty)>0?money(Number(r.totalCost)/Number(r.qty),r.currency||'MXN'):'No calculable']),[2,3,4]));
  model.sections.push(section('Total registrado · '+label.toLowerCase(),['Moneda','Costo total','Costos pendientes'],[...costs].map(([c,n])=>[c,money(n,c),num(missing)+' registros sin costo']),[1,2],{empty:rows.length?'No hay costos capturados. Los materiales no se consideran gratuitos.':'Sin inventario registrado; no se asume existencia cero.'}));
 }
 // Legacy sales remain separate to avoid double counting, but never itemized by buyer.
 const legacy=arr(d,'sales').filter(s=>s.status!=='cancelled'),legacyTotals=new Map();
 for(const s of legacy){const c=s.currency||'MXN',f=legacyTotals.get(c)||{count:0,amount:0,missing:0};f.count++;if(valid(s.amount))f.amount+=Number(s.amount);else f.missing++;legacyTotals.set(c,f);}
 if(legacy.length)model.sections.push(section('Ventas antiguas sin vínculo a lote',['Moneda','Registros','Importe conocido','Sin precio'],[...legacyTotals].map(([c,f])=>[c,num(f.count),f.count>f.missing?money(f.amount,c):'Sin capturar',num(f.missing)]),[1,2,3],{note:'Totales separados, no sumados a ventas por lote hasta confirmar si son operaciones distintas o duplicadas.'}));
 const expenses=arr(d,'expenses').filter(x=>x.status!=='cancelled'),expenseTotals=new Map();
 expenses.forEach(e=>{if(valid(e.amount)){const c=e.currency||'MXN';expenseTotals.set(c,(expenseTotals.get(c)||0)+Number(e.amount));}});
 model.sections.push(section('Gastos registrados',['Concepto','Fecha / mes','Importe','Notas'],expenses.map(e=>[e.type||e.name||e.concept||'Sin concepto',e.date||e.month||'Sin fecha',money(e.amount,e.currency||'MXN'),e.notes||'']),[2]));
 if(expenses.length)model.sections.push(section('Total de gastos por moneda',['Moneda','Importe'],[...expenseTotals].map(([c,n])=>[c,money(n,c)]),[1],{note:'No se resta de ventas como una utilidad definitiva: faltan conciliación, impuestos y posibles costos ya incluidos.'}));
 const freight=balances.flatMap(({l})=>I.shipments(d,l.id).filter(s=>s.status!=='cancelled').map(s=>({l,s})));
 if(freight.length)model.sections.push(section('Fletes y costos de movimientos',['Lote','Origen → destino','Cantidad','Costo capturado','Tratamiento'],freight.map(({l,s})=>[l.id,(s.from||'—')+' → '+(s.to||'—'),Number.isSafeInteger(s.quantity)?qty(s.quantity):'Sin cantidad',s.cost?.known?money(s.cost.amount,s.cost.currency||'MXN'):'Sin capturar',s.cost?.included?'Ya incluido en costeo':'Revisar por separado']),[2,3],{note:'No se suman otra vez los costos marcados como incluidos. Un mismo flete podría estar también en Gastos; requiere conciliación.'}));
 const docs=arr(d,'documents'),contacts=C.rows(d).map(C.view),date=new Date().toLocaleDateString('en-CA',{timeZone:'America/Mexico_City'}),limit=new Date(new Date(date+'T12:00:00Z').getTime()+30*86400000).toISOString().slice(0,10);
 model.sections.push(section('Directorio y documentación',['Registro','Cantidad','Detalle'],[
 ...C.COUNTRIES.map(c=>['Contactos · '+c,num(contacts.filter(x=>x.country===c).length),'Nombre, lugar, correo y teléfono']),
 ['Contactos sin país',num(contacts.filter(x=>!x.country).length),'Registros anteriores por clasificar'],
 ['Documentos registrados',num(docs.length),'Fichas guardadas'],
 ['Documentos vencidos',num(docs.filter(x=>x.expiry&&x.expiry<date).length),'Según fechas capturadas'],
 ['Por vencer en 30 días',num(docs.filter(x=>x.expiry&&x.expiry>=date&&x.expiry<=limit).length),'Según fechas capturadas']
 ],[1]));
 if(!balances.length)model.notes.push('No hay lotes guardados en la base consultada. Este documento no acredita que el negocio carezca de inventario.');
 if(totals.missingCount)model.notes.push('Inventario parcial: '+totals.missingCount+' lote(s) sin conteo. Los totales corresponden únicamente a existencias registradas.');
 const missingPrices=[...finance.values()].reduce((s,f)=>s+f.unknownPrice,0);if(missingPrices)model.notes.push(missingPrices+' venta(s) sin precio no se incluyen en los importes de ventas.');
 model.notes.push('1 caja = 6 botellas. 1 pallet = 80 cajas = 480 botellas. En el desglose, las cajas están fuera de los pallets y las sueltas fuera de las cajas.','Los saldos negativos y diferencias se muestran, no se corrigen automáticamente. Muestras en bodega siguen en inventario; las entregadas ya salieron.','Los costos de marketing e insumos son los capturados para esas existencias. No se suman a producción porque puede existir doble registro del mismo gasto.','No es un balance contable certificado: no hay saldo bancario ni utilidad neta confirmada. Solo información guardada; las capturas sin guardar no se incluyen.');
 if(opts.revision!==undefined)model.notes.push('Base compartida · versión '+opts.revision+(opts.updated?' · último guardado '+opts.updated:''));
 model.summary={...totals,finance:Object.fromEntries(finance),materials,locations:[...locations].map(([name,v])=>({name,...v})),contacts:contacts.length,documents:docs.length};return model;
}
const api={build,money,num};if(node)module.exports=api;else root.EBExecutive=api;
})(typeof window==='undefined'?globalThis:window);
