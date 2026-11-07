/* Reporting only: never reconciles, migrates, or writes business records. */
(function(root){
  'use strict';
  const packages=typeof module!=='undefined'&&module.exports?require('./packaging.js'):root.EBPackages;
  const names=['Espadín Capón','Cupreata','Dark Blend'];
  const number=n=>new Intl.NumberFormat('es-MX',{maximumFractionDigits:3}).format(n);
  const valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
  const money=(n,c='MXN')=>valid(n)?new Intl.NumberFormat('es-MX',{style:'currency',currency:/^[A-Z]{3}$/.test(c)?c:'MXN'}).format(Number(n))+' '+c:'Sin capturar';
  const text=v=>String(v??'');
  function array(d,k){if(d[k]===undefined)return[];if(!Array.isArray(d[k])||d[k].some(x=>!x||typeof x!=='object'))throw Error('No se puede leer '+k+'. No se modificaron tus datos.');return d[k];}
  function cases(n){return packages.describe(n,true);}
  function quantity(n){return number(n)+' bot.\n'+cases(n);}
  const metric=(label,n)=>({label,value:number(n),note:cases(n)});
  function section(title,head,body,right=[]){return{title,head,body,right};}
  function materials(d,kind,ctx={}){
    const rows=array(d,kind==='marketing'?'materials':'supplies').filter(r=>(!ctx.location||r.loc===ctx.location)&&(!ctx.search||[r.name,r.presentation].join(' ').toLocaleLowerCase('es').includes(ctx.search.toLocaleLowerCase('es'))));
    const totals={},missing=rows.filter(r=>!valid(r.totalCost)).length;
    rows.forEach(r=>{if(valid(r.totalCost)){const c=r.currency||'MXN';totals[c]=(totals[c]||0)+Number(r.totalCost);}});
    return {rows,totals,missing,section:section(kind==='marketing'?'Material marketing':'Insumos',['Concepto / presentación','Bodega','Cantidad','Costo total','Costo / unidad'],rows.map(r=>[text(r.name)+(r.presentation?'\n'+r.presentation:''),text(r.loc||'Sin ubicación'),valid(r.qty)?number(Number(r.qty)):'Sin capturar',money(r.totalCost,r.currency||'MXN'),valid(r.totalCost)&&Number(r.qty)>0?money(Number(r.totalCost)/Number(r.qty),r.currency||'MXN'):'No calculable']),[2,3,4])};
  }
  function build(d,ctx,I){
    if(!d||!Array.isArray(d.lots)||!Array.isArray(d.moves))throw Error('El respaldo actual no tiene un formato válido.');
    const model={title:'Reporte general',subtitle:'Lotes, existencias y materiales',file:'general',metrics:[],sections:[],notes:[],scope:'Todos los registros guardados'};
    if(ctx.type==='marketing'||ctx.type==='supplies'){
      const m=materials(d,ctx.type,ctx);model.title=ctx.type==='marketing'?'Material marketing':'Inventario de insumos';model.subtitle='Existencias y costos registrados';model.file=ctx.type;
      model.scope=(ctx.location||'Todas las bodegas')+(ctx.search?' · Búsqueda: '+ctx.search:'');
      model.metrics=[{label:'REGISTROS',value:number(m.rows.length),note:'Conceptos y presentaciones'},{label:'UNIDADES',value:number(m.rows.reduce((s,r)=>s+(valid(r.qty)?Number(r.qty):0),0)),note:'Cantidad capturada'},{label:'COSTO CONOCIDO · MXN',value:money(m.totals.MXN||0).replace(' MXN',''),note:'No incluye costos pendientes'},{label:'SIN COSTO CAPTURADO',value:number(m.missing),note:'No se consideran gratuitos'}];
      model.sections.push(m.section,section('Totales por moneda',['Moneda','Costo total capturado'],Object.entries(m.totals).map(([c,n])=>[c,money(n,c)]),[1]));
      model.notes.push('El costo por unidad es el costo total dividido entre la cantidad. Los importes sin capturar no se sustituyen por cero.','Las cantidades de insumos y marketing son independientes de las botellas de mezcal. No se descuentan automáticamente al producir un lote.');
      return model;
    }
    if(!I||typeof I.reconciliation!=='function')throw Error('No se cargó el cálculo de inventarios. Recarga la app antes de generar el PDF.');
    const lots=d.lots.filter(l=>(!ctx.lotId||l.id===ctx.lotId)&&(!ctx.search||[l.id,names[l.p]].join(' ').toLocaleLowerCase('es').includes(ctx.search.toLocaleLowerCase('es'))));
    if(ctx.lotId&&!lots.length)throw Error('No se encontró el lote. No se generó un reporte vacío.');
    const balances=lots.map(l=>({l,b:I.reconciliation(d,l.id)}));
    const state=balances.reduce((s,{b})=>({produced:s.produced+b.produced,sold:s.sold+b.sold,used:s.used+b.used,total:s.total+b.total,transit:s.transit+b.transit,unexplained:s.unexplained+b.unexplained}),{produced:0,sold:0,used:0,total:0,transit:0,unexplained:0});
    const locationRows=[];
    balances.forEach(({l,b})=>b.rows.filter(r=>!ctx.location||r.location===ctx.location).forEach(r=>locationRows.push([l.id,r.location,r.tag,quantity(r.quantity),number(r.commercialQuantity??0),number(r.sampleQuantity??0)])));
    const quantities=['Lote','Bodega','Etiqueta','Saldo / equivalencia','Comerciales','Muestras en bodega'];
    if(ctx.type==='warehouse'){
      model.title='Inventario por bodega';model.subtitle=ctx.location||'Todas las bodegas';model.file='bodega-'+(ctx.location||'todas');model.scope='Solo '+(ctx.location||'las bodegas seleccionadas');
      const rows=balances.flatMap(({b})=>b.rows.filter(r=>r.location===ctx.location));const sum=k=>rows.reduce((s,r)=>s+(r[k]||0),0);
      model.metrics=[metric('SALDO ACTUAL',sum('quantity')),metric('PARA VENTA',sum('commercialQuantity')),metric('MUESTRAS EN BODEGA',sum('sampleQuantity'))];
      model.sections.push(section('Existencias por lote',quantities,locationRows,[3,4,5]));
      const pending=balances.filter(({b})=>!b.configured||!b.complete&&!b.rows.some(r=>r.location===ctx.location));
      if(pending.length)model.notes.push('Conteo pendiente o parcial en esta bodega: '+pending.map(({l})=>l.id).join(', ')+'. No se asume que el inventario desconocido sea cero.');
    } else {
      model.title=ctx.lotId?'Control del lote':'Reporte general';model.subtitle=ctx.lotId?ctx.lotId+' · '+(names[lots[0].p]||'Producto'): 'Resumen para socios';model.file=ctx.lotId?'lote-'+ctx.lotId:'general';
      model.scope=ctx.lotId?'Lote '+ctx.lotId+(ctx.historyLocation?' · Historial: '+ctx.historyLocation:' · Todas las bodegas'):(ctx.search?'Búsqueda: '+ctx.search:'Todos los lotes guardados');
      model.metrics=[metric('PRODUCIDAS',state.produced),metric('VENDIDAS',state.sold),metric('MUESTRAS ENTREGADAS',state.used),metric('SALDO EN BODEGAS',state.total)];
      model.sections.push(section('Producción y saldo actual',['Lote / variedad','Producidas','Vendidas','Muestras entregadas','Saldo actual','Costo / botella'],balances.map(({l,b})=>[l.id+'\n'+(names[l.p]||'Producto'),number(b.produced),number(b.sold),number(b.used),quantity(b.total),money(l.unitCost)]),[1,2,3,4,5]));
      model.sections.push(section('Existencias por ubicación',quantities,locationRows,[3,4,5]));
      const dif=balances.filter(({b})=>b.unexplained!==0);
      if(dif.length)model.sections.push(section('Diferencias por aclarar',['Lote','Diferencia','Interpretación'],dif.map(({l,b})=>[l.id,quantity(Math.abs(b.unexplained)),b.unexplained<0?'Registradas de más':'Faltan por ubicar o explicar']),[1]));
      if(state.transit)model.notes.push('En tránsito: '+quantity(state.transit).replace('\n',' · ')+'. Se muestra separado del saldo físico en bodegas.');
    }
    const match=(from,to)=>{const loc=ctx.location||ctx.historyLocation;return !loc||(loc==='__unknown__'?!from&&!to:from===loc||to===loc);};
    const sales=balances.flatMap(({l})=>I.sales(d,l.id).filter(s=>match(s.from,'')).map(s=>({l,s})));
    if(sales.length){
      model.sections.push(section('Ventas registradas',['Lote / fecha','Cliente / origen','Botellas','Precio / botella','Total','Cobranza'],sales.map(({l,s})=>{
        const st=I.saleStatus(s,new Date().toISOString().slice(0,10)),total=valid(s.totalCents)?Number(s.totalCents)/100:null;
        return [l.id+'\n'+(s.date||'Fecha no recordada'),(s.customer||'Sin cliente')+'\n'+(s.from||'Sin origen'),quantity(s.quantity),total!==null&&s.quantity>0?money(total/s.quantity,s.currency):'Sin capturar',money(total,s.currency),st.status+(valid(st.pendingCents)?'\nPendiente: '+money(st.pendingCents/100,s.currency):'')];
      }),[2,3,4]));
    }
    const moves=balances.flatMap(({l})=>I.shipments(d,l.id).filter(s=>s.status!=='cancelled'&&match(s.from,s.to)).map(s=>({l,s})));
    if(moves.length)model.sections.push(section('Movimientos registrados',['Lote / fecha','Origen / destino','Cantidad','Motivo / estado','Costo de envío'],moves.map(({l,s})=>[l.id+'\n'+(s.date||'Sin fecha'),(s.from||'Sin origen')+'\n'+(s.to||'Sin destino'),Number.isSafeInteger(s.quantity)?quantity(s.quantity):'Sin capturar',(I.PURPOSES?.[I.purposeOf(s)]||s.purpose||'Traslado')+'\n'+(s.historical?'Referencia histórica':s.status==='transit'?'En tránsito':'Recibido'),s.cost?.known?money(s.cost.amount,s.cost.currency)+(s.cost.included?'\nIncluido en costeo':''):'Sin capturar']),[2,4]));
    const samples=balances.flatMap(({l})=>I.sampleActions(d,l.id).filter(s=>match(s.location,'')).map(s=>({l,s})));
    if(samples.length)model.sections.push(section('Registro de muestras',['Lote / fecha','Bodega','Operación','Cantidad','Ingreso'],samples.map(({l,s})=>[l.id+'\n'+(s.date||'Sin fecha'),s.location,({reserve:'Reservadas; siguen en bodega',release:'Regresadas a comercial',consume:'Entregadas / consumidas'}[s.type]||s.type),quantity(s.quantity),'$0.00']),[3,4]));
    if(!ctx.lotId&&ctx.type!=='warehouse'){
      for(const kind of ['marketing','supplies']){const m=materials(d,kind);model.sections.push(m.section);if(m.rows.length)model.sections.push(section('Costo capturado · '+(kind==='marketing'?'marketing':'insumos'),['Moneda','Total conocido','Sin costo capturado'],Object.entries(m.totals).map(([c,n])=>[c,money(n,c),number(m.missing)+' registros']),[1,2]));}
    }
    const orderExits=balances.filter(({b})=>b.orderDelivered);if(orderExits.length)model.sections.push(section('Salidas por pedidos',['Lote','Botellas entregadas'],orderExits.map(({l,b})=>[l.id,number(b.orderDelivered)]),[1],{note:'Salidas descontadas de existencias. No generan ventas con precio ni cobros automáticamente.'}));
    model.notes.push('1 caja (corrugado) = 6 botellas; 1 pallet = 80 cajas (480 botellas). Las cajas del desglose están fuera de los pallets; las sueltas están fuera de las cajas. No es inventario de cartón vacío.','Las muestras reservadas siguen físicamente en la bodega; las entregadas se descuentan. Un traslado interno cambia la ubicación, no la producción.','Las diferencias y saldos negativos se conservan tal como resultan de tus registros. Las ventas históricas anteriores al conteo no se descuentan otra vez.','Las monedas se presentan por separado, sin aplicar un tipo de cambio. Los registros sin precio o costo no se consideran gratuitos.');
    return model;
  }
  const api={build,cases,quantity,materials,money};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBReportData=api;
})(typeof window==='undefined'?globalThis:window);
