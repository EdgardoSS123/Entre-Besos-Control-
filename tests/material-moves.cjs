'use strict';
const assert=require('node:assert/strict'),M=require('../material-moves-core.js'),C=require('../materials-core.js');
let serial=0;
const original={lots:[{id:'DB-SYN',p:2,bottles:438,unitCost:237.66,totalCost:104094.40}],moves:[{id:'keep',n:6}],contacts:[{name:'Preserve'}],suppliers:[{name:'Keep'}],expenses:[{amount:4}],materials:[{name:'Gorras',qty:20,totalCost:2000,loc:'CDMX'}],supplies:[{name:'Tapones',qty:6300,totalCost:59730,loc:'CDMX',unit:'unidades'}, {name:'Botellas vacías',presentation:'700 ml',qty:1000,totalCost:20000,loc:'Oaxaca'},{name:'Botellas vacías',presentation:'720 ml',qty:200,totalCost:6000,loc:'Oaxaca'}],partnerOrders:[],documents:[{id:'preserve'}]};
const base=JSON.stringify(original),stamp='2026-11-10T18:00:00Z';
function options(d,id='m-'+(++serial),index=0){const old=M.moves(d).find(m=>m.id===id);return {id,operation:'op-'+(++serial),stamp,index,actor:'synthetic',...(old?{expected:JSON.stringify(old)}:{expectedSource:JSON.stringify(d.supplies[index])})};}
const move={type:'transfer',quantity:2100,status:'transit',to:'USA',purpose:'Para retaponado',date:'2026-11-10',notes:'Synthetic',lotId:''};
let r=M.change(original,'supplies',move,options(original,'caps'),),d=r.data;
assert.equal(JSON.stringify(original),base);assert.equal(d.supplies[0].qty,4200);assert.equal(d.supplies[0].totalCost,39820);assert.equal(d.supplies.length,3);assert.equal(r.record.costCents,1991000);assert.equal(M.summary(d,'supplies').transit[0].quantity,2100);
const pending=r.record;r=M.change(d,'supplies',{...pending,status:'received'},options(d,'caps'));d=r.data;
let usa=d.supplies.find(s=>s.loc==='USA');assert.equal(d.supplies[0].qty,4200);assert.equal(usa.qty,2100);assert.equal(usa.totalCost,19910);assert.equal(M.summary(d,'supplies').transit.length,0);
const use={type:'use',quantity:2100,to:'USA',purpose:'Retaponado',date:'2026-11-10'};
let op=options(d,'use-caps',d.supplies.indexOf(usa));r=M.change(d,'supplies',use,op);d=r.data;
usa=d.supplies.find(s=>s.loc==='USA');assert.equal(usa.qty,0);assert.equal(usa.totalCost,0);assert.equal(d.supplies[0].qty,4200);
assert.equal(M.change(d,'supplies',use,op).data,d,'Retry same request no double deduction');
assert.throws(()=>M.change(d,'supplies',{...use,quantity:1},op),/referencia/i);
const beforeMetadata=JSON.stringify(d.supplies);r=M.change(d,'supplies',{...r.record,purpose:'Retaponado terminado'},options(d,'use-caps'));d=r.data;assert.equal(JSON.stringify(d.supplies),beforeMetadata);
r=M.change(d,'supplies',{...r.record,quantity:2000},options(d,'use-caps'));d=r.data;assert.equal(d.supplies.find(s=>s.loc==='USA').qty,100);assert.equal(d.supplies.find(s=>s.loc==='USA').totalCost,948.10);
r=M.change(d,'supplies',null,{...options(d,'use-caps'),action:'cancel'});d=r.data;assert.equal(d.supplies.find(s=>s.loc==='USA').qty,2100);assert.equal(d.supplies.find(s=>s.loc==='USA').totalCost,19910);
r=M.change(d,'supplies',null,{...options(d,'use-caps'),action:'restore'});d=r.data;assert.equal(d.supplies.find(s=>s.loc==='USA').qty,100);
r=M.change(d,'supplies',null,{...options(d,'use-caps'),action:'cancel'});d=r.data;
r=M.change(d,'supplies',null,{...options(d,'caps'),action:'cancel'});d=r.data;assert.equal(d.supplies[0].qty,6300);assert.equal(d.supplies[0].totalCost,59730);assert.equal(d.supplies.find(s=>s.loc==='USA').qty,0);
// A direct use at an external location withdraws from the chosen origin only.
r=M.change(original,'supplies',use,options(original,'direct-use'));assert.equal(r.data.supplies[0].qty,4200);assert.equal(r.data.supplies[0].totalCost,39820);assert.equal(r.data.supplies.length,3);
// Exact presentation and production association, no finished bottles or lot costs created.
const bottle={type:'use',quantity:500,to:'Oaxaca',purpose:'Envasado',date:'2026-11-10',lotId:'DB-SYN'};
r=M.change(original,'supplies',bottle,options(original,'bottle',1));assert.equal(r.data.supplies[1].qty,500);assert.equal(r.data.supplies[1].totalCost,10000);assert.equal(r.data.supplies[2].qty,200);assert.deepEqual(r.data.lots,original.lots);
for(const k of ['lots','moves','contacts','suppliers','expenses','materials','partnerOrders','documents'])assert.deepEqual(r.data[k],original[k],k);
const priced=r.data;assert.throws(()=>C.change(priced,'supplies',null,{id:'d',stamp,index:1,expected:JSON.stringify(priced.supplies[1]),remove:true}),/movimientos activos/);
// Partial costs remain unknown, and cancellation restores the exact known destination cost.
const unknown={lots:[],moves:[],supplies:[{name:'Insumo sin costo',loc:'Oaxaca',qty:10,totalCost:null},{name:'Insumo sin costo',loc:'USA',qty:5,totalCost:100}]};
r=M.change(unknown,'supplies',{...move,quantity:2,status:'received'},options(unknown,'unknown'));assert.equal(r.data.supplies[1].qty,7);assert.equal(r.data.supplies[1].totalCost,null);assert.equal(r.record.costCents,null);
r=M.change(r.data,'supplies',null,{...options(r.data,'unknown'),action:'cancel'});assert.equal(r.data.supplies[1].totalCost,100);assert.equal(r.data.supplies[0].qty,10);assert.equal(r.data.supplies[0].totalCost,null);
// Existing destination unit/presentation must match exactly; a 720 ml row is not a 700 ml row.
const identity=JSON.parse(base);identity.supplies.push({name:'Botellas vacías',presentation:'720 ml',qty:3,totalCost:90,loc:'USA'});
r=M.change(identity,'supplies',{...move,quantity:100,status:'received'},options(identity,'presentations',1));assert.equal(r.data.supplies.filter(x=>x.loc==='USA').length,2);assert.equal(r.data.supplies.find(x=>x.loc==='USA'&&x.presentation==='720 ml').qty,3);
// Preserve allocated value when receiving an old transit, despite an independent manual count.
r=M.change(original,'supplies',move,options(original,'transit'));let corrected=C.change(r.data,'supplies',{...r.data.supplies[0],qty:4000,totalCost:50000},{id:'manual-count',stamp,index:0,expected:JSON.stringify(r.data.supplies[0])});r=M.change(corrected,'supplies',{...r.record,status:'received'},options(corrected,'transit'));assert.equal(r.record.costCents,1991000);assert.equal(r.data.supplies[0].qty,4000);assert.equal(r.data.supplies[0].totalCost,50000);
// Marketing uses exactly the same movement semantics.
const marketingOptions={id:'marketing',operation:'marketing-op',stamp,index:0,expectedSource:JSON.stringify(original.materials[0])};
r=M.change(original,'marketing',{...use,quantity:3,purpose:'Promoción / muestras'},marketingOptions);assert.equal(r.data.materials[0].qty,17);assert.equal(r.data.materials[0].totalCost,1700);assert.deepEqual(r.data.supplies,original.supplies);
for(const bad of [0,-1,1.5,'',null,NaN,Infinity,{},true])assert.throws(()=>M.change(original,'supplies',{...move,quantity:bad},options(original)));
assert.throws(()=>M.change(original,'supplies',{...move,to:'CDMX'},options(original)),/distinto/);
assert.throws(()=>M.change(original,'supplies',{...move,date:'2026-02-30'},options(original)),/fecha/);
assert.throws(()=>M.change(original,'supplies',{...move,purpose:''},options(original)),/para qué/);
assert.throws(()=>M.change(original,'supplies',{...move,lotId:'nonexistent'},options(original)),/lote/);
assert.throws(()=>M.change(original,'supplies',move,{...options(original),expectedSource:'stale'}),/cambiaron/);
r=M.change(original,'supplies',{...use,quantity:6400},options(original,'negative'));assert.equal(r.data.supplies[0].qty,-100);assert.equal(r.warnings.length,1);
// A thousand independent integer conservation / round-trip checks.
for(let i=1;i<=1000;i++){
 const qty=i*3+1,cost=(i*11+1)/100,n=(i%(qty-1))+1,s={lots:[],moves:[],supplies:[{name:'Unit',loc:'CDMX',qty,totalCost:cost}]};
 let r=M.change(s,'supplies',{...move,quantity:n,status:'received'},options(s,'random-'+i));
 assert.equal(r.data.supplies.reduce((s,r)=>s+r.qty,0),qty);
 assert.equal(r.data.supplies.reduce((s,r)=>s+Math.round(r.totalCost*100),0),Math.round(cost*100));
 let c=M.change(r.data,'supplies',null,{...options(r.data,'random-'+i),action:'cancel'});
 assert.equal(c.data.supplies[0].qty,qty);assert.equal(c.data.supplies[0].totalCost,cost);
}
let I=require('../inventory-core.js');for(const module of ['commerce-core','simple-core','corrections-core'])I=require('../'+module+'.js')(I);
r=M.change(original,'supplies',move,options(original,'report'));const report=require('../executive-core.js').build(r.data,I);assert(report.sections.some(s=>s.title==='Insumos y marketing en tránsito'));
const projected=require('../partner-report.cjs').buildPartnerReport(r.data,require('node:path').resolve(__dirname,'..'));assert(projected.sections.some(s=>s.title==='Insumos y marketing en tránsito'));
if(process.env.EB_MATERIAL_FIXTURE)require('node:fs').writeFileSync(process.env.EB_MATERIAL_FIXTURE,base);
console.log('PASS MATERIAL MOVEMENTS: 6300 - 2100 = 4200; 700ml - 500; transfers preserve total quantity/value; transit/receipt/use; edit/cancel/restore; 1000 round trips; unknown costs; exact retries; stale writes; independent lots, permissions projection and reports.');
