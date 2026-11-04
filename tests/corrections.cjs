'use strict';
const assert=require('node:assert/strict');
let I=require('../inventory-core.js');I=require('../commerce-core.js')(I);I=require('../simple-core.js')(I);I=require('../corrections-core.js')(I);
let seq=0;const now='2026-11-04',meta=()=>({id:'change-'+(++seq),stamp:now+'T12:'+String(seq).padStart(2,'0')+':00Z'}),clone=x=>JSON.parse(JSON.stringify(x));
const original={lots:[{id:'L1',p:0,ml:720,bottles:2000,unitCost:100,totalCost:200000},{id:'OTHER',p:1,ml:720,bottles:12,unitCost:90}],moves:[{lot:'L1',quantity:1}],contacts:[{name:'Keep'}],documents:[{lotId:'L1',file:'original.pdf'},{file:'general.pdf'}]};
let d=I.countStock(original,'L1',{id:'count',location:'USA',tag:'Nacional',amount:3,unit:'pallet',samples:0,stamp:now},now);
d=I.sellStock(d,'L1',{id:'sale',from:'USA',tag:'Nacional',amount:0.5,unit:'pallet',price:600,priceBasis:'box',currency:'MXN',customer:'Cliente',payment:'pending',stamp:now},now);
d=I.moveStock(d,'L1',{id:'move',from:'USA',to:'EB1-1 · Edgardo',tag:'Nacional',amount:10,unit:'box',cost:'50',stamp:now},now);
const before=clone(d),old=d.lots[0];
d=I.correctLot(d,'L1',{...old,id:'EDITED',p:2,ml:700,bottles:714,totalCost:80000,unitCost:112},JSON.stringify(old),meta());
assert.equal(d.lotSales[0].lotId,'EDITED');assert.equal(d.lotShipments[0].lotId,'EDITED');assert.equal(d.inventoryOpenings[0].lotId,'EDITED');assert.equal(d.lotStockAdjustments[0].lotId,'EDITED');assert.equal(d.moves[0].lot,'EDITED');assert.equal(d.documents[0].lotId,'EDITED');assert.equal(I.reconciliation(d,'EDITED').unexplained,-726);
assert.deepEqual(before.lots[0],old);assert.deepEqual(d.lots[1],original.lots[1]);
assert.throws(()=>I.correctLot(d,'EDITED',{...d.lots[0],id:'other'},JSON.stringify(d.lots[0]),meta()),/Ya existe/);
let renamed=clone(d);d=I.undoCorrection(d,d.editHistory.at(-1).id,meta());assert.deepEqual(d.lots,before.lots);assert.deepEqual(d.lotSales,before.lotSales);
let sale=d.lotSales[0];d=I.correctSale(d,'L1','sale',{amount:0.25,unit:'pallet',price:'650',priceBasis:'box',currency:'MXN',customer:'Nuevo cliente',from:'USA',tag:'Nacional',date:now,notes:'Corrección'},JSON.stringify(sale),meta(),now);
assert.equal(I.balance(d,'L1').total,1320);assert.equal(d.lotSales[0].totalCents,1300000);
d=I.addPayment(d,'L1','sale',{id:'payment',amount:'1000',date:now,stamp:now},now);
d=I.correctPayment(d,'L1','sale','payment',{amount:'500',date:now},JSON.stringify(d.lotSales[0].payments[0]),meta(),now);assert.equal(d.lotSales[0].payments[0].amountCents,50000);
d=I.removeRecord(d,'L1','payment','sale',JSON.stringify(d.lotSales[0].payments[0]),meta(),'payment');assert.equal(d.lotSales[0].payments.length,0);assert.equal(I.balance(d,'L1').total,1320);
const saleBefore=d.lotSales[0];d=I.removeRecord(d,'L1','sale','sale',JSON.stringify(saleBefore),meta());assert.equal(I.balance(d,'L1').total,1440);assert.equal(d.lotSales.length,0);
d=I.undoCorrection(d,d.editHistory.at(-1).id,meta());assert.equal(I.balance(d,'L1').total,1320);assert.deepEqual(d.lotSales[0],saleBefore);
const move=d.lotShipments[0];d=I.correctMove(d,'L1','move',{from:'USA',to:'EB1-2 · Ricardo',amount:'5',unit:'box',tag:'Nacional',purpose:'transfer',stockType:'commercial',status:'received',date:now,currency:'MXN',cost:20},JSON.stringify(move),meta(),now);
assert.equal(I.available(d,'L1','EB1-1 · Edgardo','Nacional'),0);assert.equal(I.available(d,'L1','EB1-2 · Ricardo','Nacional'),30);assert.equal(I.balance(d,'L1').total,1320);
d=I.removeRecord(d,'L1','move','move',JSON.stringify(d.lotShipments[0]),meta());assert.equal(I.available(d,'L1','USA','Nacional'),1320);
// Explicit removal of all lot-owned records, not unrelated stock, contact or general documents.
const snapshot=clone(d);d=I.removeLot(d,'L1',JSON.stringify(d.lots[0]),meta());assert.equal(d.lots.length,1);assert.equal(d.lotSales.length,0);assert.equal(d.moves.length,0);assert.equal(d.documents.length,1);assert.deepEqual(d.contacts,original.contacts);
d=I.undoCorrection(d,d.editHistory.at(-1).id,meta());assert.deepEqual(d.lotSales,snapshot.lotSales);assert.deepEqual(d.documents,snapshot.documents);
// A new lot using the deleted code cannot be overwritten by a recovery.
let removed=I.removeLot(d,'L1',JSON.stringify(d.lots.find(x=>x.id==='L1')),meta());removed.lots.push({id:'L1',p:2,ml:700,bottles:12});assert.throws(()=>I.undoCorrection(removed,removed.editHistory.at(-1).id,meta()),/cambios posteriores/);
// A withdrawal to zero is a correction, never a sale.
const q=I.balance(d,'L1').rows.find(x=>x.location==='USA');d=I.correctStock(d,'L1',{location:'USA',tag:'Nacional',amount:0,unit:'bottle',samples:0,expected:[q.quantity,q.sampleQuantity],remove:true},meta(),now);assert.equal(I.balance(d,'L1').total,0);assert.equal(I.sales(d,'L1').length,1);
d=I.undoCorrection(d,d.editHistory.at(-1).id,meta());assert.equal(I.balance(d,'L1').total,1320);
// Linked sale edit/delete affects its dispatch exactly once.
let linked=I.saveShipment(d,'L1',{id:'linked-move',from:'USA',to:'CDMX',purpose:'sale',tag:'Nacional',amount:2,unit:'box',date:now,received:true,stamp:now},now);
linked=I.saveSale(linked,'L1',{id:'linked-sale',mode:'shipment',shipmentId:'linked-move',price:600,priceBasis:'box',currency:'MXN',date:now,paidAmount:0,stamp:now},now);
linked=I.correctSale(linked,'L1','linked-sale',{from:'USA',tag:'Nacional',amount:3,unit:'box',price:700,priceBasis:'box',currency:'MXN',customer:'Cliente asociado',date:now},JSON.stringify(linked.lotSales.at(-1)),meta(),now);
assert.equal(I.balance(linked,'L1').total,1302);linked=I.removeRecord(linked,'L1','sale','linked-sale',JSON.stringify(linked.lotSales.at(-1)),meta());assert.equal(I.balance(linked,'L1').total,1320);assert(!linked.lotShipments.some(x=>x.id==='linked-move'));
assert.deepEqual(original.contacts,[{name:'Keep'}]);assert(!original.inventoryOpenings);
console.log('PASS CORRECTIONS: rename linked records, editable production, duplicate and stale protection, price/quantity/location/payment corrections, single stock reversal, lot deletion, recovery, no overwrite and unrelated data preservation.');
