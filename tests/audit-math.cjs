'use strict';
const A=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let I=require('../inventory-core.js');for(const f of ['commerce-core','simple-core','corrections-core'])I=require('../'+f+'.js')(I);
const O=require('../orders-core.js'),P=require('../packaging.js');
let seed=84019;function rand(n){seed=(seed*1664525+1013904223)>>>0;return seed%n;}
const source=fs.readFileSync('control.js','utf8');function range(a,b){return source.slice(source.indexOf(a),source.indexOf(b,source.indexOf(a)));}
const C=vm.runInNewContext(range('const PRODUCTS=','const ICONS=')+"const today=()=> '2026-11-09';"+range('function blank()','try{const d=JSON.parse(localStorage.getItem(DRAFT)')+range('function production(d)','function readDraft(')+range('function calc(d)','function saveDraft(')+'({blank,calc,production})');
let cases=0,assertions=0;function eq(a,b,msg){assertions++;A.equal(a,b,msg);}
for(let k=0;k<2000;k++){
 const ml=[50,375,700,720,730,750,1000][rand(7)],gross=1000+rand(6000000),loss=rand(Math.min(gross,50000));
 const d=C.blank();Object.assign(d,{ml,producedLiters:gross/1000,lossLiters:loss/1000,liquid:rand(100000)/100});d.lines=d.lines.map(r=>({...r,amount:0}));
 const p=C.production(d),n=Number(BigInt(gross-loss)/BigInt(ml));eq(p.n,n);eq(Math.round(p.remainder*1000),gross-loss-n*ml);if(n>0){const cost=C.calc(d);A(Math.abs(cost.total-(n*ml+loss)/1000*d.liquid)<1e-6);assertions++;}
 const qty=rand(1000000),pack=I.pack(qty);eq(pack.full*480+pack.half*240+pack.boxes*6+pack.bottles,qty);eq(I.quantity('2.5','pallet'),1200);cases++;
}
for(let k=0;k<300;k++){
 const day='2026-11-09',stamp=day+'T18:00:00Z',n=500+rand(3000);let d={lots:[{id:'AUD',p:0,bottles:n,ml:720,unitCost:200,totalCost:n*200}],moves:[]};d=I.initializeOrigin(d,'AUD','Oaxaca',day,stamp);
 const moved=1+rand(200),sold=1+rand(30),sample=1+rand(12),ordered=1+rand(40);d=I.moveStock(d,'AUD',{id:'mv',from:'Oaxaca',to:'CDMX',tag:'Por clasificar',amount:moved,unit:'bottle',cost:0,currency:'MXN',stamp},day);
 eq(I.balance(d,'AUD').total,n,'Transfer conserves stock');
 d=I.sellStock(d,'AUD',{id:'sl',from:'CDMX',tag:'Por clasificar',amount:sold,unit:'bottle',price:'850',priceBasis:'bottle',currency:'MXN',customer:'Test',payment:'pending',stamp},day);
 eq(d.lotSales[0].totalCents,sold*85000);d=I.deliverSamples(d,'AUD',{id:'sm',from:'CDMX',tag:'Por clasificar',amount:sample,unit:'bottle',stockType:'commercial',stamp,notes:'test'},day);
 let opt={id:'ord',operation:'audit-'+k+'-add',day,stamp,actor:'test'};let r=O.save(d,{partner:'edgardo',customer:'Test',from:'Oaxaca',date:day,status:'delivered',lines:[{product:0,lotId:'AUD',amount:ordered,unit:'bottle'}]},opt,I);d=r.data;
 let b=I.reconciliation(d,'AUD');eq(b.total,n-sold-sample-ordered);eq(b.unexplained,0);eq(O.save(d,{...r.order}, {...opt,expected:JSON.stringify(r.order),operation:'nochange'},I).unchanged,true);
 opt={...opt,operation:'audit-'+k+'-delete',expected:JSON.stringify(r.order),action:'delete'};r=O.save(d,null,opt,I);d=r.data;eq(I.balance(d,'AUD').total,n-sold-sample);
 r=O.save(d,null,{...opt,operation:'audit-'+k+'-restore',expected:JSON.stringify(r.order),action:'restore'},I);d=r.data;eq(r.order.status,'pending');eq(I.balance(d,'AUD').total,n-sold-sample);
 r=O.setStatus(d,'ord','delivered',{...opt,action:'save',operation:'audit-'+k+'-deliver',expected:JSON.stringify(r.order)},I);d=r.data;eq(I.balance(d,'AUD').total,n-sold-sample-ordered);
 d=I.removeRecord(d,'AUD','sale','sl',JSON.stringify(d.lotSales[0]),{id:'delete-sale',stamp});eq(I.balance(d,'AUD').total,n-sample-ordered);eq(I.reconciliation(d,'AUD').unexplained,0);cases++;
}
console.log(JSON.stringify({suite:'independent-math',cases,assertions,status:'PASS'}));
