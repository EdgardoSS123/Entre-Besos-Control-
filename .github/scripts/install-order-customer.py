from pathlib import Path

def replace(path, old, new):
    p = Path(path); source = p.read_text()
    if new in source:
        return
    assert source.count(old) == 1, (path, old[:100], source.count(old))
    p.write_text(source.replace(old, new, 1))

replace('orders-core.js',
    " const notes=text(input.notes);if(notes.length>1000)fail('Las notas admiten hasta 1,000 caracteres.');",
    " const customer=text(input.customer);if(customer.length>240)fail('El nombre del cliente admite hasta 240 caracteres.');\n const notes=text(input.notes);if(notes.length>1000)fail('Las notas admiten hasta 1,000 caracteres.');")
replace('orders-core.js',
    'return{partner,from,date:date(input.date),status,lines,quantity:totals(lines),notes};',
    'return{partner,customer,from,date:date(input.date),status,lines,quantity:totals(lines),notes};')
replace('orders-core.js',
    'function signature(r){return JSON.stringify([r.partner,r.from,r.date,r.status,r.lines,r.notes]);}',
    "function signature(r){return JSON.stringify([r.partner,text(r.customer),r.from,r.date,r.status,r.lines,r.notes]);}\nfunction stockSignature(r){return JSON.stringify([r.from,r.status,r.lines.map(l=>[l.lotId,l.quantity])]);}")
replace('orders-core.js',
    ' if(before&&signature(before)===signature(normalized))',
    " if(action==='save'&&!normalized.customer&&(!before||text(before.customer)))fail('Indica para quién es el pedido.');\n if(before&&signature(before)===signature(normalized))")
replace('orders-core.js',
    " reverse(next,opts.id,stamp);\n if(after.status==='delivered')debit(next,after,I,{operation,stamp,day,actor:opts.actor});",
    " // A recipient-only edit must preserve the original stock exits byte for byte.\n if(!before||stockSignature(before)!==stockSignature(after)){\n  reverse(next,opts.id,stamp);\n  if(after.status==='delivered')debit(next,after,I,{operation,stamp,day,actor:opts.actor});\n }")
replace('orders-ui.js',
    "+'</h2><p>Sale de <b>'+esc(r.from)",
    "+'</h2><p class=\"order-recipient\">Para: <b>'+esc(r.customer||'Destinatario por capturar')+'</b></p><p>Sale de <b>'+esc(r.from)")
replace('orders-ui.js',
    'function captureLines(){',
    "function customerOptions(data){\n const names=(data.contacts||[]).map(c=>window.EBContacts?.view(c)).filter(Boolean).map(c=>c.name+(c.place&&c.place!==c.name?' · '+c.place:''));\n return [...new Set(names.filter(v=>v&&v.length<=240))].sort((a,b)=>a.localeCompare(b,'es')).map(v=>'<option value=\"'+esc(v)+'\"></option>').join('');\n}\nfunction captureLines(){")
replace('orders-ui.js',
    '<div class="fields"><label>Fecha de entrega solicitada',
    '<div class="fields"><label class="wide" for="order-customer">Cliente / para quién es el pedido *<input id="order-customer" type="text" maxlength="240" required list="order-customers" placeholder="Nombre de la persona o empresa" value="\'+esc(order?.customer||\'\')+\'" autocomplete="off"><datalist id="order-customers">\'+customerOptions(data)+\'</datalist></label><label>Fecha de entrega solicitada')
replace('orders-ui.js',
    "return{partner:selected,from:$('order-from').value",
    "return{partner:selected,customer:$('order-customer').value,from:$('order-from').value")
replace('orders.html', '/orders-core.js?v=orders1', '/orders-core.js?v=order-customer1')
replace('orders.html', '/orders-ui.js?v=orders1', '/orders-ui.js?v=order-customer1')
replace('orders.html', '/orders.css?v=orders1', '/orders.css?v=order-customer1')
p=Path('orders.css'); s=p.read_text()
if '.order-record-head .order-recipient' not in s:
    p.write_text(s+'\n.order-record-head>div{min-width:0}.order-record-head .order-recipient{font-size:14px;color:#101827;margin:0 0 8px;overflow-wrap:anywhere}#order-customer{width:100%}\n')
replace('tests/orders.cjs',
    "input={partner:'edgardo',from:",
    "input={partner:'edgardo',customer:'Cliente de prueba',from:")
replace('tests/browser-orders.py',
    "a.locator('#order-new').click();a.locator('[data-amount]').fill('2');",
    "a.locator('#order-new').click();a.locator('#order-customer').fill('Cliente de prueba PC');a.locator('[data-amount]').fill('2');")
replace('tests/browser-orders.py',
    "z.locator('#order-new').click();z.locator('#order-from').select_option('Oaxaca');",
    "z.locator('#order-new').click();z.locator('#order-customer').fill('Cliente de Ricardo');z.locator('#order-from').select_option('Oaxaca');")
replace('tests/browser-orders.py',
    "z.locator('#order-new').click();z.locator('[data-amount]').fill('1');",
    "z.locator('#order-new').click();z.locator('#order-customer').fill('Cliente de Mario');z.locator('[data-amount]').fill('1');")
print('Recipient field integrated. No stored orders, contacts, inventory or sales modified.')
