'use strict';
const assert=require('node:assert/strict'),E=require('../executive-core.js');
let I=require('../inventory-core.js');I=require('../commerce-core.js')(I);I=require('../simple-core.js')(I);I=require('../corrections-core.js')(I);
const day='2026-11-04';let d={lots:[{id:'PARTNER-TEST',p:0,bottles:60,unitCost:200,totalCost:12000,ml:720}],moves:[],contacts:[{country:'USA',name:'PRIVATE-CONTACT',place:'Austin',email:'private@example.test',phone:'+1 512 000 0000'}],sales:[{client:'PRIVATE-LEGACY',amount:321,currency:'MXN',status:'private-payment-status'},{customer:'PRIVATE-LEGACY-2',amount:79,currency:'MXN'},{client:'PRIVATE-LEGACY-USD',amount:20,currency:'USD'},{client:'PRIVATE-UNKNOWN',currency:'USD'},{client:'PRIVATE-CANCELLED',amount:99999,currency:'MXN',status:'cancelled'}]};
d=I.initializeOrigin(d,'PARTNER-TEST','Oaxaca',day,day);
d=I.sellStock(d,'PARTNER-TEST',{id:'paid-sale',from:'Oaxaca',tag:'Por clasificar',amount:6,unit:'bottle',price:'1000',priceBasis:'bottle',currency:'MXN',customer:'PRIVATE-MX-BUYER',payment:'paid',stamp:day},day);
d=I.sellStock(d,'PARTNER-TEST',{id:'pending-sale',from:'Oaxaca',tag:'Por clasificar',amount:4,unit:'bottle',price:'100',priceBasis:'bottle',currency:'USD',customer:'PRIVATE-US-BUYER',payment:'pending',stamp:day},day);
const original=JSON.stringify(d),m=E.build(d,I),sales=m.sections.find(s=>s.title==='Ventas');
assert.deepEqual(sales.head,['Moneda','Ventas']);assert.deepEqual(sales.body,[['MXN',E.money(6000,'MXN')],['USD',E.money(400,'USD')]]);
assert(!m.sections.some(s=>s.title==='Ventas por cliente'));
const old=m.sections.find(s=>s.title==='Ventas antiguas sin vínculo a lote');assert.deepEqual(old.head,['Moneda','Registros','Importe conocido','Sin precio']);assert.deepEqual(old.body,[['MXN','2',E.money(400,'MXN'),'0'],['USD','2',E.money(20,'USD'),'1']]);
function noBuyers(model){const visible=JSON.stringify({sections:model.sections,metrics:model.metrics,notes:model.notes});for(const term of ['Cobrado registrado','Por cobrar','Pago por aclarar','cobranza','Ventas y saldos','Ventas por cliente','"Cliente"','PRIVATE-','private@example.test','private-payment-status'])assert(!visible.includes(term),term);}
noBuyers(m);assert.equal(m.summary.finance.MXN.sales,600000);assert.equal(m.summary.finance.MXN.paid,600000);assert.equal(m.summary.finance.USD.pending,40000);
const unknown=JSON.parse(original);unknown.lotSales[0].priceKnown=false;const u=E.build(unknown,I);noBuyers(u);assert.equal(u.summary.finance.MXN.sales,0);assert.equal(u.summary.finance.MXN.unknownPrice,1);assert(u.notes.some(x=>x.includes('1 venta(s) sin precio')));assert(!u.sections.some(s=>s.title==='Ventas que aún no tienen precio'));
const unknownLegacy=JSON.parse(original);unknownLegacy.sales=[{client:'PRIVATE-NOPRICE',currency:'MXN'}];assert.equal(E.build(unknownLegacy,I).sections.find(s=>s.title==='Ventas antiguas sin vínculo a lote').body[0][2],'Sin capturar');
assert.equal(JSON.stringify(d),original,'Reporting must never modify original buyers, payments or inventory.');
console.log('PASS PARTNER SALES: no buyer lists, including unpriced and legacy sales; currency totals preserved, cancelled legacy excluded, unknown prices retained, all original contacts/payments/inventory untouched.');
