'use strict';
(function(){
  const I=window.EBLedger,$s=id=>document.getElementById(id),num=n=>number(n),idNew=()=>crypto.randomUUID(),stamp=()=>new Date().toISOString();
  let active=null,screen='count',preferred='',formId=null,expected=null,printed=null;
  const opts=(arr,v)=>arr.map(([key,text])=>'<option value="'+esc(key)+'" '+(key===v?'selected':'')+'>'+esc(text)+'</option>').join('');
  const sel=(id,label,arr,v)=>'<div class="field"><label for="'+id+'">'+label+'</label><select id="'+id+'">'+opts(arr,v)+'</select></div>';
  const inp=(id,label,v='',extra='')=>'<div class="field"><label for="'+id+'">'+label+'</label><input id="'+id+'" value="'+esc(v)+'" '+extra+'></div>';
  const decimal='type="text" inputmode="decimal" autocomplete="off" placeholder="Cantidad" maxlength="24"';
  const units=[['bottle','Botellas'],['box','Cajas (6)'],['pallet','Pallets (480)']];
  const locations=()=>I.locations(data).map(x=>[x,x==='CDMX'?'México · CDMX':x]);
  const cases=n=>{const p=I.packCounts(n);return num(p.fullCases)+' corrugados'+(p.looseBottles?' + '+num(p.looseBottles)+' bot. sueltas':'');};
  const pretty=n=>num(n)+' botellas · '+cases(n);
  const metric=(label,n,id)=>'<div><small>'+label+'</small><strong'+(id?' id="'+id+'"':'')+'>'+num(n)+'</strong><span class="metric-unit">botellas</span><span class="metric-cases">'+cases(n)+'</span></div>';
  function sampleOptions(){return I.balance(data,active).rows.filter(r=>r.quantity>0).map(r=>[JSON.stringify([r.location,r.tag]),r.location+' · '+r.tag+' ('+num(r.quantity)+' bot.; '+num(r.sampleQuantity)+' muestras)']);}
  const fmt=(v,c)=>v===null||v===undefined?'Por confirmar':new Intl.NumberFormat('es-MX',{style:'currency',currency:c}).format(v/100)+' '+c;
  function fail(e){const box=$s('simple-error');if(box){box.textContent=e.message||String(e);box.hidden=false;}else toast(e.message);}
  function write(action){
    if(storageError)throw Error(storageError);
    const raw=localStorage.getItem(KEY),latest=freshData(),next=action(latest);
    if(localStorage.getItem(KEY)!==raw)throw Error('Otra pestaña cambió la información. Vuelve a abrir el lote.');
    if(raw&&!localStorage.getItem('eb-before-simple-v1'))localStorage.setItem('eb-before-simple-v1',raw);
    localStorage.setItem(KEY,JSON.stringify(next));data=next;
  }
  function stockOptions(samples=false){return I.balance(data,active).rows.filter(r=>(samples?r.sampleQuantity:r.commercialQuantity)>0).map(r=>[JSON.stringify([r.location,r.tag]),r.location+' · '+r.tag+' ('+num(samples?r.sampleQuantity:r.commercialQuantity)+' bot.)']);}
  function selectedBucket(id){try{return JSON.parse($s(id).value);}catch(e){return['','Por clasificar'];}}
  function selectedSource(arr){return arr.find(([v])=>JSON.parse(v)[0]===preferred)?.[0]||arr[0]?.[0]||'';}
  function bind(id,fn){if($s(id))$s(id).onclick=fn;}
  function safeData(){data=freshData();return data;}
  function listSales(id){return I.sales(data,id).slice().reverse().map(s=>{const st=I.saleStatus(s,today());return '<article class="simple-record"><div><strong>'+pretty(s.quantity)+'</strong><span>'+esc(s.customer||'Cliente no identificado')+'</span><small>'+esc(s.from||'Origen no recordado')+' · '+esc(s.date||'Fecha no recordada')+(s.mode==='historical'?' · No descontada: anterior al conteo':' · Descontada de bodega')+'</small></div><div><b>'+fmt(s.totalCents,s.currency)+'</b><small>'+esc(st.status)+'</small>'+(st.pendingCents>0?'<button class="textbtn" data-simple-payment="'+esc(s.id)+'">Registrar pago</button>':'')+(s.mode==='historical'&&!s.stockEffect&&!s.shipmentId?'<button class="secondary" data-apply-sale="'+esc(s.id)+'">Descontar de bodega</button>':'')+window.EBEditUI.buttons('sale',s.id)+'</div>'+window.EBEditUI.payments(s)+'</article>';}).join('')||'<p class="muted">No has registrado ventas de este lote.</p>';}
  function open(id,tab='count',from){
    try{
      safeData();const l=data.lots.find(l=>l.id===id);if(!l)throw Error('Guarda primero los costos del lote.');
      active=id;screen=tab;preferred=from||preferred;const b=I.reconciliation(data,id),p=PRODUCTS[l.p]||PRODUCTS[0];view='stock';
      const rows=I.locations(data).map(loc=>{const a=b.rows.filter(r=>r.location===loc&&r.quantity>0),n=a.reduce((n,r)=>n+r.quantity,0),samples=a.reduce((n,r)=>n+r.sampleQuantity,0);return a.length?'<article class="simple-location-wrap"><button class="simple-location" data-place="'+esc(loc)+'"><span>'+esc(loc)+'</span><b>'+num(n)+' <small>bot.</small></b><small>'+cases(n)+' · '+num(n/480)+' pallets'+(samples?' · '+num(samples)+' muestras':'')+'</small></button>'+a.map(r=>{const key=esc(JSON.stringify([r.location,r.tag]));return '<div class="stock-record-actions"><span>'+esc(r.tag)+' · '+num(r.quantity)+' bot.</span><div class="record-buttons"><button class="textbtn" data-stock-edit="'+key+'">Editar</button><button class="textbtn danger-text" data-stock-delete="'+key+'">Eliminar</button></div></div>';}).join('')+'</article>':'';}).join('');
      $s('app').innerHTML='<div class="heading"><div><div class="eyebrow">CONTROL DEL LOTE</div><h1>'+esc(id)+'</h1><p class="muted">'+esc(p.name)+' · '+esc(l.ml)+' ml'+(l.originWarehouse?' · Origen: '+esc(l.originWarehouse):'')+' · Costo por botella '+(Number.isFinite(l.unitCost)?cash(l.unitCost):'pendiente')+'</p></div><div class="simple-header-actions"><button class="secondary" id="simple-costs">Editar lote</button><button class="secondary danger-text" id="simple-delete-lot">Eliminar lote</button><button class="secondary" id="simple-back">Mis lotes</button></div></div>'+
        '<section class="card simple-overview"><div class="simple-metrics">'+metric('Producidas',b.produced,'simple-produced')+metric('Vendidas',b.sold,'simple-sold')+metric('Muestras entregadas',b.used,'simple-samples-used')+metric('Saldo en bodegas',b.total,'simple-current')+'</div><p class="case-rule">Corrugado = caja de 6 botellas. Las sueltas se muestran aparte; no es inventario de cartón vacío.</p><p class="simple-account-note">Disponible para vender: '+pretty(b.commercialTotal)+'<br>Muestras aún en bodega: '+pretty(b.sampleTotal)+(b.transit?'<br>En tránsito: '+pretty(b.transit):'')+'</p><div class="reconciliation-line '+(b.unexplained?'difference':'balanced')+'"><b>'+(b.unexplained<0?'Registradas de más':'Por aclarar')+': <span id="simple-difference">'+num(Math.abs(b.unexplained))+'</span> botellas</b><span>'+cases(Math.abs(b.unexplained))+'</span><small>'+(b.unexplained>0?'Faltan por ubicar o explicar. No se inventan ventas ni pérdidas.':b.unexplained<0?'Revisa existencias y ventas antiguas sin descuento.':'Producidas = saldo + ventas + muestras entregadas'+(b.transit?' + en tránsito':'')+'.')+'</small>'+(b.unexplained<0&&I.sales(data,id).some(x=>x.mode==='historical')?'<button class="textbtn" id="review-undiscounted">Revisar ventas sin descuento</button>':'')+'</div></section>'+
        '<div class="simple-tabs"><button id="simple-count-tab">Existencias</button><button id="simple-sale-tab">Venta</button><button id="simple-sample-tab">Muestras</button><button id="simple-move-tab">Mover bodega</button></div><div id="simple-error" class="alert" hidden role="alert"></div><section class="card" id="simple-form"></section>'+
        '<div class="section-toolbar"><h2>Lo que tienes por ubicación</h2><button class="textbtn" id="simple-print">Imprimir</button></div><div class="simple-location-grid">'+(rows||'<p class="muted">Indica dónde tienes botellas. No hace falta reconstruir envíos anteriores.</p>')+'</div>'+
        '<details class="card simple-history"><summary>Ventas y movimientos registrados</summary><div class="card-body"><h3>Ventas</h3>'+listSales(id)+'<h3>Movimientos</h3>'+I.shipments(data,id).filter(x=>x.status!=='cancelled').slice().reverse().map(x=>'<article class="simple-record"><div><strong>'+esc(x.from||'Sin origen')+' → '+esc(x.to)+'</strong><small>'+pretty(x.quantity||0)+(x.purpose==='sample'||x.stockType==='sample'?' · Muestras · ingreso $0':'')+' · '+esc(x.status==='transit'?'En tránsito':'Registrado')+'</small></div>'+window.EBEditUI.buttons('move',x.id)+'</article>').join('')+'<h3>Muestras</h3>'+I.sampleActions(data,id).slice().reverse().map(x=>'<article class="simple-record"><div><strong>'+esc(x.location)+' · '+pretty(x.quantity)+'</strong><small>'+esc({reserve:'Marcadas como muestra',release:'Regresadas a comercial',consume:'Entregadas / consumidas'}[x.type])+'</small></div>'+window.EBEditUI.buttons('sample',x.id)+'</article>').join('')+'<details><summary>Correcciones de existencias</summary>'+(data.lotStockAdjustments||[]).filter(x=>x.lotId===id).slice().reverse().map(x=>'<p>'+esc(x.location)+' · '+num(x.previousQuantity)+' → '+num(x.quantity)+' bot. · '+esc(x.date)+'</p>').join('')+'</details><button class="textbtn" id="simple-samples">Muestras y pagos detallados</button></div></details>'+
        '<p class="small-note">Datos en este navegador. Usa Respaldo al terminar.</p>';
      bind('simple-costs',()=>loadLot(id,false));bind('simple-delete-lot',()=>window.EBEditUI.deleteLot(id));bind('simple-back',()=>show('lots'));bind('simple-count-tab',()=>form('count'));bind('simple-sale-tab',()=>form('sale'));bind('simple-sample-tab',()=>form('sample'));bind('simple-move-tab',()=>form('move'));
      bind('simple-samples',()=>window.EBCommerceUI.render(id,{samples:true}));
      document.querySelectorAll('[data-place]').forEach(btn=>btn.onclick=()=>{preferred=btn.dataset.place;form('count');$s('simple-form').scrollIntoView({block:'start',behavior:'smooth'});});
      bind('simple-print',()=>{const html=$s('app').cloneNode(true);html.querySelectorAll('button,#simple-form,.simple-tabs,#simple-error').forEach(x=>x.remove());html.querySelectorAll('details').forEach(x=>x.open=true);$s('print-view').innerHTML='<h1>Entre Besos · Resumen del lote</h1>'+html.innerHTML;window.print();});
      document.querySelectorAll('[data-simple-payment]').forEach(btn=>btn.onclick=()=>paymentDialog(id,btn.dataset.simplePayment));
      document.querySelectorAll('[data-apply-sale]').forEach(btn=>btn.onclick=()=>applySaleDialog(id,btn.dataset.applySale));
      bind('review-undiscounted',()=>{const h=document.querySelector('.simple-history');h.open=true;h.scrollIntoView({block:'start',behavior:'smooth'});});
      window.EBEditUI.bindRecords(id);form(tab);setNav();$s('nav-lots')?.classList.add('active');$s('mobile-save')?.classList.add('hidden');window.scrollTo(0,0);
    }catch(e){fail(e);}
  }
  function form(tab){
    screen=tab;formId=idNew();$s('simple-error').hidden=true;
    ['count','sale','sample','move'].forEach(x=>$s('simple-'+x+'-tab').classList.toggle('active',x===tab));
    const s=tab==='sale'?sampleOptions():stockOptions(),picked=selectedSource(s),location=preferred||I.balance(data,active).rows[0]?.location||'Oaxaca';
    let html='';
    if(tab==='count')html='<div class="card-head"><h2>¿Cuánto tienes ahora?</h2></div><div class="card-body"><div class="simple-fields">'+sel('simple-location','Ubicación',locations(),location)+inp('simple-amount','Cantidad actual','',decimal)+sel('simple-unit','Unidad',units,'bottle')+'</div><p id="simple-count-before" class="small-note"></p><details class="simple-details"><summary>Más detalles (opcional)</summary><div class="fields">'+sel('simple-tag','Etiqueta',I.LABELS.map(x=>[x,x]),'Por clasificar')+'</div></details><p class="small-note">Reemplaza la cantidad de esta ubicación y etiqueta; no la suma otra vez.</p><div id="simple-preview" class="simple-preview"></div><button class="primary" id="simple-save">Guardar existencias</button></div>';
    if(tab==='sale')html='<div class="card-head"><h2>Registrar venta</h2></div><div class="card-body"><p id="simple-sale-help" class="small-note">Descuenta de la ubicación y actualiza el total disponible.</p><div class="simple-fields">'+sel('simple-source','Sale de',s.length?s:[['','Primero registra existencias']],picked)+inp('simple-amount','Cantidad vendida','',decimal)+sel('simple-unit','Unidad',units,'box')+'</div><div class="fields simple-price">'+inp('simple-price','Precio de venta','', 'type="text" inputmode="decimal" placeholder="Importe"')+sel('simple-price-basis','Precio por',[['box','Caja de 6'],['bottle','Botella']],'box')+'</div><details class="simple-details" id="simple-sale-details"><summary>Cliente, pago o venta antigua (opcional)</summary><label class="checklabel history-check"><input id="simple-history" type="checkbox"> Ya estaba descontada de mi conteo · NO descontar otra vez</label><div class="fields">'+inp('simple-customer','Cliente','','type="text" maxlength="160" placeholder="Puedes dejarlo pendiente"')+sel('simple-payment','Pago',[['pending','Pendiente'],['paid','Pagada']],'pending')+sel('simple-currency','Moneda',I.CURRENCIES.map(x=>[x,x]),'MXN')+inp('simple-date','Fecha anterior (si la recuerdas)','','type="date" max="'+today()+'"')+'</div></details><div id="simple-preview" class="simple-preview"></div><button class="primary" id="simple-save">Guardar venta</button></div>';
    if(tab==='sample'){const a=sampleOptions();html='<div class="card-head"><h2>Muestras</h2><span class="chip">Ingreso $0</span></div><div class="card-body"><p class="small-note">Las entregas descuentan botellas. Reservar o liberar cambia únicamente su clasificación en bodega.</p>'+sel('simple-sample-action','Operación',[['consume','Entregar sin cobro'],['reserve','Reservar en bodega'],['release','Liberar para venta o traslado']],'consume')+'<div class="simple-fields">'+sel('simple-source','Sale de',a.length?a:[['','Primero registra existencias']],selectedSource(a))+inp('simple-amount','Cantidad','',decimal)+sel('simple-unit','Unidad',units,'bottle')+'</div><details class="simple-details"><summary>Destinatario o notas (opcional)</summary>'+inp('simple-sample-notes','Destinatario / motivo','','type="text" maxlength="2000"')+'</details><div id="simple-preview" class="simple-preview"></div><button class="primary" id="simple-save">Guardar operación de muestras</button></div>';}
    if(tab==='move')html='<div class="card-head"><h2>Movimiento de bodega</h2></div><div class="card-body"><div class="fields">'+sel('simple-source','De',s.length?s:[['','Primero registra existencias']],picked)+sel('simple-destination','A',locations(),location==='CDMX'?'EB1-1 · Edgardo':'CDMX')+'</div><div class="fields">'+inp('simple-amount','Cantidad','',decimal)+sel('simple-unit','Unidad',units,'box')+'</div><p class="small-note">Al guardar, se resta del origen y se suma al destino. Es un movimiento realizado, no una venta.</p><details class="simple-details"><summary>Flete y moneda (opcional)</summary><div class="fields">'+inp('simple-freight','Costo de flete','', 'type="text" inputmode="decimal" placeholder="Si lo conoces"')+sel('simple-currency','Moneda',I.CURRENCIES.map(x=>[x,x]),'MXN')+'</div></details><div id="simple-preview" class="simple-preview"></div><button class="primary" id="simple-save">Guardar movimiento</button></div>';
    $s('simple-form').innerHTML=html;
    if(tab==='count'){$s('simple-location').onchange=loadCount;$s('simple-tag').onchange=loadCountBucket;loadCount();}
    if(tab==='sale'){$s('simple-history').onchange=()=>{
      const history=$s('simple-history').checked;
      $s('simple-source').innerHTML=history?opts([['','No recuerdo / no hace falta'],...locations().map(([x,t])=>[JSON.stringify([x,'Por clasificar']),t])],''):opts(s,picked);
      $s('simple-payment').innerHTML=opts(history?[['unknown','No recuerdo'],['pending','Pendiente'],['paid','Pagada']]:[['pending','Pendiente'],['paid','Pagada']],history?'unknown':'pending');
      $s('simple-sale-help').textContent=history?'Solo úsalo si esa venta YA está excluida de tus existencias. No descuenta otra vez. Cliente, precio y fecha pueden quedar pendientes.':'Descuenta de la ubicación y actualiza el total disponible.';preview();
    };}
    $s('simple-form').addEventListener('input',preview);$s('simple-form').addEventListener('change',preview);bind('simple-save',save);preview();
  }
  function loadCount(){
    const loc=$s('simple-location').value,rows=I.balance(data,active).rows.filter(r=>r.location===loc);
    $s('simple-tag').value=rows[0]?.tag||'Por clasificar';loadCountBucket();
  }
  function loadCountBucket(){
    const r=I.balance(data,active).rows.find(r=>r.location===$s('simple-location').value&&r.tag===$s('simple-tag').value);
    expected=[r?.quantity||0,r?.sampleQuantity||0];$s('simple-amount').value=r?String(r.quantity):'';$s('simple-unit').value='bottle';
    $s('simple-count-before').textContent='Registrado: '+num(expected[0])+' botellas · '+$s('simple-tag').value+'. Puedes escribir 2.5 pallets.';preview();
  }
  function preview(){
    const box=$s('simple-preview');if(!box)return;try{
      const n=I.quantity($s('simple-amount').value,$s('simple-unit').value,screen==='count'),b=I.balance(data,active);
      if(screen==='count'){box.textContent=pretty(n)+' · Total del lote después: '+num(b.total-expected[0]+n)+' botellas.';return;}
      const [loc,tag]=selectedBucket('simple-source'),isGift=screen==='sample',history=screen==='sale'&&!isGift&&$s('simple-history').checked;
      const a=history?null:(isGift||screen==='sale')?b.rows.find(r=>r.location===loc&&r.tag===tag)?.quantity||0:I.available(data,active,loc,tag);
      if(!history&&n>a)throw Error('Solo hay '+num(a)+' botellas disponibles en el origen.');
      if(isGift&&$s('simple-sample-action').value!=='consume'){
        const reserve=$s('simple-sample-action').value==='reserve',available=I.available(data,active,loc,tag,reserve?'commercial':'sample');
        if(n>available)throw Error('Solo hay '+num(available)+' botellas para esta operación.');
        box.textContent=pretty(n)+(reserve?' para reservar.':' para liberar.');return;
      }
      if(isGift){box.textContent=pretty(n)+' entregadas · Ingreso $0 · Saldo total: '+pretty(b.total-n);return;}
      if(screen==='sale'){
        const p=$s('simple-price').value.trim().replace(',','.');const total=p?fmt(I.quote(n,p,$s('simple-price-basis').value).totalCents,$s('simple-currency').value):'Precio pendiente';
        const reserved=history?0:Math.max(0,n-I.available(data,active,loc,tag));
        box.textContent=pretty(n)+' · '+total+(reserved?' · Se usarán '+num(reserved)+' botellas reservadas como muestra para esta venta.':'')+(history?' · No cambia las existencias.':' · Saldo en origen: '+pretty(a-n)+' · Saldo total: '+pretty(b.total-n));
      }else box.textContent=pretty(n)+' · '+loc+': '+num(a)+' → '+num(a-n)+' · '+'Total general sin cambio.';
    }catch(e){box.textContent=$s('simple-amount')?.value?e.message:'Escribe la cantidad. Acepta 2.5 pallets o 0.5 pallet.';}
  }
  function save(){
    try{
      const amount=$s('simple-amount').value,unit=$s('simple-unit').value,input={id:formId,amount,unit,stamp:stamp()};
      if(screen==='count'){
        preferred=$s('simple-location').value;
        Object.assign(input,{location:preferred,tag:$s('simple-tag').value,samples:Math.min(expected[1],I.quantity(amount,unit,true)),expected});write(d=>I.countStock(d,active,input,today()));
      }else{
        const [from,tag]=selectedBucket('simple-source');Object.assign(input,{from,tag});preferred=from||preferred;
        if(screen==='sale'){
          Object.assign(input,{customer:$s('simple-customer').value,price:$s('simple-price').value.trim().replace(',','.'),priceBasis:$s('simple-price-basis').value,currency:$s('simple-currency').value,payment:$s('simple-payment').value,date:$s('simple-date').value});
          write(d=>{
            const date=today();
            if($s('simple-history').checked)return I.knownSale(d,active,input,date);
            const reserved=Math.max(0,I.quantity(amount,unit)-I.available(d,active,from,tag));
            if(reserved)d=I.sampleAction(d,active,{id:formId+'-release',type:'release',location:from,tag,unit:'bottle',amount:reserved,date,stamp:input.stamp,notes:'Reclasificación para venta '+formId},date);
            return I.sellStock(d,active,input,date);
          });
        }else if(screen==='sample'){
          Object.assign(input,{stockType:'any',notes:$s('simple-sample-notes').value});const type=$s('simple-sample-action').value,date=today();
          write(d=>type==='consume'?I.deliverSamples(d,active,input,date):I.sampleAction(d,active,{...input,type,date,location:from,stockType:type==='reserve'?'commercial':'sample',notes:input.notes||'Clasificación desde Muestras'},date));
        }else{
          Object.assign(input,{to:$s('simple-destination').value,isSample:false,stockType:'commercial',cost:$s('simple-freight').value.trim().replace(',','.'),currency:$s('simple-currency').value});write(d=>I.moveStock(d,active,input,today()));
        }
      }
      toast(screen==='count'?'Existencias actualizadas.':screen==='sale'?'Venta registrada.':screen==='sample'?'Operación de muestras registrada.':'Origen y destino actualizados.');open(active,screen,preferred);
    }catch(e){fail(e);}
  }
  function applySaleDialog(id,saleId){
    safeData();const sale=I.sales(data,id).find(x=>x.id===saleId);if(!sale)return;
    const choices=stockOptions(),token=JSON.stringify(sale),modal=document.createElement('dialog');modal.className='eb-modal';
    modal.innerHTML='<h2>Descontar venta ya registrada</h2><p>'+pretty(sale.quantity)+'. Se conserva la venta, su precio y sus pagos. No se crea otra venta.</p>'+sel('apply-sale-source','¿De qué bodega salieron?',choices.length?choices:[['','No hay existencias']],choices.find(([v])=>JSON.parse(v)[0]===sale.from)?.[0]||choices[0]?.[0]||'')+'<p id="apply-sale-preview" class="simple-preview"></p><div class="wrap-actions"><button class="secondary" data-cancel>Cancelar</button><button class="primary" data-apply>Descontar una vez</button></div><p data-error role="alert"></p>';
    document.body.append(modal);modal.onclose=()=>modal.remove();modal.querySelector('[data-cancel]').onclick=()=>modal.close();
    const preview=()=>{try{const [where,label]=selectedBucket('apply-sale-source'),b=I.balance(data,id),n=I.available(data,id,where,label);$s('apply-sale-preview').textContent=n<sale.quantity?'No hay suficiente producto en esta bodega.':'Saldo total: '+pretty(b.total)+' → '+pretty(b.total-sale.quantity);}catch(e){$s('apply-sale-preview').textContent=e.message;}};
    $s('apply-sale-source').onchange=preview;preview();
    modal.querySelector('[data-apply]').onclick=()=>{try{const [from,tag]=selectedBucket('apply-sale-source');write(d=>I.applySaleStock(d,id,saleId,{from,tag},token,{id:idNew(),stamp:stamp()},today()));modal.close();open(id,'sale',from);toast('Venta descontada una sola vez.');}catch(e){modal.querySelector('[data-error]').textContent=e.message;}};modal.showModal();
  }
  function paymentDialog(id,saleId){
    const s=I.sales(data,id).find(s=>s.id===saleId),state=I.saleStatus(s,today()),pid=idNew(),dialog=document.createElement('dialog');dialog.className='eb-modal';
    dialog.innerHTML='<h2>Registrar pago</h2><p>Saldo: '+fmt(state.pendingCents,s.currency)+'</p>'+inp('simple-pay-amount','Importe','','type="text" inputmode="decimal"')+'<div class="wrap-actions"><button class="secondary" data-cancel>Cancelar</button><button class="primary" data-save>Guardar</button></div><p data-error role="alert"></p>';
    document.body.append(dialog);dialog.querySelector('[data-cancel]').onclick=()=>dialog.close();dialog.onclose=()=>dialog.remove();dialog.querySelector('[data-save]').onclick=()=>{try{const amount=$s('simple-pay-amount').value.trim().replace(',','.');write(d=>I.addPayment(d,id,saleId,{id:pid,amount,date:today(),reference:'',stamp:stamp()},today()));dialog.close();open(id,'sale');toast('Pago guardado; no cambia el inventario.');}catch(e){dialog.querySelector('[data-error]').textContent=e.message;}};dialog.showModal();
  }
  if(new URLSearchParams(location.search).has('classic'))return;
  window.EBSimpleUI={open};
  // One entry point per lot; existing data and costing remain untouched.
  const previousDraw=drawLots;drawLots=function(){previousDraw();document.querySelectorAll('.saved-lot').forEach(card=>{const id=card.querySelector('[data-edit]')?.dataset.edit;if(!id)return;const a=card.querySelector('.actions');a.innerHTML='<button class="primary" data-simple-open="'+esc(id)+'">Abrir lote</button><button class="secondary" data-edit="'+esc(id)+'">Editar</button><button class="secondary danger-text" data-delete-lot="'+esc(id)+'">Eliminar</button>';a.querySelector('[data-simple-open]').onclick=()=>open(id);a.querySelector('[data-edit]').onclick=()=>loadLot(id,false);a.querySelector('[data-delete-lot]').onclick=()=>window.EBEditUI.deleteLot(id);});};
  document.documentElement.dataset.simpleLots='1';
})();
