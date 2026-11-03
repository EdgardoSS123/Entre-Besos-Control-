from pathlib import Path
import hashlib
p=Path('inventory-core.js');s=p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest()=='ed3bffe5650c0fdbc1af4e80025d9bfa8d4aaf19ada8a4e4887351ea242e9718','Unexpected base; do not replace changed source'
s=s.replace("const VERSION='3.3'","const VERSION='3.4'")
s=s.replace("  const CURRENCIES=['MXN','USD','SGD'];", """  const CURRENCIES=['MXN','USD','SGD'];
  const KINDS={warehouse:'Bodega',distributor:'Distribuidor',client:'Cliente'};
  const PURPOSES={transfer:'Traslado de inventario propio',consignment:'Consignación',sale:'Entrega por venta'};""")
s=s.replace("  function shipments(d,id)","""  function locationInfo(d,name){
    const record=(d.warehouses||[]).find(x=>x.name===name);
    return{name,kind:record?.kind||'warehouse',address:record?.address||'',contact:record?.contact||''};
  }
  // Physical dispatch, delivery and ownership are separate. A sale is removed
  // from owned stock on confirmed delivery, not counted in the customer's depot.
  function purposeOf(s){return s.purpose||'transfer';}
  function shipments(d,id)""")
s=s.replace('let transit=0;', 'let transit=0,deliveredSales=0;')
s=s.replace("if(start)active.forEach(s=>{add(s.from,s.tag,-s.quantity);if(s.status==='received')add(s.to,s.tag,s.quantity);else transit+=s.quantity;});", """if(start)active.forEach(s=>{
      add(s.from,s.tag,-s.quantity);
      if(s.status==='received'){
        if(purposeOf(s)==='sale')deliveredSales+=s.quantity;
        else add(s.to,s.tag,s.quantity);
      }else transit+=s.quantity;
    });""")
s=s.replace("return{configured:!!start,complete:!!start?.complete,asOf:start?.asOf||null,rows,total:total(rows),transit,knownTotal:total(rows)+transit,opening:start};", """const atThirdParties=total(rows.filter(r=>locationInfo(d,r.location).kind!=='warehouse'));
    return{configured:!!start,complete:!!start?.complete,asOf:start?.asOf||null,rows,total:total(rows),transit,knownTotal:total(rows)+transit,atThirdParties,deliveredSales,opening:start};""")
s=s.replace("if(!locations(d).includes(input.to))fail('Selecciona la bodega de destino.');", """if(!locations(d).includes(input.to))fail('Selecciona la bodega, distribuidor o cliente de destino.');
    const destination=locationInfo(d,input.to),purpose=input.purpose||'transfer';
    if(!Object.hasOwn(PURPOSES,purpose))fail('Selecciona el motivo del envío.');
    if(destination.kind!=='warehouse'&&purpose==='transfer')fail('Para un distribuidor o cliente indica consignación o entrega por venta.');""")
s=s.replace("from:input.from||null,to:input.to,tag:input.tag,quantity:n", "from:input.from||null,to:input.to,destination:clone(destination),purpose,inputAmount:n===null?null:Number(input.amount),inputUnit:input.unit,tag:input.tag,quantity:n")
a=s.index('  function addLocation(');b=s.index('  const api=',a)
s=s[:a]+"""  function addLocation(d,name,details={}){
    name=String(name||'').trim();if(name.length<2||name.length>100)fail('Escribe un nombre de destino de 2 a 100 caracteres.');
    const kind=details.kind||'warehouse';
    if(!Object.hasOwn(KINDS,kind))fail('Selecciona bodega, distribuidor o cliente.');
    if(locations(d).some(s=>s.toLocaleLowerCase()===name.toLocaleLowerCase()))fail('Este destino ya existe. Usa un nombre distinto para cada sucursal.');
    const next=clone(d);next.warehouses=next.warehouses||[];
    next.warehouses.push({name,kind,address:String(details.address||'').trim().slice(0,400),contact:String(details.contact||'').trim().slice(0,160)});
    return next;
  }
"""+s[b:]
s=s.replace('CURRENCIES,pack','CURRENCIES,KINDS,PURPOSES,locationInfo,purposeOf,pack')
assert hashlib.sha256(s.encode()).hexdigest()=='04d6ae3c2fdbfebdcf63092c4e9f90434883a73704579ea708382ff3dd7724a3'
p.write_text(s)
