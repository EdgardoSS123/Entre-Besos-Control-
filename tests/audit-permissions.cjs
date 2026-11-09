'use strict';
const A=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {createApp}=require('../server.cjs');const origin='http://127.0.0.1:8798';
const salt='55'.repeat(16),password='isolated-audit-not-a-real-password',hash=crypto.scryptSync(password,Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');
const users=['esalazars','rsalazarm','msaenzc','socioEB2'].map((username,i)=>({username,role:i<3?'editor':'reader',salt,hash}));
async function main(){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'eb-audit-role-'));const app=createApp({folder:dir,root:path.join(__dirname,'..'),users,origins:[origin],secure:false});await new Promise(r=>app.server.listen(8798,'127.0.0.1',r));
 const call=async(route,method='GET',value,s)=>{const r=await fetch(origin+'/api/'+route,{method,headers:{'Content-Type':'application/json',Origin:origin,...(s?{Cookie:s.cookie,'X-EB-CSRF':s.csrf}:{})},...(value?{body:JSON.stringify(value)}:{})});return{status:r.status,body:await r.json(),cookie:r.headers.get('set-cookie')?.split(';')[0]};};
 try{
  const sessions=[];for(const u of users){const x=await call('login','POST',{username:u.username,password});A.equal(x.status,200);A.equal(x.body.user.role,u.role);sessions.push({cookie:x.cookie,csrf:x.body.csrf});}
  const B=sessions[3];const seed={lots:[{id:'AUDIT',p:0,bottles:120,ml:720,unitCost:100,totalCost:12000}],moves:[],contacts:[{name:'PRIVATE_CONTACT',email:'private@example.test',country:'USA'}],suppliers:[{name:'PRIVATE_SUPPLIER'}],partnerOrders:[],materials:[],supplies:[],expenses:[{type:'Gasto',amount:500,notes:'PRIVATE_NOTES'}],documents:[{title:'PRIVATE_DOCUMENT'}],lotSales:[]};
  const body={revision:0,initialize:true,operation:crypto.randomUUID(),data:seed};A.equal((await call('state','PUT',body,B)).status,403);A.equal((await call('state','PUT',body,sessions[0])).status,200);
  for(let i=0;i<3;i++){const r=await call('state','GET',null,sessions[i]);A.equal(r.status,200);r.body.data.contacts[0].phone=String(i);A.equal((await call('state','PUT',{revision:r.body.revision,operation:crypto.randomUUID(),data:r.body.data},sessions[i])).status,200);}
  for(const route of ['state','state?since=4','documents','documents?trash=1','documents/00000000-0000-4000-8000-000000000001/file'])A.equal((await call(route,'GET',null,B)).status,403,route);
  for(const [route,method] of [['state','PUT'],['documents','POST'],['documents/00000000-0000-4000-8000-000000000001','PATCH'],['documents/00000000-0000-4000-8000-000000000001','DELETE']])A.equal((await call(route,method,{},B)).status,403);
  A.equal((await call('partner-report')).status,401);const report=await call('partner-report','GET',null,B);A.equal(report.status,200,JSON.stringify(report.body));A.equal(report.body.data,undefined);A.equal(report.body.model.summary,undefined);
  const raw=JSON.stringify(report.body);for(const key of ['PRIVATE_CONTACT','PRIVATE_SUPPLIER','PRIVATE_NOTES','PRIVATE_DOCUMENT','private@example.test','paidCents','pendingCents','unknownPayment'])A(!raw.includes(key),key);
  for(const s of sessions.slice(0,3))A.deepEqual((await call('partner-report','GET',null,s)).body,report.body,'Same report for every account');
  const state=(await call('state','GET',null,sessions[0])).body;
  const results=await Promise.all(sessions.slice(0,3).map((s,i)=>call('state','PUT',{revision:state.revision,operation:crypto.randomUUID(),data:{...state.data,auditMarker:i}},s)));
  A.equal(results.filter(r=>r.status===200).length,1);A.equal(results.filter(r=>r.status===409).length,2);A.equal(app.db.prepare('PRAGMA quick_check').get().quick_check,'ok');
  console.log('PASS PERMISSIONS: 3 EB1 cross-edit; EB2 report-only; state/documents/files denied; safe report excludes private notes and collections; identical report; concurrent writes protected; SQLite integrity.');
 }finally{await new Promise(r=>app.server.close(r));app.db.close();fs.rmSync(dir,{recursive:true,force:true});}
}
main().catch(e=>{console.error(e);process.exit(1);});
