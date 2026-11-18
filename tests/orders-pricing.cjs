'use strict';
const assert=require('node:assert/strict'),O=require('../orders-core.js');
let I=require('../inventory-core.js');for(const file of ['commerce-core','simple-core','corrections-core'])I=require('../'+file+'.js')(I);
const day='2026-11-17',stamp=day+'T18:00:00Z';let sequence=0;
const meta=(id,before)=>({id,operation:'price-'+(++sequence),stamp,day,actor:'esalazars',...(before?{expected:JSON.stringify(before)}:{})});
let d={orderSalesVersion:1,lots:[{id:'ESP',p:0,bottles:1000,ml:700,unitCost:200},{id:'CUP',p:1,bottles:1000,ml:700,unitCost:250},{id:'DB',p:2,bottles:1000,ml:700,unitCost:150}],moves:[],contacts:[{name:'Preserved contact'}],supplies:[{name:'Caps',qty:2100}]};
for(const lot of d.lots)d=I.initializeOrigin(d,lot.id,'CDMX',day,stamp);
const original=JSON.stringify(d);
const input={partner:'edgardo',customer:'Pricing test',from:'CDMX',date:day,status:'pending',pricingVersion:1,lines:[{product:0,lotId:'ESP',amount:'2',unit:'box'},{product:1,lotId:'CUP',amount:'3',unit:'bottle'},{product:2,lotId:'DB',amount:'1',unit:'box'}]};
let r=O.save(d,input,meta('order'),I);d=r.data;
assert.equal(r.order.quantity,21);assert.equal(r.order.subtotalCents,2205000);assert.equal(r.order.totalCents,2205000);assert.equal(r.order.discountCents,0);
assert.deepEqual(r.order.lines.map(l=>l.unitPriceCents),[110000,125000,85000]);
assert.equal(I.balance(d,'ESP').total,1000);assert(!d.lotSales);assert.equal(JSON.stringify(JSON.parse(original)),original);
const initial=r.order;
r=O.save(d,{...r.order,discount:{type:'percent',value:'10'}},meta('order',r.order),I);d=r.data;
assert.equal(r.order.totalCents,1984500);assert.equal(r.order.discountCents,220500);assert.deepEqual(r.order.discount,{type:'percent',value:'10.00'});
const retryMeta=meta('order',r.order),retryInput={...r.order,discount:{type:'amount',value:'150.25'}};
r=O.save(d,retryInput,retryMeta,I);d=r.data;assert.equal(r.order.totalCents,2189975);assert.equal(O.save(d,retryInput,retryMeta,I).data,d);
assert.throws(()=>O.save(d,{...initial,discount:{type:'percent',value:50}},meta('order',initial),I),/cambió/);
r=O.setStatus(d,'order','delivered',meta('order',r.order),I);d=r.data;O.assertLinkedSales(d);
assert.equal(d.lotSales.reduce((sum,s)=>sum+s.totalCents,0),r.order.totalCents);
assert.equal(d.lotSales.reduce((sum,s)=>sum+s.discountCents,0),15025);
assert(d.lotSales.every(s=>s.stockEffect===false&&s.priceKnown&&s.payments.length===0));
assert.equal(I.balance(d,'ESP').total,988);assert.equal(I.balance(d,'CUP').total,997);assert.equal(I.balance(d,'DB').total,994);
const exits=JSON.stringify(d.lotStockAdjustments),ids=d.lotSales.map(s=>s.id);
r=O.save(d,{...r.order,discount:{type:'percent',value:'12,50'}},meta('order',r.order),I);d=r.data;O.assertLinkedSales(d);
assert.equal(r.order.discountCents,275625);assert.equal(r.order.totalCents,1929375);assert.equal(JSON.stringify(d.lotStockAdjustments),exits);assert.deepEqual(d.lotSales.map(s=>s.id),ids);
const paid=structuredClone(d);paid.lotSales[0].payments=[{id:'p',amountCents:1000000,date:day}];
assert.throws(()=>O.save(paid,{...r.order,discount:{type:'percent',value:100}},meta('order',r.order),I),/cobros/);
assert.equal(paid.lotSales[0].payments[0].amountCents,1000000);
r=O.save(d,{...r.order,discount:{type:'percent',value:100}},meta('order',r.order),I);d=r.data;O.assertLinkedSales(d);assert.equal(r.order.totalCents,0);assert(d.lotSales.every(s=>s.totalCents===0));assert.equal(JSON.stringify(d.lotStockAdjustments),exits);
// An older still-open client omitting pricing fields cannot erase a discount.
const oldClient={...input,status:'delivered',customer:'Old client kept price'};delete oldClient.pricingVersion;
r=O.save(d,oldClient,meta('order',r.order),I);d=r.data;assert.equal(r.order.totalCents,0);assert.equal(r.order.discount.value,'100.00');assert.equal(JSON.stringify(d.lotStockAdjustments),exits);O.assertLinkedSales(d);
for(const discount of [{type:'percent',value:'100.01'},{type:'amount',value:'22050.01'},{type:'percent',value:'-1'},{type:'amount',value:'1.001'},{type:'amount',value:'1e3'},{type:'bad',value:'1'},null])assert.throws(()=>O.validate(d,{...input,discount},I));
assert.throws(()=>O.pricing({lines:[{product:0,quantity:Number.MAX_SAFE_INTEGER}]}),/rango/);
assert.throws(()=>O.pricing({lines:[{product:0,quantity:1,unitPriceCents:0}]}),/precio/);
// One cent distributed across repeated lots must remain exactly one cent.
const rounding={...input,lines:[{product:0,lotId:'ESP',amount:1,unit:'bottle'},{product:0,lotId:'ESP',amount:1,unit:'bottle'},{product:1,lotId:'CUP',amount:1,unit:'bottle'}],discount:{type:'amount',value:'0.01'},status:'delivered'};
const grouped=O.save(JSON.parse(original),rounding,meta('rounding'),I).data;
assert.equal(grouped.lotSales.length,2);assert.equal(grouped.lotSales.reduce((n,s)=>n+s.discountCents,0),1);assert.equal(grouped.lotSales.reduce((n,s)=>n+s.totalCents,0),344999);O.assertLinkedSales(grouped);
const fractional=O.validate(d,{...input,lines:[{product:2,lotId:'DB',amount:'0.5',unit:'box'}],discount:{type:'percent',value:'33.33'}},I);
assert.equal(fractional.quantity,3);assert.equal(fractional.subtotalCents,255000);assert.equal(fractional.discountCents,84992);assert.equal(fractional.totalCents,170008);
// The server validator checks both stored order math and linked net totals.
for(const mutate of [x=>x.partnerOrders[0].totalCents++,x=>x.partnerOrders[0].discountCents++,x=>x.partnerOrders[0].currency='USD',x=>x.lotSales[0].totalCents++,x=>x.lotSales[0].priceCents++,x=>x.lotSales[0].discountCents++,x=>x.lotSales[0].currency='USD']){const bad=structuredClone(grouped);mutate(bad);assert.throws(()=>O.assertLinkedSales(bad));}
// Showing legacy totals does not write or invent a historical price/payment.
const legacy=structuredClone(grouped);for(const key of ['pricingVersion','currency','discount','subtotalCents','discountCents','totalCents'])delete legacy.partnerOrders[0][key];for(const line of legacy.partnerOrders[0].lines)delete line.unitPriceCents;
legacy.lotSales=[];delete legacy.orderSalesVersion;const raw=JSON.stringify(legacy);
assert.equal(O.pricing(legacy.partnerOrders[0]).totalCents,345000);assert.equal(JSON.stringify(legacy),raw);
const synchronized=O.synchronizeSales(legacy,I);assert(synchronized.lotSales.every(s=>s.totalCents===null&&s.priceKnown===false&&s.paymentKnown===false));
assert.equal(O.synchronizeSales(synchronized,I),synchronized);
// Existing legacy known prices stay intact on a status transition.
const known=structuredClone(synchronized);known.lotSales[0].priceCents=80000;known.lotSales[0].totalCents=160000;known.lotSales[0].priceKnown=true;known.lotSales[0].payments=[{id:'old',amountCents:10000,date:day}];
let old=known.partnerOrders[0];let pending=O.setStatus(known,old.id,'pending',meta(old.id,old),I);assert.equal(pending.order.pricingVersion,undefined);
let back=O.setStatus(pending.data,old.id,'delivered',meta(old.id,pending.order),I);assert.equal(back.order.pricingVersion,undefined);assert.equal(back.data.lotSales[0].totalCents,160000);assert.equal(back.data.lotSales[0].payments[0].amountCents,10000);
const foreign=structuredClone(known);foreign.lotSales[0].currency='USD';const foreignBefore=JSON.stringify(foreign);
assert.throws(()=>O.save(foreign,{...foreign.partnerOrders[0],pricingVersion:1,discount:{type:'percent',value:'10'}},meta(old.id,foreign.partnerOrders[0]),I),/cobros registrados en USD/);
assert.equal(JSON.stringify(foreign),foreignBefore,'Applying MXN defaults never redenominates existing USD payments');
for(const key of ['contacts','supplies'])assert.deepEqual(d[key],JSON.parse(original)[key]);
console.log('PASS ORDER PRICING: three bottle prices, boxes, cents/rounding, percentage/peso discounts, zero total, bounds, snapshots, old-client preservation, exact retries, stale edits, single stock debit, linked-sale totals, server tampering checks, legacy prices and payment preservation.');
