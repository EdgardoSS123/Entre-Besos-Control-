'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),P=require('../packaging.js'),B=require('../device-backup.js');
for(const n of [0,1,5,6,82,83,234,240,438,479,480,481,714,834,1200,1440,3004,-1,-6,-83,-480,-834]){
 const p=P.parts(n);assert.equal((480*p.pallets+6*p.cases+p.loose)*p.sign,n);assert(p.cases>=0&&p.cases<80);assert(p.loose>=0&&p.loose<6);
}
for(let n=-5000;n<=5000;n++){const p=P.parts(n);assert.equal((480*p.pallets+6*p.cases+p.loose)*p.sign,n);}
assert.equal(P.describe(834),'1 pallet + 59 cajas + 0 botellas sueltas');assert.equal(P.describe(82),'0 pallets + 13 cajas + 4 botellas sueltas');assert.equal(P.describe(1200),'2 pallets + 40 cajas + 0 botellas sueltas');
for(const n of [NaN,Infinity,3.5,'834'])assert.throws(()=>P.parts(n));
const memory=()=>{const d=new Map();return{getItem:k=>d.has(k)?d.get(k):null,setItem:(k,v)=>d.set(k,v),removeItem:k=>d.delete(k)}};
let I=require('../inventory-core.js');I=require('../commerce-core.js')(I);I=require('../simple-core.js')(I);I=require('../corrections-core.js')(I);
let data={lots:[{id:'PRUEBA-PACK',p:2,ml:720,bottles:834,unitCost:237.66,totalCost:834*237.66,date:'2026-11-05'}],moves:[],contacts:[],materials:[],supplies:[],costs:{}};
data=I.initializeOrigin(data,'PRUEBA-PACK','Oaxaca','2026-11-05','2026-11-05T18:00:00Z');const raw=JSON.stringify(data);
const store=memory(),expected=B.inspect(store);assert.equal(expected.occupied,false);B.restore(store,raw,expected);assert.equal(store.getItem(B.KEY),raw);assert.equal(B.inspect(store).occupied,true);assert.throws(()=>B.restore(store,raw,B.inspect(store)),/ya tiene datos/);
const empty=memory();empty.setItem(B.KEY,JSON.stringify({lots:[],moves:[],contacts:[],costs:{}}));const before=B.inspect(empty);empty.setItem(B.KEY,JSON.stringify({lots:[],moves:[],costs:{x:1}}));assert.throws(()=>B.restore(empty,raw,before));
const draft=memory();draft.setItem(B.DRAFT,JSON.stringify({id:'PENDIENTE',lines:[]}));assert.equal(B.inspect(draft).occupied,true);
const invalid=['{}','null','[]','{"lots":{},"moves":[]}','{"lots":[],"moves":[],"__proto__":{"x":1}}','{"lots":[{"id":"X"},{"id":"X"}],"moves":[]}'];for(const r of invalid)assert.throws(()=>B.parse(r));
const quota=memory();quota.setItem=()=>{throw Error('quota')};assert.throws(()=>B.restore(quota,raw,B.inspect(quota)));assert.equal(quota.getItem(B.KEY),null);
assert.equal(JSON.stringify(data),raw);assert.equal(I.balance(data,'PRUEBA-PACK').total,834);
if(process.env.EB_APP_FIXTURE)fs.writeFileSync(process.env.EB_APP_FIXTURE,raw);
console.log('PASS PACKAGING: exact bottles = pallets*480 + cases*6 + loose; zero, fractional pallet equivalents and negative balances preserved. PASS DEVICE: no automatic writes, occupied device protection, stale guard, invalid-file rejection and exact JSON recovery.');
