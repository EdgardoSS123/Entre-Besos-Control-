from pathlib import Path
r=Path('.')
def edit(name,pairs):
 p=r/name;s=p.read_text()
 for a,b in pairs:
  assert a in s,(name,a[:90])
  s=s.replace(a,b)
 p.write_text(s)
edit('inventory-core.js',[
 ("if(!Number.isSafeInteger(n)||n<0)fail('La cantidad debe ser un número entero de botellas.');\n    const full=Math.floor(n/PALLET);let rest=n%PALLET;","if(!Number.isSafeInteger(n))fail('La cantidad debe ser un número entero de botellas.');\n    const signed=n;n=Math.abs(n);\n    const full=Math.floor(n/PALLET);let rest=n%PALLET;"),
 ("bottles:rest%BOX,total:n,boxSize:BOX,palletSize:PALLET","bottles:rest%BOX,total:signed,...(signed<0?{sign:-1}:{}),boxSize:BOX,palletSize:PALLET"),
 ("if(rows.some(r=>r.quantity<0))fail('El historial genera existencias negativas. No se modificó la información.');","if(rows.some(r=>!Number.isSafeInteger(r.quantity)))fail('Cantidad de inventario fuera de rango.');"),
 ("if(total(rows)>Number(lot.bottles))fail('El inventario inicial supera las botellas calculadas de este lote. Revisa la producción o el conteo.');","// Differences remain visible for reconciliation."),
 ("if(n>available)fail('Solo hay '+available+' botellas de este lote y etiqueta en '+input.from+'.');","// Preserve known dispatches even when counts need reconciliation.")])
edit('commerce-core.js',[
 ("r.quantity<0||r.sampleQuantity<0||r.sampleQuantity>r.quantity","!Number.isSafeInteger(r.commercialQuantity)"),
 ("La operación deja inventario comercial o muestras insuficientes. No se guardó.","La cantidad de inventario está fuera de rango."),
 ("if(n>a)fail('Solo hay '+a+' botellas disponibles en '+input.from+'.');","// Preserve signed balances for reconciliation."),
 ("Math.min(n,r?.sampleQuantity||0)","Math.max(0,Math.min(n,r?.sampleQuantity||0))"),
 ("if(n>a)fail('Solo hay '+a+' botellas '+(source==='sample'?'de muestra':'comerciales')+' disponibles.');","// Known samples can be recorded before correcting counts."),
 ("Math.min(n,available(d,id,input.location,input.tag,'sample'))","Math.max(0,Math.min(n,available(d,id,input.location,input.tag,'sample')))"),
 ("if(n>a)fail('Solo hay '+a+' botellas comerciales; las muestras no están disponibles para venta.');","/* Negative balances are shown, not rejected. */"),
 ("if(n>Number(l.bottles))fail('La cantidad supera la producción declarada del lote.');","/* Production differences stay visible. */"),
 ("return {...b,rows,total,knownTotal:","const stockWarnings=rows.filter(r=>r.quantity<0||r.sampleQuantity<0||r.commercialQuantity<0).map(r=>({location:r.location,tag:r.tag,quantity:r.quantity,sampleQuantity:r.sampleQuantity,commercialQuantity:r.commercialQuantity}));\n    return {...b,stockWarnings,rows,total,knownTotal:")])
edit('simple-core.js',[("if(!Number.isSafeInteger(n)||n<0)fail('Cantidad de botellas inválida.');\n    return {bottles:n,fullCases:Math.floor(n/6),looseBottles:n%6,caseSize:6,equivalentCases:n/6};","if(!Number.isSafeInteger(n))fail('Cantidad de botellas inválida.');\n    return {bottles:n,...(n<0?{sign:-1}:{}),fullCases:Math.floor(Math.abs(n)/6),looseBottles:Math.abs(n)%6,caseSize:6,equivalentCases:n/6};")])
edit('corrections-core.js',[
 ("try{I.balance(d,id);}catch(e){fail('No se guardó: esta corrección dejaría existencias o muestras negativas. Corrige primero la venta o el movimiento relacionado. '+e.message);}","I.balance(d,id);"),
 ("const q=price?I.quote(n,price,p.priceBasis):{priceCents:null,totalCents:null,priceBasis:p.priceBasis||'bottle'};","const oldBottle=s.priceCents==null?'':Number((s.priceCents/100/(s.priceBasis==='box'?6:1)).toFixed(6)).toString();\n    const unchangedLegacy=p.priceBasis==='bottle'&&s.priceBasis==='box'&&price!==''&&Number(price)===Number(oldBottle);\n    const q=unchangedLegacy?I.quote(n,(s.priceCents/100).toFixed(2),'box'):price?I.quote(n,price,p.priceBasis):{priceCents:null,totalCents:null,priceBasis:p.priceBasis||'bottle'};\n    if(unchangedLegacy&&n===s.quantity)q.totalCents=s.totalCents;"),
 ("if(s.quantity>available)fail('Solo hay '+available+' botellas comerciales en esta bodega.');","// Apply an existing sale once; retain discrepancies for review."),
 ("Math.min(n,(r?.sampleQuantity||0)+restored)","Math.max(0,Math.min(n,(r?.sampleQuantity||0)+restored))"),
 ("Math.min(n,(current?.sampleQuantity||0)+restored)","Math.max(0,Math.min(n,(current?.sampleQuantity||0)+restored))")])
edit('corrections-ui.js',[
 ("field('edit-price','Precio',r.priceCents==null?'':(r.priceCents/100).toFixed(2),dec)+select('edit-basis','Precio por',[['bottle','Botella'],['box','Caja de 6']],r.priceBasis||'bottle')","field('edit-price','Precio por botella',r.priceCents==null?'':Number((r.priceCents/100/(r.priceBasis==='box'?6:1)).toFixed(6)).toString(),dec+' placeholder=\"Importe por botella\"')"),
 ("priceBasis:val('edit-basis')","priceBasis:'bottle'"),
 ("Los cobros registrados se conservan; puedes editarlos o eliminarlos en Pagos.","El precio es siempre por botella. Se permite guardar saldos negativos para cuadrarlos después. Los cobros registrados se conservan."),
 ("toast('Venta y existencias actualizadas.');","const warnings=I.balance(data,id).stockWarnings||[];toast(warnings.length?'Venta guardada. Hay saldos negativos por cuadrar.':'Venta y existencias actualizadas.');")])
edit('commerce-ui.js',[
 ("${field('sale-price','Precio de venta acordado *','','number','min=\"0.01\" step=\"0.01\" inputmode=\"decimal\" placeholder=\"Importe\"')}${select('sale-price-basis','Este precio es por',[['box','Caja de 6 botellas'],['bottle','Botella']],'box')}","${field('sale-price','Precio por botella *','','number','min=\"0.01\" step=\"0.01\" inputmode=\"decimal\" placeholder=\"Importe por botella\"')}"),
 ("by('sale-price-basis').value","'bottle'"),
 ("(n<=a?number(a-n):'cantidad insuficiente')","number(a-n)+(n>a?' · Saldo negativo por cuadrar':'')"),
 ("money(s.priceCents,s.currency)+' / '+(s.priceBasis==='box'?'caja de 6':'botella')","money(s.priceCents==null?null:s.priceCents/(s.priceBasis==='box'?6:1),s.currency)+' / botella'"),
 ("money(x.priceCents,x.currency)+' / '+(x.priceBasis==='box'?'caja de 6':'botella')","money(x.priceCents==null?null:x.priceCents/(x.priceBasis==='box'?6:1),x.currency)+' / botella'")])
edit('lot-operations.js',[
 ("return a.join(' + ')||'0 botellas';","return (p.sign<0?'−':'')+(a.join(' + ')||'0 botellas');"),
 ("(n<=available?number(available-n)+' botellas.':'cantidad insuficiente.')","number(available-n)+' botellas.'+(n>available?' Saldo negativo por cuadrar.':'')"),
 ("number(Math.floor(n/6))+' corrugados'+(n%6?' + '+number(n%6)+' botellas sueltas':'')","(n<0?'−':'')+number(Math.floor(Math.abs(n)/6))+' corrugados'+(Math.abs(n)%6?' + '+number(Math.abs(n)%6)+' botellas sueltas':'')")])
p=r/'simple-lot.js';s=p.read_text()
s=s.replace("let active=null,screen='count',preferred='',formId=null,expected=null,printed=null;","let active=null,screen='count',preferred='',formId=null,expected=null,printed=null,historyLocation='';")
s=s.replace("return num(p.fullCases)+' corrugados'","return (p.sign<0?'−':'')+num(p.fullCases)+' corrugados'")
a="function sampleOptions(){return I.balance(data,active).rows.filter(r=>r.quantity>0).map(r=>[JSON.stringify([r.location,r.tag]),r.location+' · '+r.tag+' ('+num(r.quantity)+' bot.; '+num(r.sampleQuantity)+' muestras)']);}"
b="function allBuckets(){const rows=I.balance(data,active).rows.slice();I.locations(data).forEach(location=>{if(!rows.some(r=>r.location===location))rows.push({location,tag:'Por clasificar',quantity:0,sampleQuantity:0,commercialQuantity:0});});return rows;}\n  function sampleOptions(){return allBuckets().map(r=>[JSON.stringify([r.location,r.tag]),r.location+' · '+r.tag+' ('+num(r.quantity)+' bot.; '+num(r.sampleQuantity)+' muestras)']);}"
assert a in s;s=s.replace(a,b)
s=s.replace("return I.balance(data,active).rows.filter(r=>(samples?r.sampleQuantity:r.commercialQuantity)>0).map","return allBuckets().map")
s=s.replace("active=id;screen=tab;","if(active!==id)historyLocation='';active=id;screen=tab;")
s=s.replace("r.location===loc&&r.quantity>0","r.location===loc&&(r.quantity!==0||r.sampleQuantity!==0)")
s=s.replace("if(!history&&n>a)throw Error('Solo hay '+num(a)+' botellas disponibles en el origen.');","const warning=!history&&n>a?' · Saldo negativo por cuadrar; puedes guardar.':'';")
s=s.replace("if(n>available)throw Error('Solo hay '+num(available)+' botellas para esta operación.');","// Known operations remain recordable.")
s=s.replace("+'Total general sin cambio.';","+'Total general sin cambio.'+warning;")
s=s.replace("pretty(b.total-n));","pretty(b.total-n)+warning);")
s=s.replace("const reserved=history?0:Math.max(0,n-I.available(data,active,loc,tag));","const reserved=history?0:Math.min(Math.max(0,n-I.available(data,active,loc,tag)),Math.max(0,I.available(data,active,loc,tag,'sample')));")
s=s.replace("const reserved=Math.max(0,I.quantity(amount,unit)-I.available(d,active,from,tag));","const reserved=Math.min(Math.max(0,I.quantity(amount,unit)-I.available(d,active,from,tag)),Math.max(0,I.available(d,active,from,tag,'sample')));")
s=s.replace("samples:Math.min(expected[1],I.quantity(amount,unit,true))","samples:Math.max(0,Math.min(expected[1],I.quantity(amount,unit,true)))")
s=s.replace("n<sale.quantity?'No hay suficiente producto en esta bodega.':'Saldo total: '+pretty(b.total)+' → '+pretty(b.total-sale.quantity)","'Saldo total: '+pretty(b.total)+' → '+pretty(b.total-sale.quantity)+(n<sale.quantity?' · Saldo negativo por cuadrar; puedes guardar.':'')")
marker="'<div class=\"simple-tabs\"><button id=\"simple-count-tab\">";assert marker in s
s=s.replace(marker,"((b.stockWarnings||[]).length?'<p class=\"stock-warning\" role=\"status\">Saldo por cuadrar: '+b.stockWarnings.map(w=>esc(w.location)+' · '+esc(w.tag)+' · '+pretty(w.quantity)+(w.sampleQuantity<0?' · muestras '+num(w.sampleQuantity):'')).join(' / ')+'. Tus registros sí se guardaron.</p>':'')+\n        "+marker)
helper='''
  const hAttrs=(kind,from,to='')=>' data-history-entry data-history-kind="'+kind+'" data-history-from="'+esc(from||'')+'" data-history-to="'+esc(to||'')+'"';
  function applyHistoryFilter(){
    const root=document.querySelector('.simple-history');if(!root)return;
    historyLocation=$s('history-warehouse').value;const counts={sale:0,move:0,sample:0,count:0};
    root.querySelectorAll('[data-history-entry]').forEach(el=>{const a=el.dataset.historyFrom||'',b=el.dataset.historyTo||'';const show=!historyLocation||(historyLocation==='__unknown__'?!a&&!b:a===historyLocation||b===historyLocation);el.hidden=!show;if(show)counts[el.dataset.historyKind]++;});
    $s('history-counts').textContent=(historyLocation==='__unknown__'?'Sin bodega registrada':historyLocation||'Todas las bodegas')+' · '+counts.sale+' ventas · '+counts.move+' movimientos · '+counts.sample+' muestras · '+counts.count+' ajustes';
    $s('history-empty').hidden=Object.values(counts).some(n=>n>0);
  }
'''
s=s.replace("  function listSales(id)",helper+"  function listSales(id)")
s=s.replace("return '<article class=\"simple-record\"><div><strong>'+pretty(s.quantity)","return '<article class=\"simple-record\"'+hAttrs('sale',s.from)+'><div><strong>'+pretty(s.quantity)")
s=s.replace("<div class=\"card-body\"><h3>Ventas</h3>'+listSales(id)","<div class=\"card-body\"><div class=\"history-filter\">'+sel('history-warehouse','Ver historial por bodega',[['','Todas las bodegas'],...locations(),['__unknown__','Sin bodega registrada']],historyLocation)+'</div><p id=\"history-counts\" class=\"small-note\" aria-live=\"polite\"></p><p id=\"history-empty\" hidden>No hay registros para esta bodega.</p><h3>Ventas</h3>'+listSales(id)")
s=s.replace("map(x=>'<article class=\"simple-record\"><div><strong>'+esc(x.from||'Sin origen')","map(x=>'<article class=\"simple-record\"'+hAttrs('move',x.from,x.to)+'><div><strong>'+esc(x.from||'Sin origen')")
s=s.replace("map(x=>'<article class=\"simple-record\"><div><strong>'+esc(x.location)","map(x=>'<article class=\"simple-record\"'+hAttrs('sample',x.location)+'><div><strong>'+esc(x.location)")
s=s.replace("map(x=>'<p>'+esc(x.location)+' · '+num(x.previousQuantity)","map(x=>'<p'+hAttrs('count',x.location)+'>'+esc(x.location)+' · '+num(x.previousQuantity)")
s=s.replace("window.EBEditUI.bindRecords(id);form(tab);","$s('history-warehouse').onchange=applyHistoryFilter;applyHistoryFilter();window.EBEditUI.bindRecords(id);form(tab);")
s=s.replace("screen==='sale'?'Venta registrada.'","screen==='sale'?((I.balance(data,active).stockWarnings||[]).length?'Venta guardada. Saldo negativo por cuadrar.':'Venta registrada.')")
p.write_text(s)
with (r/'simple-lot.css').open('a') as f:f.write('\n.simple-history [hidden]{display:none!important}.history-filter{max-width:420px;margin-bottom:10px}.history-filter select{min-height:48px;width:100%}.stock-warning{padding:14px 16px;border:1px solid #eacb8e;border-radius:12px;background:#fff4df;color:#755012;font-size:13px;line-height:1.55}@media print{.history-filter{display:none}}\n')
import re
p=r/'control.html';s=p.read_text();s=re.sub(r'(src|href)="(\./(?:inventory-core|commerce-core|commerce-ui|simple-core|simple-lot|corrections-core|corrections-ui|lot-operations)\.(?:js|css))\?[^\"]*"',r'\1="\2?v=history-bottle6"',s);p.write_text(s)
# Tests rejecting oversells are changed to test invalid negative INPUT instead.
# Signed BALANCES are validated separately in the new regression suite.
for p in (r/'tests').glob('*.cjs'):
 s=p.read_text()
 if p.name=='inventory.cjs':
  s=s.replace("amount:681,unit:'bottle'","amount:-681,unit:'bottle'").replace("id:'too-many',amount:421","id:'too-many',amount:-421")
 if p.name=='dispatch.cjs':s=s.replace("id:'X',amount:71},now),/Solo hay 420/","id:'X',amount:-71},now)")
 if p.name=='commerce.cjs':
  s=s.replace("id:'bad',amount:71},now),/420/","id:'bad',amount:-71},now)")
  s=s.replace("assert.throws(()=>I.saveSale(d,'A',{...input,id:'bad',from:'Singapur',tag:'Exportación',amount:1},now),/muestras/);","assert.equal(I.available(I.saveSale(d,'A',{...input,id:'bad',from:'Singapur',tag:'Exportación',amount:1,paidAmount:0},now),'A','Singapur','Exportación'),-6);")
 if p.name=='simple-lot.cjs':s=s.replace("from:'USA',to:'CDMX',tag:'Exportación',amount:3,unit:'pallet',cost:''","from:'USA',to:'CDMX',tag:'Exportación',amount:-3,unit:'pallet',cost:''")
 if p.name=='partner-depots.cjs':s=s.replace("id:'over',from:depots[0],tag:'Nacional',customer:'Test',amount:2","id:'over',from:depots[0],tag:'Nacional',customer:'Test',amount:-2").replace("},now),/Solo hay/);","},now));")
 if p.name=='origin-stock.cjs':s=s.replace("id:'too-many',from:'CDMX',tag:'Por clasificar',amount:1000","id:'too-many',from:'CDMX',tag:'Por clasificar',amount:-1000").replace("},day),/Solo hay/);","},day));")
 if p.name=='always-samples.cjs':
  s=s.replace("assert.throws(()=>I.sellStock(d,'L',{id:'s',from:'Singapur',tag:'Por clasificar',amount:1,unit:'bottle',price:'1000',priceBasis:'bottle',currency:'MXN',payment:'paid',stamp:day},day),/muestras/);","assert.equal(I.available(I.sellStock(d,'L',{id:'s',from:'Singapur',tag:'Por clasificar',amount:1,unit:'bottle',price:'1000',priceBasis:'bottle',currency:'MXN',payment:'paid',stamp:day},day),'L','Singapur','Por clasificar'),-1);")
  s=s.replace("move('over','CDMX','Singapur',715)","move('over','CDMX','Singapur',-715)").replace("id:'overgift',from:'CDMX',tag:'Por clasificar',amount:715","id:'overgift',from:'CDMX',tag:'Por clasificar',amount:-715").replace("/Solo hay/","/cantidad/i")
 s=s.replace('overship protection','signed stock reconciliation').replace('oversell protection','signed stock reconciliation')
 p.write_text(s)
for name in ['browser-simple-lot.py','browser-dispatch.py','browser-inventory.py','browser-commerce.py']:
 p=r/'tests'/name;s=p.read_text()
 if name=='browser-simple-lot.py':s=s.replace("fill('10');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click();assert page.locator('#simple-error').is_visible()","fill('-10');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click();assert page.locator('#simple-error').is_visible()")
 if name=='browser-dispatch.py':s=s.replace("fill('66');page.locator('#save-shipment').click()","fill('-66');page.locator('#save-shipment').click()").replace("assert 'Solo hay 390' in page.locator('#inventory-errors').inner_text()","assert page.locator('#inventory-errors').is_visible()")
 if name=='browser-inventory.py':s=s.replace("fill('421');page.locator('#save-shipment').click()","fill('-421');page.locator('#save-shipment').click()").replace("assert 'Solo hay 420' in page.locator('#inventory-errors').inner_text()","assert page.locator('#inventory-errors').is_visible()")
 if name=='browser-commerce.py':s=s.replace("fill('6600');page.locator('#sale-payment-state')","fill('1100');page.locator('#sale-payment-state')").replace("fill('10000');page.locator('#sale-customer')","fill('-10000');page.locator('#sale-customer')").replace("assert 'Solo hay' in page.locator('#commerce-errors').inner_text()","assert page.locator('#commerce-errors').is_visible()")
 p.write_text(s)
