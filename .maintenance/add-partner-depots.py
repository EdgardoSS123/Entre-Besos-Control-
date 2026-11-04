"""Add requested partner depots without rewriting any stored balances."""
from pathlib import Path
import hashlib
expected = {
 'inventory-core.js':'d9d495768091277645d170d040d8ff0a58890838',
 'lot-operations.js':'ada87d17bc50805d9fb14b2d25d6f50ec41d99ad',
 'commerce-ui.js':'1458c0e7f8f735541bcb978478f8cd8b0a2bbabd',
 'lot-operations.css':'78dbdc2c526d491c4b237a78ddfa6bbb9f30dee5',
 'control.html':'3d20f7624df54ce8ae4314d07140701ec7dc2012',
}
for name,sha in expected.items():
 b=Path(name).read_bytes()
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==sha, 'Source changed: '+name

def replace(s, old, new):
 assert s.count(old)==1, 'Expected a unique replacement: '+old[:100]
 return s.replace(old,new)
p=Path('inventory-core.js');s=p.read_text()
s=replace(s,"const VERSION='3.4',BOX=6,PALLET=480,HALF=240;", "const VERSION='3.4.1-minibodegas',BOX=6,PALLET=480,HALF=240;")
s=replace(s,"  const LOCATIONS=['Oaxaca','CDMX','USA','Singapur'];", """  const LOCATIONS=['Oaxaca','CDMX','USA','Singapur'];
  // Catalog only: no automatic opening balance, movement, sale or user account.
  const PARTNER_DEPOTS=Object.freeze([
    Object.freeze({name:'EB1-1 · Edgardo',code:'EB1-1',custodian:'Edgardo',parent:'CDMX'}),
    Object.freeze({name:'EB1-2 · Ricardo',code:'EB1-2',custodian:'Ricardo',parent:'CDMX'}),
    Object.freeze({name:'EB1-3 · Mario',code:'EB1-3',custodian:'Mario',parent:'CDMX'})
  ]);""")
s=replace(s,"function locations(d){return [...new Set([...LOCATIONS,...(d.warehouses||[]).map(x=>x.name)])];}", "function locations(d){return [...new Set([...LOCATIONS,...PARTNER_DEPOTS.map(x=>x.name),...(d.warehouses||[]).map(x=>x.name)])];}")
s=replace(s,"    return{name,kind:record?.kind||'warehouse',address:record?.address||'',contact:record?.contact||''};", "    const depot=PARTNER_DEPOTS.find(x=>x.name===name);\n    return{name,kind:record?.kind||'warehouse',address:record?.address||'',contact:record?.contact||'',...(depot?{parent:depot.parent,code:depot.code,custodian:depot.custodian,isPartnerDepot:true}:{})};")
s=replace(s,'const api={VERSION,BOX,PALLET,HALF,LOCATIONS,', 'const api={VERSION,BOX,PALLET,HALF,LOCATIONS,PARTNER_DEPOTS,')
p.write_text(s)
p=Path('lot-operations.js');s=p.read_text()
marker='  function renderWarehouses(){'
new='''  function partnerDepotDirectory(){
    const choices=[{name:'CDMX',code:'Bodega principal',custodian:'CDMX'},...I.PARTNER_DEPOTS];
    return '<section class="card partner-depots"><div class="card-head"><h2>México · CDMX y minibodegas</h2></div><div class="card-body"><p class="small-note">Producto de Entre Besos en custodia de cada socio. Llevarlo a su casa es un traslado interno, no una venta.</p><div class="partner-depot-grid">'+choices.map(x=>'<button class="secondary partner-depot '+(locationFilter===x.name?'selected':'')+'" data-partner-location="'+esc(x.name)+'" aria-pressed="'+String(locationFilter===x.name)+'"><strong>'+esc(x.code)+'</strong><span>'+esc(x.custodian)+'</span></button>').join('')+'</div><p class="small-note">Cada ubicación tiene su propio saldo. No se suma de nuevo al inventario de CDMX.</p></div></section>';
  }
'''
s=replace(s,marker,new+marker)
s=replace(s,"'</select></div></div></section><div class=\"warehouse-lots\">'", "'</select></div></div></section>'+partnerDepotDirectory()+'<div class=\"warehouse-lots\">'")
s=replace(s,"by('warehouse-filter').onchange=()=>{locationFilter=by('warehouse-filter').value;renderWarehouses();};", "by('warehouse-filter').onchange=()=>{locationFilter=by('warehouse-filter').value;renderWarehouses();};document.querySelectorAll('[data-partner-location]').forEach(btn=>btn.onclick=()=>{locationFilter=btn.dataset.partnerLocation;renderWarehouses();});document.querySelectorAll('[data-depot-sale]').forEach(btn=>btn.onclick=()=>window.EBCommerceUI.render(btn.dataset.depotSale,{from:locationFilter}));")
s=replace(s,"'<button class=\"secondary\" data-stock=\"'+esc(l.id)+'\">Ver lote y envíos</button></article>'", "'<div class=\"wrap-actions\"><button class=\"secondary\" data-stock=\"'+esc(l.id)+'\">Ver lote y envíos</button><button class=\"primary\" data-depot-sale=\"'+esc(l.id)+'\">Registrar venta</button></div></article>'")
s=replace(s,"I.locationInfo(data,loc).kind!=='warehouse'?' · Inventario propio en terceros':''", "I.locationInfo(data,loc).isPartnerDepot?' · Minibodega de CDMX · Responsable: '+esc(I.locationInfo(data,loc).custodian):I.locationInfo(data,loc).kind!=='warehouse'?' · Inventario propio en terceros':''")
s=replace(s,"by('destination-detail').textContent=[info.address,info.contact].filter(Boolean).join(' · ');", "by('destination-detail').textContent=[info.isPartnerDepot?'Minibodega de CDMX · Responsable: '+info.custodian:'',info.address,info.contact].filter(Boolean).join(' · ');")
p.write_text(s)
p=Path('commerce-ui.js');s=p.read_text()
s=replace(s,"      tab(!!options.samples);salePreview();sampleHints();", "      if(options.from&&I.locations(data).includes(options.from)){by('sale-from').value=options.from;const row=I.balance(data,id).rows.find(r=>r.location===options.from&&r.commercialQuantity>0);if(row)by('sale-tag').value=row.tag;}\n      tab(!!options.samples);salePreview();sampleHints();")
p.write_text(s)
p=Path('lot-operations.css');p.write_text(p.read_text()+'''\n/* Partner depots: same visual language, independent locations, no new balances. */
.partner-depots .partner-depot-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:14px 0}
.partner-depots .partner-depot{display:flex;flex-direction:column;align-items:flex-start;text-align:left;gap:5px;min-height:78px;white-space:normal;padding:14px;min-width:0}
.partner-depots .partner-depot span{font-size:13px;color:#617089}
.partner-depots .partner-depot.selected{border-color:#d90074;background:#fff2f8;color:#a90059}
.partner-depots .partner-depot:focus-visible{outline:3px solid #d90074;outline-offset:2px}
@media(max-width:700px){.partner-depots .partner-depot-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.partner-depots .card-head h2{font-size:17px}}
''')
p=Path('control.html');s=p.read_text()
s=replace(s,'lot-operations.css?v=34','lot-operations.css?v=mini1')
s=replace(s,'inventory-core.js?v=34','inventory-core.js?v=mini1')
import re
assert len(re.findall(r'lot-operations.js\?v=[^"\s]+',s))==1
s=re.sub(r'lot-operations.js\?v=[^"\s]+','lot-operations.js?v=mini1',s)
assert len(re.findall(r'commerce-ui.js\?v=[^"\s]+',s))==1
s=re.sub(r'commerce-ui.js\?v=[^"\s]+','commerce-ui.js?v=mini1',s)
s=s.replace('Control v3.4 · Lotes y bodegas','Control v3.4.1 · Minibodegas EB1')
p.write_text(s)
print('Partner depot catalog and location controls applied. Existing storage is untouched.')
