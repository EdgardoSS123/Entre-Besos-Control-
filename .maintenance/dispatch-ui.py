from pathlib import Path
import hashlib
p=Path('lot-operations.js');s=p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest()=='3fdb7ca09a7d607097849e7abb6d78e8b2080bd1aa591de26a168d72e134464d','Unexpected base source'
def replace_func(name,nextname,text):
 global s
 a=s.index('  function '+name+'('); b=s.index('  function '+nextname+'(',a)
 s=s[:a]+text.rstrip()+'\n'+s[b:]
replace_func('shippingForm','shipmentList',r'''
  function shippingForm(b){return `<section class="card hidden" id="shipment-panel"><div class="card-head"><h2>Registrar envío</h2><span class="chip">Origen → destino</span></div><div class="card-body">
    <label class="checklabel"><input type="checkbox" id="ship-history" ${!b.configured?'checked':''}> Referencia anterior al corte (no mover inventario)</label><p class="small-note" id="ship-help"></p>
    <div class="fields">
      <div class="field"><label for="ship-from">¿De dónde sale?</label><select id="ship-from"><option value="">No recuerdo / seleccionar</option>${choose(I.locations(data),'Oaxaca')}</select></div>
      <div class="field"><label for="ship-kind">Tipo de destino</label><select id="ship-kind">${Object.entries(I.KINDS).map(([v,t])=>'<option value="'+v+'">'+t+'</option>').join('')}</select></div>
      <div class="field"><label for="ship-to">¿A dónde va?</label><select id="ship-to">${choose(I.locations(data).filter(n=>I.locationInfo(data,n).kind==='warehouse'),'CDMX')}</select><button class="textbtn" id="new-destination" type="button">＋ Registrar destino</button></div>
      <div class="field"><label for="ship-purpose">Motivo del envío</label><select id="ship-purpose"><option value="transfer">Traslado de inventario propio</option></select><small id="purpose-help"></small></div>
      ${field('ship-amount','Cantidad','','type="number" inputmode="numeric" min="1" step="1" placeholder="Ej. 10"')}
      <div class="field"><label for="ship-unit">Unidad</label><select id="ship-unit"><option value="box">Cajas de 6</option><option value="bottle">Botellas</option><option value="pallet">Pallets de 80 cajas</option><option value="half">Medios pallets</option></select></div>
      <div class="field"><label for="ship-tag">Etiqueta</label><select id="ship-tag">${choose(I.LABELS,'Por clasificar')}</select></div>
      <div class="field"><label for="ship-status">Estado</label><select id="ship-status"><option value="transit">En tránsito</option><option value="received">Ya recibido en destino</option></select></div>
      ${field('ship-date','Fecha',today(),'type="date" max="'+today()+'"')}${field('ship-reference','Guía / referencia (opcional)','','type="text" maxlength="120"')}
    </div><div id="destination-detail" class="destination-detail"></div>
    <div id="dispatch-preview" class="dispatch-preview" role="status" aria-live="polite"></div><p id="ship-available" class="small-note"></p>
    <label class="checklabel"><input id="ship-cost-known" type="checkbox"> Conozco el costo del envío (marca también si fue $0)</label><div id="ship-cost-fields" class="hidden"><div class="fields">${field('ship-cost','Importe total','','type="number" inputmode="decimal" min="0" step="0.01"')}<div class="field"><label for="ship-currency">Moneda</label><select id="ship-currency">${choose(I.CURRENCIES,'MXN')}</select></div></div><label class="checklabel"><input id="ship-cost-included" type="checkbox"> Este gasto ya está incluido en el costo de producción del lote.</label></div>
    ${field('ship-notes','Notas (opcional)','','type="text" placeholder="Flete, seguro, maniobras…"')}
    <p class="small-note">Los gastos no cambian el costo histórico de producción. Registrar una entrega por venta no emite una factura ni registra un cobro.</p><button id="save-shipment" class="primary">Guardar envío</button></div></section>`;}
  function shipmentQuantity(s){
    if(s.quantity===null)return 'Cantidad no informada';
    const names={bottle:'botellas',box:'cajas',pallet:'pallets',half:'medios pallets'};
    return s.inputUnit&&names[s.inputUnit]?number(s.inputAmount)+' '+names[s.inputUnit]+(s.inputUnit==='bottle'?'':' ('+number(s.quantity)+' botellas)'):number(s.quantity)+' botellas';
  }
''')
replace_func('shipmentList','renderStock',r'''
  function shipmentList(id){return I.shipments(data,id).slice().reverse().map(s=>{
    const dest=s.destination||I.locationInfo(data,s.to),purpose=I.PURPOSES[I.purposeOf(s)];
    return '<article class="shipment"><div><div class="eyebrow">'+(s.historical?'Referencia histórica · sin efecto en inventario':s.status==='transit'?'En tránsito':I.purposeOf(s)==='sale'?'Entregado al comprador':'Recibido')+'</div><h3>'+esc(s.from||'Origen no informado')+' → '+esc(s.to)+'</h3><p>'+shipmentQuantity(s)+' · '+esc(s.tag)+' · '+esc(s.date||'Fecha no informada')+'</p><p><b>'+esc(purpose)+'</b> · '+esc(I.KINDS[dest.kind]||'Bodega')+'</p>'+(dest.address||dest.contact?'<p>'+esc([dest.address,dest.contact].filter(Boolean).join(' · '))+'</p>':'')+'<p>'+(s.cost?.known?currency(s.cost.amount,s.cost.currency)+(s.cost.included?' · Ya incluido en producción':' · Gasto adicional'):'Costo no informado')+'</p><small>'+esc(s.reference||'')+' '+esc(s.notes||'')+'</small></div>'+(s.status==='transit'?'<button class="secondary" data-receive="'+esc(s.id)+'">Confirmar recepción</button>':'')+'</article>';
  }).join('')||'<p class="muted">No hay envíos registrados. No hace falta inventar los anteriores al corte.</p>';}
''')
s=s.replace("['ship-history','ship-from','ship-tag','ship-cost-known','ship-amount','ship-unit']", "['ship-history','ship-from','ship-to','ship-purpose','ship-tag','ship-cost-known','ship-amount','ship-unit','ship-status']")
s=s.replace("      by('save-shipment').onclick=()=>submitShipment(id);", """      by('ship-kind').onchange=()=>{setDestinationKind();shipmentHints(b);};
      by('new-destination').onclick=()=>destinationDialog(b);
      by('ship-amount').oninput=()=>shipmentHints(b);
      by('save-shipment').onclick=()=>submitShipment(id);""")
replace_func('shipmentHints','submitShipment',r'''
  function setDestinationKind(selected){
    const kind=by('ship-kind').value,items=I.locations(data).filter(n=>I.locationInfo(data,n).kind===kind);
    const previous=selected||by('ship-to').value;
    by('ship-to').innerHTML=(items.length?'':'<option value="">Registra un destino</option>')+choose(items,items.includes(previous)?previous:items[0]);
    by('ship-purpose').innerHTML=kind==='warehouse'?'<option value="transfer">Traslado de inventario propio</option>':'<option value="">Selecciona el motivo</option><option value="consignment">Consignación · sigue siendo nuestro</option><option value="sale">Entrega por venta · sale del inventario</option>';
  }
  function destinationDialog(b){
    const dialog=modal('Registrar destino',`<div class="field"><label for="destination-kind">Tipo de destino</label><select id="destination-kind">${Object.entries(I.KINDS).map(([v,t])=>'<option value="'+v+'" '+(v===by('ship-kind').value?'selected':'')+'>'+t+'</option>').join('')}</select></div>
      ${field('destination-name','Nombre y sucursal *','','type="text" maxlength="100" placeholder="Ej. Distribuidor · Bodega Georgia"')}
      ${field('destination-address','Dirección / ciudad (opcional)','','type="text" maxlength="400"')}
      ${field('destination-contact','Contacto / teléfono (opcional)','','type="text" maxlength="160"')}
      <p class="small-note">Este destino queda disponible para los siguientes envíos. Usa un nombre distinto para cada sucursal.</p>`,()=>{
      const name=by('destination-name').value.trim(),kind=by('destination-kind').value;
      write(d=>I.addLocation(d,name,{kind,address:by('destination-address').value,contact:by('destination-contact').value}));
      by('ship-kind').value=kind;setDestinationKind(name);shipmentHints(b);
      const origin=by('ship-from').value;by('ship-from').innerHTML='<option value="">No recuerdo / seleccionar</option>'+choose(I.locations(data),origin);
    });
    dialog.querySelector('#destination-name').focus();
  }
  function shipmentHints(b){
    const historical=by('ship-history').checked,purpose=by('ship-purpose').value,to=by('ship-to').value,from=by('ship-from').value;
    by('ship-status').disabled=historical;
    by('ship-help').textContent=historical?'Referencia: no modifica el inventario actual. Puedes dejar fecha y cantidad sin informar.':'El lote y su etiqueta se conservan durante todo el envío. La recepción se confirma por separado.';
    const meanings={transfer:'Al recibir, aumenta el inventario de la bodega de destino.',consignment:'Al recibir, se muestra como inventario propio en poder del distribuidor o cliente.',sale:'Al confirmar la entrega, deja de formar parte del inventario propio. No crea factura ni cobro.'};
    by('purpose-help').textContent=meanings[purpose]||'Indica si sigue siendo inventario propio o si es una entrega por venta.';
    const available=b.rows.find(r=>r.location===from&&r.tag===by('ship-tag').value)?.quantity||0;
    let n=0;try{if(by('ship-amount').value!=='')n=I.quantity(by('ship-amount').value,by('ship-unit').value);}catch(e){}
    const unitNames={box:'cajas',bottle:'botellas',pallet:'pallets',half:'medios pallets'};
    by('dispatch-preview').textContent=n&&from&&to?
      (historical?'Referencia: ':'Salen ')+by('ship-amount').value+' '+unitNames[by('ship-unit').value]+' = '+number(n)+' botellas · '+from+' → '+to+'.':
      'Selecciona origen, destino y cantidad. 1 caja = 6 botellas.';
    by('ship-available').textContent=historical?'Sin movimiento de existencias.':'Disponible en origen: '+number(available)+' botellas ('+number(available/6)+' cajas equivalentes).'+(n?' Después del envío: '+(n<=available?number(available-n)+' botellas.':'cantidad insuficiente.'):'');
    by('dispatch-preview').classList.toggle('invalid',!historical&&n>available);
    const info=I.locationInfo(data,to);
    by('destination-detail').textContent=[info.address,info.contact].filter(Boolean).join(' · ');
    by('ship-cost-fields').classList.toggle('hidden',!by('ship-cost-known').checked);
  }
''')
s=s.replace("to:by('ship-to').value,tag:","to:by('ship-to').value,purpose:by('ship-purpose').value,tag:")
s=s.replace("function submitShipment(id){try{const input=", "function submitShipment(id){try{if(!by('ship-purpose').value)throw Error('Selecciona el motivo: consignación o entrega por venta.');const input=")
replace_func('receiveDialog','renderWarehouses',r'''
  function receiveDialog(id,sid){
    const shipment=I.shipments(data,id).find(s=>s.id===sid);if(!shipment)return;
    const sale=I.purposeOf(shipment)==='sale';
    modal(sale?'Confirmar entrega al comprador':'Confirmar recepción completa',
      '<p class="muted">'+esc(shipmentQuantity(shipment))+' · '+esc(shipment.from)+' → '+esc(shipment.to)+'. '+(sale?'La cantidad dejará de contarse como inventario propio. No se registra factura ni cobro.':'La cantidad en tránsito se agrega al inventario propio en destino, sin duplicarla.')+'</p>'+field('receipt-date','Fecha de recepción',today(),'type="date" max="'+today()+'"'),()=>{
      write(d=>I.receive(d,id,sid,by('receipt-date').value,today(),stamp()));toast(sale?'Entrega por venta confirmada.':'Recepción confirmada.');renderStock(id);
    });
  }
''')
s=s.replace('Captura solo lo que tienes. No necesitas reconstruir ventas ni envíos pasados.', 'Captura solo inventario que todavía pertenece a Entre Besos, incluso en consignación. No incluyas mercancía ya vendida. No necesitas reconstruir el pasado.')
s=s.replace('En bodegas / en tránsito','Inventario propio / en tránsito')
s=s.replace("+' · Corte '+esc(b.asOf)","+' · Corte '+esc(b.asOf)+' · '+number(b.atThirdParties||0)+' en terceros · '+number(b.deliveredSales||0)+' entregadas por venta'")
s=s.replace("<div class=\"eyebrow\">'+esc(loc)+'</div>","<div class=\"eyebrow\">'+esc(loc)+'</div><small>'+esc(I.KINDS[I.locationInfo(data,loc).kind])+(I.locationInfo(data,loc).kind!=='warehouse'?' · Inventario propio en terceros':'')+'</small>")
s=s.replace("'<div class=\"eyebrow\">CONTROL DE EXISTENCIAS</div><h1>Inventario por bodega</h1>","'<div class=\"eyebrow\">CONTROL DE EXISTENCIAS</div><h1>Inventario por ubicación</h1>")
s=s.replace('Lo que tienes ahora; después, cada traslado.','Salidas por cajas a bodegas, distribuidores y clientes.')
s=s.replace("<h2>Existencias por bodega y etiqueta</h2>","<h2>Inventario propio por ubicación y etiqueta</h2>")
s=s.replace("esc(s.to)+'</td><td>'+(s.quantity===null?'No informada':number(s.quantity))", "esc(s.to)+'<br>'+esc(I.PURPOSES[I.purposeOf(s)])+' · '+esc(I.KINDS[(s.destination||I.locationInfo(data,s.to)).kind])+'</td><td>'+shipmentQuantity(s)")
s=s.replace("<footer>Control interno, datos locales. El corte inicial", "<footer>Las entregas por venta no se suman al inventario propio de destino. La consignación sí conserva propiedad. Este reporte no es una factura ni un reporte de cobranza. Control interno, datos locales. El corte inicial")
s=s.replace("version:'eb-costos-3.3'", "version:'eb-costos-3.4'")
assert hashlib.sha256(s.encode()).hexdigest()=='f1a244343b783ca4d53dd043c49d56b1cc7b66eba9d05f34ee68f0c605ae8734','UI final source hash mismatch'
p.write_text(s)
p=Path('lot-operations.css');s=p.read_text()+'''\n/* Shipment route and recipient details. */\n.dispatch-preview{padding:14px 16px;margin-top:15px;background:#fff2f8;border:1px solid #f5c9e1;border-radius:12px;color:#80244f;font-size:14px;font-weight:650;line-height:1.6;overflow-wrap:anywhere}.dispatch-preview.invalid{background:#fff1ed;border-color:#e7a598;color:#943321}.destination-detail{font-size:12px;color:#657083;overflow-wrap:anywhere;margin-top:8px}.destination-detail:empty{display:none}.shipment h3,.shipment p,.shipment small{overflow-wrap:anywhere}#new-destination{justify-content:flex-start;padding-left:0}#purpose-help{line-height:1.5} .eb-modal .field{margin-top:13px}\n''';p.write_text(s)
p=Path('control.html');s=p.read_text().replace('?v=33','?v=34').replace('v3.3','v3.4');p.write_text(s)
p=Path('tests/browser-inventory.py');s=p.read_text().replace("=='eb-costos-3.3'","=='eb-costos-3.4'");p.write_text(s)
p=Path('Dockerfile');s=p.read_text().replace('COPY tests/inventory.cjs ./tests/inventory.cjs','COPY tests/inventory.cjs tests/dispatch.cjs ./tests/').replace('&& node tests/inventory.cjs','&& node tests/inventory.cjs && node tests/dispatch.cjs');p.write_text(s)
p=Path('.github/workflows/verify-published.yml');s=p.read_text().replace("          PY\n      - name: Install pinned", "          with open('/tmp/eb-browser-dispatch.py','wb') as f:\n              f.write(read(src+'tests/browser-dispatch.py'))\n          PY\n      - name: Install pinned").replace('        run: python3 /tmp/eb-browser-inventory.py','        run: |\n          python3 /tmp/eb-browser-inventory.py\n          python3 /tmp/eb-browser-dispatch.py');p.write_text(s)
