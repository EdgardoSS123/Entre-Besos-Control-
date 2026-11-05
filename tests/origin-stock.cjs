'use strict';
const assert=require('node:assert/strict');let I=require('../inventory-core.js');I=require('../commerce-core.js')(I);I=require('../simple-core.js')(I);I=require('../corrections-core.js')(I);
const day='2026-11-04';let serial=0;const meta=()=>({id:'edit-'+(++serial),stamp:day+'T16:00:00Z',localDate:day});
const base={lots:[{id:'L',p:2,ml:700,bottles:714,unitCost:218.13,totalCost:155744.82}],moves:[],contacts:[{name:'Keep'}],documents:[{keep:'unchanged'}]};
let d=I.initializeOrigin(base,'L','CDMX',day,day);
assert.equal(I.balance(d,'L').total,714);assert.equal(base.inventoryOpenings,undefined);
assert.deepEqual(I.initializeOrigin(d,'L','Oaxaca',day,day),d); // No duplicate or implicit relocation.
let sold=I.sellStock(d,'L',{id:'s1',from:'CDMX',tag:'Por clasificar',amount:25,unit:'bottle',price:'1000',priceBasis:'bottle',currency:'MXN',customer:'Demo',payment:'pending',stamp:day},day);
let b=I.reconciliation(sold,'L');assert.equal(b.produced,714);assert.equal(b.total,689);assert.equal(b.sold,25);assert.equal(b.unexplained,0);
assert.deepEqual(I.packCounts(689),{bottles:689,fullCases:114,looseBottles:5,caseSize:6,equivalentCases:689/6});
assert.equal(I.packCounts(25).fullCases,4);assert.equal(I.packCounts(25).looseBottles,1);
let delivered=I.deliverSamples(sold,'L',{id:'sample',from:'CDMX',tag:'Por clasificar',amount:6,unit:'bottle',stockType:'commercial',stamp:day},day);
b=I.reconciliation(delivered,'L');assert.equal(b.total,683);assert.equal(b.used,6);assert.equal(b.produced,714);assert.equal(b.unexplained,0);assert.equal(delivered.lotSampleActions[0].income,0);assert.equal(delivered.lotSampleActions[0].receivable,0);
let reserved=I.sampleAction(delivered,'L',{id:'reserve',location:'CDMX',tag:'Por clasificar',type:'reserve',amount:12,unit:'bottle',date:day,stamp:day},day);
assert.equal(I.balance(reserved,'L').total,683);assert.equal(I.reconciliation(reserved,'L').used,6); // reserving is not delivering
reserved=I.deliverSamples(reserved,'L',{id:'sample2',from:'CDMX',tag:'Por clasificar',amount:1,unit:'box',stockType:'sample',stamp:day},day);
assert.equal(I.balance(reserved,'L').total,677);assert.equal(I.balance(reserved,'L').sampleTotal,6);assert.equal(I.reconciliation(reserved,'L').used,12);
const moved=I.moveStock(reserved,'L',{id:'move',from:'CDMX',to:'EB1-1 · Edgardo',tag:'Por clasificar',amount:10,unit:'box',stamp:day},day);
assert.equal(I.balance(moved,'L').total,677);assert.equal(I.available(moved,'L','EB1-1 · Edgardo','Por clasificar'),60);
assert.equal(I.reconciliation(moved,'L').produced,714);
// Reproduce screenshot: a known/historical sale wasn't deducted. Repair must be explicit and reversible.
let wrong=I.knownSale(d,'L',{id:'old-sale',amount:25,unit:'bottle',price:'1000',priceBasis:'bottle',currency:'MXN',payment:'paid',customer:'Known',date:'2024-11-03',stamp:day},day);
assert.equal(I.reconciliation(wrong,'L').unexplained,-25);assert.equal(I.balance(wrong,'L').total,714);
const old=JSON.stringify(wrong.lotSales[0]);let fixed=I.applySaleStock(wrong,'L','old-sale',{from:'CDMX',tag:'Por clasificar'},old,meta(),day);
assert.equal(I.balance(fixed,'L').total,689);assert.equal(I.reconciliation(fixed,'L').sold,25);assert.equal(fixed.lotSales.length,1);assert.deepEqual(fixed.lotSales[0].payments,wrong.lotSales[0].payments);assert.equal(fixed.lotSales[0].date,'2024-11-03');assert.equal(I.reconciliation(fixed,'L').unexplained,0);
assert.throws(()=>I.applySaleStock(fixed,'L','old-sale',{from:'CDMX',tag:'Por clasificar'},JSON.stringify(fixed.lotSales[0]),meta(),day),/ya descuenta/);
const undone=I.undoCorrection(fixed,fixed.editHistory.at(-1).id,meta());assert.equal(I.balance(undone,'L').total,714);
let missing=I.knownSale(d,'L',{id:'unknown',amount:25,unit:'bottle',price:'',priceBasis:'bottle',currency:'MXN',payment:'unknown',stamp:day},day);
missing=I.applySaleStock(missing,'L','unknown',{from:'CDMX',tag:'Por clasificar'},JSON.stringify(missing.lotSales[0]),meta(),day);
assert.equal(I.balance(missing,'L').total,689);assert.equal(missing.lotSales[0].priceKnown,false);assert.equal(missing.lotSales[0].date,null);
// Deleting or editing a delivered sample restores or adjusts stock only once.
let rev=I.removeRecord(delivered,'L','sample','sample',JSON.stringify(delivered.lotSampleActions[0]),meta());assert.equal(I.balance(rev,'L').total,689);
rev=I.undoCorrection(rev,rev.editHistory.at(-1).id,meta());assert.equal(I.balance(rev,'L').total,683);
rev=I.correctSample(rev,'L','sample',{location:'CDMX',tag:'Por clasificar',amount:3,unit:'bottle',type:'consume',date:day,notes:'Corrected'},JSON.stringify(rev.lotSampleActions[0]),meta(),day);assert.equal(I.balance(rev,'L').total,686);
assert.throws(()=>I.deliverSamples(delivered,'L',{id:'too-many',from:'CDMX',tag:'Por clasificar',amount:-1000,unit:'bottle',stockType:'commercial',stamp:day},day));
// Setting origin on an existing lot with current stock never overwrites the count.
const record={...sold.lots[0],originWarehouse:'Oaxaca'};const corrected=I.correctLot(sold,'L',record,JSON.stringify(sold.lots[0]),meta());assert.equal(I.balance(corrected,'L').total,689);assert.equal(I.available(corrected,'L','CDMX','Por clasificar'),689);
// Origin added to an unconfigured old lot is reversible together with the generated initial balance.
let oldOrigin=I.correctLot(base,'L',{...base.lots[0],originWarehouse:'CDMX'},JSON.stringify(base.lots[0]),meta());assert.equal(I.balance(oldOrigin,'L').total,714);
oldOrigin=I.undoCorrection(oldOrigin,oldOrigin.editHistory.at(-1).id,meta());assert.equal(I.balance(oldOrigin,'L').total,0);
assert.deepEqual(moved.documents,base.documents);assert.deepEqual(moved.contacts,base.contacts);
console.log('PASS ORIGIN STOCK: 714-25=689, exact cases/remainders, one-time origin, samples delivered/reserved, warehouse moves, explicit repair, payments preserved, undo/delete, unknown historical fields and no mutation.');
