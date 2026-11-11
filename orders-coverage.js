/* Read-only order planning. Uses the live ledger; never reserves or moves stock. */
(function(root){
'use strict';
const text=v=>String(v??'').trim();
function integer(value,label){
 const n=Number(value);
 if(value===null||value===''||!Number.isSafeInteger(n))throw Error('Revisa '+label+'.');
 return n;
}
function add(a,b){const n=a+b;if(!Number.isSafeInteger(n))throw Error('El total de botellas está fuera de rango.');return n;}
function build(data,ledger,orders){
 if(!ledger?.balance||!orders?.rows)throw Error('No se pudo consultar el inventario.');
 const partnerIds=new Set(orders.PARTNERS.map(p=>p.id));
 const pending=orders.rows(data).filter(o=>o.status==='pending'&&partnerIds.has(o.partner));
 const byLot=new Map(),warnings=[];
 const partners=orders.PARTNERS.map(p=>({id:p.id,name:p.name,count:0,quantity:0}));
 let otherOrigins=0;
 for(const order of pending){
  const partner=partners.find(p=>p.id===order.partner);partner.count++;
  if(order.from!=='CDMX')otherOrigins++;
  for(const line of order.lines){
   const product=integer(line.product,'la variedad del pedido'),q=integer(line.quantity,'la cantidad del pedido');
   if(product<0||product>=orders.PRODUCTS.length||q<=0||!text(line.lotId))throw Error('Hay un renglón de pedido incompleto.');
   const key=JSON.stringify([product,line.lotId]);
   const item=byLot.get(key)||{product,lotId:line.lotId,pending:0};
   item.pending=add(item.pending,q);byLot.set(key,item);partner.quantity=add(partner.quantity,q);
  }
 }
 const items=[];
 for(const item of byLot.values()){
  const lot=(data.lots||[]).find(l=>l.id===item.lotId);
  const valid=!!lot&&lot.p===item.product;
  let availableCDMX=0,availableOaxaca=0;
  if(!valid)warnings.push('Revisa el lote '+item.lotId+': no coincide con la variedad del pedido.');
  else{
   const b=ledger.balance(data,item.lotId);
   if(!b.configured)warnings.push('Lote '+item.lotId+': inventario sin capturar. No se supone existencia disponible.');
   for(const location of ['CDMX','Oaxaca']){
    const rows=b.rows.filter(r=>r.location===location);
    // Net negatives within a lot before clamping; samples never create stock.
    const physical=rows.reduce((n,r)=>add(n,integer(r.quantity,'el saldo de '+location)),0);
    const commercial=rows.reduce((n,r)=>add(n,integer(r.commercialQuantity,'el saldo comercial de '+location)),0);
    const available=Math.max(0,Math.min(physical,commercial));
    if(rows.some(r=>r.quantity<0||r.sampleQuantity<0||r.commercialQuantity<0))warnings.push('Lote '+item.lotId+' en '+location+': hay saldos por cuadrar.');
    if(location==='CDMX')availableCDMX=available;else availableOaxaca=available;
   }
  }
  const coveredCDMX=Math.min(item.pending,availableCDMX);
  const requestOaxaca=item.pending-coveredCDMX;
  const coveredOaxaca=Math.min(requestOaxaca,availableOaxaca);
  items.push({...item,ml:lot?.ml||null,availableCDMX,availableOaxaca,coveredCDMX,requestOaxaca,coveredOaxaca,shortage:requestOaxaca-coveredOaxaca});
 }
 const columns=['pending','availableCDMX','availableOaxaca','coveredCDMX','requestOaxaca','coveredOaxaca','shortage'];
 const sum=list=>Object.fromEntries(columns.map(k=>[k,list.reduce((n,r)=>add(n,r[k]),0)]));
 const varieties=orders.PRODUCTS.map((name,product)=>{const lots=items.filter(r=>r.product===product);return{product,name,lots,...sum(lots)};});
 return{orderCount:pending.length,partners,otherOrigins,varieties,items,warnings:[...new Set(warnings)],...sum(items)};
}
const api={build};
if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
root.EBOrderCoverage=api;
const esc=v=>text(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=n=>new Intl.NumberFormat('es-MX').format(n);
const boxes=n=>number(Math.floor(n/6))+' cajas'+(n%6?' + '+number(n%6)+' sueltas':'');
function amount(n){return'<b>'+number(n)+' <small>botellas</small></b><span>'+boxes(n)+'</span>';}
function cell(label,n,extra,kind){return'<div class="coverage-cell '+(kind||'')+'"><small>'+label+'</small>'+amount(n)+(extra?'<em>'+esc(extra)+'</em>':'')+'</div>';}
function render(data){
 const anchor=document.getElementById('orders-message');if(!anchor)return;
 let section=document.getElementById('orders-coverage');
 if(!section){section=document.createElement('section');section.id='orders-coverage';section.className='orders-coverage';section.setAttribute('aria-label','Total de pedidos y cobertura de inventario');anchor.after(section);}
 try{
  const m=build(data,root.EBLedger,root.EBOrders);
  const totals='<div class="coverage-totals">'+cell('Total pendiente',m.pending,m.orderCount+' pedidos · los 3 socios','coverage-primary')+cell('Cubres con CDMX',m.coveredCDMX,'Solo bodega principal')+cell('Pedir a Oaxaca',m.requestOaxaca,m.shortage?'Oaxaca cubre '+number(m.coveredOaxaca)+'; faltan '+number(m.shortage)+' más.':m.requestOaxaca?'Hay existencia suficiente en Oaxaca.':'No hace falta reponer para estos pedidos.',m.requestOaxaca?'coverage-needed':'')+'</div>';
  const rows=m.varieties.map(v=>'<div class="coverage-variety" data-coverage-product="'+v.product+'"><h3>'+esc(v.name)+'</h3><div class="coverage-variety-values">'+cell('Pedidos',v.pending)+cell('CDMX cubre',v.coveredCDMX,number(v.availableCDMX)+' disponibles en lotes pedidos')+cell('Pedir a Oaxaca',v.requestOaxaca,number(v.availableOaxaca)+' disponibles en Oaxaca',v.requestOaxaca?'coverage-needed':'')+'</div>'+(v.shortage?'<p class="coverage-warning">Con Oaxaca aún faltan <strong>'+number(v.shortage)+' botellas · '+boxes(v.shortage)+'</strong>.</p>':'')+'</div>').join('');
  const detail=m.items.map(l=>'<div class="coverage-lot"><strong>'+esc(root.EBOrders.PRODUCTS[l.product])+' · '+esc(l.lotId)+(l.ml?' · '+esc(l.ml)+' ml':'')+'</strong><p>Pedidos: '+number(l.pending)+' · CDMX cubre: '+number(l.coveredCDMX)+' · Pedir a Oaxaca: '+number(l.requestOaxaca)+' · Oaxaca puede surtir: '+number(l.coveredOaxaca)+'</p></div>').join('');
  section.innerHTML='<div class="coverage-heading"><h2>Pedidos de los tres socios</h2><p>Solo pendientes de entrega · total general, sin filtros.</p></div>'+totals+'<details class="coverage-details"><summary>Ver por variedad y lote</summary>'+rows+(m.items.length?'<details class="coverage-lot-details"><summary>Detalle por lote</summary>'+detail+'</details>':'')+'<p class="coverage-footnote">Se compara cada lote por separado: una variedad, presentación o lote no cubre otro. No incluye muestras, tránsito ni minibodegas. No reserva ni descuenta inventario.</p></details>'+(m.otherOrigins?'<p class="coverage-footnote">'+m.otherOrigins+' pedido(s) tienen salida en otra bodega. Este resumen planea surtir todos desde CDMX; no cambia sus bodegas de salida.</p>':'')+(m.warnings.length?'<p class="coverage-warning">'+m.warnings.map(esc).join('<br>')+'</p>':'');
 }catch(e){section.innerHTML='<p class="coverage-warning">No se pudo calcular la cobertura: '+esc(e.message)+' Los pedidos se conservan.</p>';}
}
api.render=render;
})(typeof window==='undefined'?globalThis:window);
