'use strict';
const assert=require('node:assert/strict');let I=require('../inventory-core.js');I=require('../commerce-core.js')(I);I=require('../simple-core.js')(I);I=require('../corrections-core.js')(I);
const day='2026-11-04';let serial=0;const m=()=>({id:'edit'+(++serial),stamp:day,localDate:day});
const base={lots:[{id:'L',p:2,ml:700,bottles:714,unitCost:218.13,totalCost:155744.82}],moves:[],contacts:[{name:'Unchanged'}],documents:[{keep:true}]};
let d=I.initializeOrigin(base,'L','CDMX',day,day);
const move=(id,from,to,amount,isSample=true)=>({id,from,to,amount,tag:'Por clasificar',unit:'bottle',isSample,stamp:day});
// Commercial stock can become a sample in the same warehouse movement, without a sale.
d=I.moveStock(d,'L',move('sg','CDMX','Singapur',12),day);
let b=I.reconciliation(d,'L');assert.equal(b.total,714);assert.equal(b.sampleTotal,12);assert.equal(b.sold,0);assert.equal(b.used,0);assert.equal(b.unexplained,0);
assert.equal(I.available(d,'L','CDMX','Por clasificar'),702);assert.equal(I.available(d,'L','Singapur','Por clasificar','sample'),12);assert.equal(I.available(d,'L','Singapur','Por clasificar'),0);
assert.equal(d.lotSales,undefined);assert.equal(d.lotShipments[0].sampleAccounting.income,0);assert.equal(d.lotShipments[0].sampleAccounting.receivable,0);
// Moving reserved samples to another location preserves the group totals.
d=I.addLocation(d,'Filipinas');d=I.moveStock(d,'L',move('ph','Singapur','Filipinas',6),day);
assert.equal(I.balance(d,'L').sampleTotal,12);assert.equal(I.available(d,'L','Singapur','Por clasificar','sample'),6);assert.equal(I.available(d,'L','Filipinas','Por clasificar','sample'),6);
// Delivery is distinct: reduces location total and preserves produced number.
d=I.deliverSamples(d,'L',{id:'given',from:'Filipinas',tag:'Por clasificar',amount:6,unit:'bottle',stamp:day},day);
b=I.reconciliation(d,'L');assert.equal(b.total,708);assert.equal(b.used,6);assert.equal(b.produced,714);assert.equal(b.sold,0);assert.equal(b.unexplained,0);
assert.equal(d.lotSampleActions[0].income,0);assert.equal(d.lotSampleActions[0].receivable,0);
assert.equal(I.available(I.sellStock(d,'L',{id:'s',from:'Singapur',tag:'Por clasificar',amount:1,unit:'bottle',price:'1000',priceBasis:'bottle',currency:'MXN',payment:'paid',stamp:day},day),'L','Singapur','Por clasificar'),-1);
// New origin can be marked all samples. No side effects on load or existing records.
let all=I.initializeOrigin({...base,lots:[{...base.lots[0],originSamples:true}]},'L','Singapur',day,day);
assert.equal(I.balance(all,'L').sampleTotal,714);assert.equal(I.balance(all,'L').commercialTotal,0);assert.equal(I.reconciliation(all,'L').used,0);
// Mixture at source is handled in one entry, debiting reserved samples first.
let mix=I.initializeOrigin(base,'L','CDMX',day,day);
mix=I.sampleAction(mix,'L',{id:'reserve',location:'CDMX',tag:'Por clasificar',type:'reserve',amount:5,unit:'bottle',date:day,stamp:day},day);
const before=JSON.parse(JSON.stringify(mix));mix=I.moveStock(mix,'L',move('mixed','CDMX','USA',12),day);
assert.equal(mix.lotShipments[0].sourceSampleQuantity,5);assert.equal(I.balance(mix,'L').sampleTotal,12);assert.equal(I.available(mix,'L','CDMX','Por clasificar','sample'),0);
const args={from:'CDMX',to:'USA',tag:'Por clasificar',amount:3,unit:'bottle',status:'received',date:day,receivedDate:day,purpose:'sample',stockType:'commercial',cost:'',currency:'MXN',historical:false};
mix=I.correctMove(mix,'L','mixed',args,JSON.stringify(mix.lotShipments[0]),m(),day);
assert.equal(mix.lotShipments[0].sourceSampleQuantity,3);assert.equal(I.available(mix,'L','CDMX','Por clasificar','sample'),2);assert.equal(I.available(mix,'L','USA','Por clasificar','sample'),3);assert.equal(I.balance(mix,'L').total,714);
mix=I.removeRecord(mix,'L','move','mixed',JSON.stringify(mix.lotShipments[0]),m());assert.deepEqual(I.balance(mix,'L'),I.balance(before,'L'));
// A mixed delivery, its correction, deletion and undo are also stock-safe.
mix=I.deliverSamples(before,'L',{id:'mixed-gift',from:'CDMX',tag:'Por clasificar',amount:12,unit:'bottle',stamp:day},day);
assert.equal(I.balance(mix,'L').total,702);assert.equal(I.balance(mix,'L').sampleTotal,0);assert.equal(mix.lotSampleActions.at(-1).sourceSampleQuantity,5);
mix=I.correctSample(mix,'L','mixed-gift',{location:'CDMX',tag:'Por clasificar',amount:3,unit:'bottle',type:'consume',date:day,notes:'Correction'},JSON.stringify(mix.lotSampleActions.at(-1)),m(),day);
assert.equal(I.balance(mix,'L').total,711);assert.equal(I.balance(mix,'L').sampleTotal,2);assert.equal(I.reconciliation(mix,'L').used,3);
mix=I.removeRecord(mix,'L','sample','mixed-gift',JSON.stringify(mix.lotSampleActions.at(-1)),m());assert.deepEqual(I.balance(mix,'L'),I.balance(before,'L'));
assert.throws(()=>I.moveStock(before,'L',move('over','CDMX','Singapur',-715),day),/cantidad/i);assert.throws(()=>I.deliverSamples(before,'L',{id:'overgift',from:'CDMX',tag:'Por clasificar',amount:-715,unit:'bottle',stamp:day},day),/cantidad/i);
assert.deepEqual(d.contacts,base.contacts);assert.deepEqual(d.documents,base.documents);assert.equal(base.inventoryOpenings,undefined);
console.log('PASS ALWAYS SAMPLES: commercial-to-sample transfer, Singapore and third-country tracking, no sale/income, mixed source one step, delivery deductions, edits/reversal/undo compatibility, origin samples and signed stock reconciliation.');
