'use strict';
const assert=require('node:assert/strict');
const I=require('../commerce-core.js')(require('../inventory-core.js'));
const now='2026-11-04',stamp=now+'T18:00:00Z';
const depots=I.PARTNER_DEPOTS.map(x=>x.name);
assert.deepEqual(depots,['EB1-1 · Edgardo','EB1-2 · Ricardo','EB1-3 · Mario']);
let d={lots:[{id:'MINI',p:0,ml:720,bottles:600,unitCost:200},{id:'OTHER',bottles:100,unitCost:150}],moves:[],documents:[{keep:true}],contacts:[{name:'Keep'}]};
const before=JSON.stringify(d);
for(const name of depots){assert.ok(I.locations(d).includes(name));assert.equal(I.locationInfo(d,name).parent,'CDMX');assert.equal(I.locationInfo(d,name).kind,'warehouse');}
assert.equal(JSON.stringify(d),before,'Reading the catalog must not mutate data');
assert.equal(I.locations({...d,warehouses:[{name:depots[0],kind:'warehouse'}]}).filter(x=>x===depots[0]).length,1);
assert.throws(()=>I.addLocation(d,depots[0]),/existe/);
d=I.saveOpening(d,'MINI',{asOf:now,complete:true,stamp,rows:[{location:'CDMX',tag:'Nacional',amount:20,unit:'box'}]},now);
function quantity(where){return I.balance(d,'MINI').rows.find(x=>x.location===where&&x.tag==='Nacional')?.quantity||0;}
for(const [i,to] of depots.entries()){
 d=I.saveShipment(d,'MINI',{id:'to-'+i,from:'CDMX',to,purpose:'transfer',tag:'Nacional',amount:2,unit:'box',date:now,stamp,received:false},now);
 assert.equal(I.balance(d,'MINI').knownTotal,120);assert.equal(I.balance(d,'MINI').transit,12);assert.equal(quantity(to),0);
 d=I.receive(d,'MINI','to-'+i,now,now,stamp);assert.equal(quantity(to),12);assert.equal(I.balance(d,'MINI').total,120);
 assert.equal(I.sales(d,'MINI').length,0,'Internal transfers are not sales');
}
assert.equal(quantity('CDMX'),84);assert.equal(I.balance(d,'MINI').atThirdParties,0);
d=I.saveSale(d,'MINI',{id:'sale',mode:'direct',from:depots[0],tag:'Nacional',customer:'Test customer',amount:1,unit:'box',price:6600,priceBasis:'box',currency:'MXN',paidAmount:0,date:now,stamp},now);
assert.equal(quantity(depots[0]),6);assert.equal(quantity('CDMX'),84);assert.equal(I.balance(d,'MINI').total,114);assert.equal(I.saleStatus(d.lotSales[0],now).pendingCents,660000);
d=I.addPayment(d,'MINI','sale',{id:'pay',amount:6600,date:now,stamp},now);assert.equal(I.balance(d,'MINI').total,114);assert.equal(I.saleStatus(d.lotSales[0],now).status,'Pagada');
d=I.saveShipment(d,'MINI',{id:'return',from:depots[2],to:'CDMX',purpose:'transfer',tag:'Nacional',amount:2,unit:'bottle',date:now,stamp,received:true},now);
assert.equal(quantity(depots[2]),10);assert.equal(quantity('CDMX'),86);assert.equal(I.balance(d,'MINI').total,114);
assert.throws(()=>I.saveSale(d,'MINI',{id:'over',from:depots[0],tag:'Nacional',customer:'Test',amount:2,unit:'box',price:1,priceBasis:'box',currency:'MXN',date:now},now),/Solo hay/);
assert.deepEqual(d.lots,JSON.parse(before).lots);assert.deepEqual(d.documents,JSON.parse(before).documents);assert.deepEqual(d.contacts,JSON.parse(before).contacts);
const initial=I.saveOpening(JSON.parse(before),'MINI',{asOf:now,complete:false,stamp,rows:[{location:depots[0],tag:'Nacional',amount:3,unit:'box'},{location:depots[1],tag:'Nacional',amount:1,unit:'box',isSample:true}]},now);
assert.equal(I.balance(initial,'MINI').total,24);assert.equal(I.balance(initial,'MINI').sampleTotal,6);assert.equal(I.balance(initial,'MINI').complete,false);
console.log('PASS: partner depot catalog, no mutation, initial holdings, 3 transfers, receipt, no revenue on transfer, home sale, payment, return, no double counting, preservation.');
