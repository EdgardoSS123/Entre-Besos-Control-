from pathlib import Path
import re

def replace(path,old,new):
    p=Path(path);s=p.read_text()
    if new in s:return
    assert s.count(old)==1,(path,old[:100],s.count(old))
    p.write_text(s.replace(old,new,1))

replace('simple-core.js',"const used=b.samplesUsed||0,produced=Number(l.bottles)||0,unexplained=produced-b.knownTotal-sold-used;", "const orderDelivered=-(d.lotStockAdjustments||[]).filter(a=>a.lotId===id&&a.source==='partner-order'&&active(a)).reduce((n,a)=>n+a.delta,0);\n    const used=b.samplesUsed||0,produced=Number(l.bottles)||0,unexplained=produced-b.knownTotal-sold-used-orderDelivered;")
replace('simple-core.js',"return{...b,produced,sold,used,unexplained,accounted:b.knownTotal+sold+used};", "return{...b,produced,sold,used,orderDelivered,unexplained,accounted:b.knownTotal+sold+used+orderDelivered};")
replace('corrections-core.js',"const owns = (x,id) => x && (x.lotId === id || x.lot === id);", "const owns = (x,id) => x && (x.lotId === id || x.lot === id || (Array.isArray(x.lines)&&x.lines.some(r=>r.lotId===id))); ")
replace('corrections-core.js',"if(item.lot===id)item.lot=newId;", "if(item.lot===id)item.lot=newId;if(k==='partnerOrders')for(const line of item.lines||[])if(line.lotId===id)line.lotId=newId;")
replace('corrections-core.js',"function removeLot(d,id,expected,meta){checkToken(getLot(d,id),expected);", "function removeLot(d,id,expected,meta){if((d.partnerOrders||[]).some(r=>!['cancelled','deleted'].includes(r.status)&&r.lines.some(l=>l.lotId===id)))fail('Este lote tiene pedidos vinculados. Cancela esos pedidos antes de eliminarlo.');checkToken(getLot(d,id),expected);")
replace('corrections-core.js',"const old=getLot(d,id);checkToken(old,expected);const newId=String(record.id||'').trim();", "const old=getLot(d,id);checkToken(old,expected);if(old.p!==record.p&&(d.partnerOrders||[]).some(r=>!['cancelled','deleted'].includes(r.status)&&r.lines.some(l=>l.lotId===id)))fail('Corrige primero los pedidos vinculados antes de cambiar la variedad del lote.');const newId=String(record.id||'').trim();")
replace('corrections-core.js',"if(!r)fail('Registro no encontrado.');return{k,r};", "if(!r)fail('Registro no encontrado.');if(kind==='count'&&r.source==='partner-order')fail('Modifica o cancela esta entrega desde Pedidos; así se conserva el descuento correcto.');return{k,r};")
replace('simple-lot.js',"+(b.transit?'<br>En tránsito:'", "+(b.orderDelivered?'<br>Entregadas por pedido: '+pretty(b.orderDelivered):'')+(b.transit?'<br>En tránsito:'") if "+(b.transit?'<br>En tránsito:'" in Path('simple-lot.js').read_text() else None
p=Path('simple-lot.js');s=p.read_text()
if 'Entregadas por pedido:' not in s:
    old="+(b.transit?'<br>En tránsito: '"
    assert s.count(old)==1
    s=s.replace(old,"+(b.orderDelivered?'<br>Entregadas por pedido: '+pretty(b.orderDelivered):'')"+old,1)
if "(b.orderDelivered?' + pedidos entregados':'')" not in s:
    s=s.replace("'Producidas = saldo + ventas + muestras entregadas'+", "'Producidas = saldo + ventas + muestras entregadas'+(b.orderDelivered?' + pedidos entregados':'')+",1)
p.write_text(s)
# Explain the new stock exits without adding buyers, revenue or collection details to partner reports.
p=Path('executive-core.js');s=p.read_text()
if "section('Salidas por pedidos'" not in s:
    marker=" model.sections.push(section('Diferencias que requieren revisión'"
    assert s.count(marker)==1
    extra=" const orderExits=balances.filter(({b})=>b.orderDelivered);if(orderExits.length)model.sections.push(section('Salidas por pedidos',['Lote','Botellas entregadas','Equivalencia'],orderExits.map(({l,b})=>[l.id,num(b.orderDelivered),P.describe(b.orderDelivered,true)]),[1],{note:'Estas entregas ya están descontadas del saldo. Se muestran aparte de ventas y muestras; no generan ingresos ni cobros automáticamente.'}));\n"
    s=s.replace(marker,extra+marker,1);p.write_text(s)
p=Path('reports-data.js');s=p.read_text()
if "section('Salidas por pedidos'" not in s:
    marker="    model.notes.push('1 caja (corrugado)"
    assert s.count(marker)==1
    extra="    const orderExits=balances.filter(({b})=>b.orderDelivered);if(orderExits.length)model.sections.push(section('Salidas por pedidos',['Lote','Botellas entregadas'],orderExits.map(({l,b})=>[l.id,number(b.orderDelivered)]),[1],{note:'Salidas descontadas de existencias. No generan ventas con precio ni cobros automáticamente.'}));\n"
    s=s.replace(marker,extra+marker,1);p.write_text(s)
# Generate a workspace using the already authenticated application shell.
s=Path('office.html').read_text()
s=re.sub(r'<title>.*?</title>','<title>Entre Besos · Pedidos</title>',s,count=1)
s=s.replace('id="office-app"','id="orders-app"')
s=re.sub(r'<script[^>]+src="/contacts-import.js[^>]+></script>','',s)
s=re.sub(r'<script[^>]+src="/vendor/fflate.js[^>]+></script>','',s)
s=re.sub(r'<script[^>]+src="/office-ui.js[^>]+></script>','<script type="application/x-eb-shared" src="/orders-core.js?v=orders1"></script><script type="application/x-eb-shared" src="/orders-ui.js?v=orders1"></script>',s)
s=s.replace('</head>','<link rel="stylesheet" href="/orders.css?v=orders1"></head>',1)
s=s.replace('Resumen y contactos compartidos entre PC y celular.','Pedidos e inventarios compartidos entre PC y celular.')
Path('orders.html').write_text(s)
# Current navigation is shared by lots, inventories, contacts and documents.
p=Path('office-nav.js');s=p.read_text()
if "section==='orders'" not in s:
    s=s.replace("location.href=section==='documents'?", "location.href=section==='orders'?'/orders.html':section==='documents'?",1)
    s=s.replace("add(side,'documents','Documentos','▱');", "add(side,'documents','Documentos','▱');add(side,'orders','Pedidos','▣');",1)
    s=s.replace("add(mobile,'documents','Docs','▱');", "add(mobile,'documents','Docs','▱');add(mobile,'orders','Pedidos','▣');",1)
    s=s.replace("(location.pathname==='/documents.html'&&b.dataset.office==='documents')", "(location.pathname==='/documents.html'&&b.dataset.office==='documents')||(location.pathname==='/orders.html'&&b.dataset.office==='orders')",1)
    s=s.replace("if(current==='warehouses'", "if(mobile&&mobile.children.length>6){mobile.style.setProperty('display','flex','important');mobile.style.overflowX='auto';for(const b of mobile.children){b.style.flex='0 0 72px';b.style.minWidth='72px';}const active=mobile.querySelector('.active');if(active)mobile.scrollLeft=Math.max(0,active.offsetLeft-mobile.clientWidth/2);}\nif(current==='warehouses'",1)
    p.write_text(s)
p=Path('index.html');s=p.read_text()
if "if(s==='Pedidos')" not in s:
    s=s.replace('function go(s){',"function go(s){if(s==='Pedidos'){location.href='/orders.html';return;}",1);p.write_text(s)
# Force browsers to revalidate changed modules without modifying local/shared records.
for name in ['control.html','materials.html','office.html','documents.html','orders.html','index.html']:
    p=Path(name)
    if not p.exists():continue
    s=p.read_text()
    for asset in ['simple-core.js','simple-lot.js','corrections-core.js','executive-core.js','reports-data.js','office-nav.js']:
        s=re.sub(re.escape(asset)+r'\?v=[^"\s]+',asset+'?v=orders1',s)
    p.write_text(s)
p=Path('Dockerfile');s=p.read_text()
if 'COPY orders-core.js orders-ui.js ./' not in s:
    marker='FROM nginx:alpine AS static'
    s=s.replace(marker,'COPY orders-core.js orders-ui.js ./\nCOPY tests/orders.cjs ./tests/\nRUN node --check orders-core.js && node --check orders-ui.js && node tests/orders.cjs\n\n'+marker,1)
    s=s.replace('COPY nginx.conf','COPY orders.html orders-core.js orders-ui.js orders.css /usr/share/nginx/html/\nCOPY nginx.conf',1)
    s=s.replace('for asset in ','for asset in orders.html orders-core.js orders-ui.js orders.css ',1);p.write_text(s)
print('Orders integrated: pending does not move stock; delivery posts reversible exits in the existing ledger; no user records changed.')
