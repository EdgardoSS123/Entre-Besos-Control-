'use strict';
const assert=require('node:assert/strict'),O=require('../orders-core.js');
let I=require('../inventory-core.js');for(const f of ['commerce-core','simple-core','corrections-core'])I=require('../'+f+'.js')(I);
const day='2026-11-17',stamp=day+'T18:00:00Z';let seq=0;
const meta=()=>({id:'price-correction-'+(++seq),operation:'price-correction-'+seq,stamp,day,localDate:day,actor:'esalazars'});
function fixture(discount={type:'percent',value:'10'}){
 let d={orderSalesVersion:1,lots:[{id:'ESP',p:0,bottles:100,ml:700,unitCost:200},{id:'CUP',p:1,bottles:100,ml:700,unitCost:300},{id:'DB',p:2,bottles:100,ml:700,unitCost:250}],moves:[]};
 for(const l of d.lots)d=I.initializeOrigin(d,l.id,'CDMX',day,stamp);
 return O.save(d,{partner:'ricardo',customer:'Synthetic pricing test',from:'CDMX',date:day,status:'delivered',notes:'',discount,lines:[{product:0,lotId:'ESP',amount:3,unit:'bottle'},{product:1,lotId:'CUP',amount:2,unit:'bottle'},{product:2,lotId:'DB',amount:1,unit:'bottle'}]},{...meta(),id:'priced-order'},I).data;
}
const sale=(d,id='ESP')=>I.sales(d,id)[0];
const form=s=>({historical:false,from:s.from,tag:s.tag,amount:s.quantity,unit:'bottle',price:(s.priceCents/100).toFixed(2),priceBasis:'bottle',customer:s.customer,currency:s.currency,date:day,dueDate:s.dueDate||'',reference:s.reference||'',notes:s.notes||'',paymentKnown:s.paymentKnown});
function edit(d,changes={},id='ESP'){const s=sale(d,id);return I.correctSale(d,id,s.id,{...form(s),...changes},JSON.stringify(s),meta(),day);}
const total=d=>d.lotSales.filter(s=>s.status!=='cancelled').reduce((n,s)=>n+s.totalCents,0);

// Notes and collection metadata preserve the exact net cents and the original stock exits.
let d=fixture(),exits=structuredClone(d.lotStockAdjustments),expected=total(d);
assert.equal(expected,598500);assert.equal(sale(d).subtotalCents,330000);assert.equal(sale(d).totalCents,297000);
d=edit(d,{notes:'Updated delivery note',dueDate:'2026-11-30',paymentKnown:false});
assert.equal(sale(d).notes,'Updated delivery note');assert.equal(sale(d).paymentKnown,false);
assert.equal(total(d),expected);assert.deepEqual(d.lotStockAdjustments,exits);O.assertLinkedSales(d);
d=edit(d,{paymentKnown:true,customer:'Updated customer'});assert.equal(sale(d).paymentKnown,true);assert.equal(total(d),expected);assert.deepEqual(d.lotStockAdjustments,exits);O.assertLinkedSales(d);

// A changed gross price flows back to the order snapshot and keeps its discount.
d=edit(d,{price:'1000'});assert.equal(d.partnerOrders[0].lines[0].unitPriceCents,100000);
assert.equal(d.partnerOrders[0].subtotalCents,635000);assert.equal(d.partnerOrders[0].discountCents,63500);assert.equal(total(d),571500);
assert.equal(sale(d).totalCents,270000);assert.deepEqual(d.lotStockAdjustments,exits);O.assertLinkedSales(d);
const priceHistory=d.editHistory.at(-1).id;
d=I.undoCorrection(d,priceHistory,meta());assert.equal(total(d),598500);assert.equal(d.partnerOrders[0].lines[0].unitPriceCents,110000);assert.deepEqual(d.lotStockAdjustments,exits);O.assertLinkedSales(d);

// Quantity edits retain list price/discount and post exactly the new quantity.
d=edit(d,{amount:4});assert.equal(sale(d).quantity,4);assert.equal(sale(d).totalCents,396000);assert.equal(I.balance(d,'ESP').total,96);assert.equal(total(d),697500);O.assertLinkedSales(d);
assert.equal(O.activeDebits(d,'priced-order').filter(a=>a.lotId==='ESP').reduce((n,a)=>n-a.delta,0),4);

// Partial deletion reallocates the order's percentage discount; undo restores exact monetary and stock data.
const before=structuredClone(d),s=sale(d),delMeta=meta();d=I.removeRecord(d,'ESP','sale',s.id,JSON.stringify(s),delMeta);
assert.equal(d.partnerOrders[0].subtotalCents,335000);assert.equal(total(d),301500);assert.equal(I.balance(d,'ESP').total,100);O.assertLinkedSales(d);
d=I.undoCorrection(d,delMeta.id,meta());assert.deepEqual(d.lotSales,before.lotSales);assert.deepEqual(d.lotStockAdjustments,before.lotStockAdjustments);O.assertLinkedSales(d);

// Paid amounts cannot silently exceed a newly discounted/net sale and currency cannot diverge from its order.
d=I.addPayment(d,'ESP',sale(d).id,{id:'net-payment',amount:'3900',date:day,stamp},day);
const paidSnapshot=JSON.stringify(d);assert.throws(()=>edit(d,{price:'100'}),/cobros|pagos/i);assert.equal(JSON.stringify(d),paidSnapshot);
assert.throws(()=>edit(d,{currency:'USD'}),/MXN/);

// A 1-cent discount keeps its exact allocation on metadata edits, even if the net amount is not divisible by quantity.
d=fixture({type:'amount',value:'0.01'});const penny=total(d),sums=structuredClone(d.lotSales.map(s=>[s.id,s.subtotalCents,s.discountCents,s.totalCents]));
d=edit(d,{notes:'Rounding retained'});assert.equal(total(d),penny);assert.deepEqual(d.lotSales.map(s=>[s.id,s.subtotalCents,s.discountCents,s.totalCents]),sums);O.assertLinkedSales(d);

// Fully discounted orders remain zero and never acquire a payment just from a metadata save.
d=fixture({type:'percent',value:'100'});d=edit(d,{notes:'Complimentary order'});assert.equal(total(d),0);assert.equal(sale(d).totalCents,0);assert.deepEqual(sale(d).payments,[]);assert.equal(I.saleStatus(sale(d),day).status,'Sin saldo por descuento');O.assertLinkedSales(d);

// Removing a line cannot silently cap or otherwise change an explicitly entered fixed discount.
d=fixture({type:'amount',value:'6000'});const fixedSnapshot=JSON.stringify(d),fixedSale=sale(d);
assert.throws(()=>I.removeRecord(d,'ESP','sale',fixedSale.id,JSON.stringify(fixedSale),meta()),/descuento.*subtotal/i);assert.equal(JSON.stringify(d),fixedSnapshot);

console.log('PASS PRICING CORRECTIONS: exact net cents, price/quantity synchronization, stock preservation, partial delete and undo, payments bounds, MXN, penny rounding, full discount, fixed-discount bounds');
