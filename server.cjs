'use strict';
/* Single shared workspace. Credentials live in environment, data on a persistent volume. */
const http=require('node:http'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {DatabaseSync}=require('node:sqlite');
const {promisify}=require('node:util'),scrypt=promisify(crypto.scrypt);
const MAX=12*1024*1024,COOKIE='eb_session',now=()=>Date.now(),digest=x=>crypto.createHash('sha256').update(x).digest('hex');
function error(status,message){return Object.assign(Error(message),{status});}
function parseState(d){if(!d||typeof d!=='object'||Array.isArray(d)||!Array.isArray(d.lots)||!Array.isArray(d.moves))throw error(400,'Formato de datos no válido; no se modificó la base.');return JSON.stringify(d);}
function createApp(options={}){
 const root=path.resolve(options.root||process.env.EB_PUBLIC_DIR||path.join(__dirname,'public'));
 const folder=options.folder||process.env.EB_DATA_DIR;
 if(!folder)throw Error('EB_DATA_DIR is required; refusing ephemeral storage.');
 if(process.env.RAILWAY_ENVIRONMENT_ID&&!process.env.RAILWAY_VOLUME_MOUNT_PATH)throw Error('Persistent volume required.');
 fs.mkdirSync(folder,{recursive:true,mode:0o700});
 const users=options.users||JSON.parse(process.env.EB_USERS_JSON||'[]');
 if(!Array.isArray(users)||!users.length||users.some(u=>!u.username||!['editor','reader'].includes(u.role)||!/^([0-9a-f]{32})$/.test(u.salt)||!/^([0-9a-f]{128})$/.test(u.hash)))throw Error('Valid server-side users are required.');
 const origins=options.origins||[process.env.EB_ORIGIN||'https://entre-besos-web-production.up.railway.app'];
 const secure=options.secure??true, db=new DatabaseSync(path.join(folder,'entre-besos.sqlite'));
 db.exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;
 CREATE TABLE IF NOT EXISTS workspace(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,payload TEXT,updated TEXT,actor TEXT);
 INSERT OR IGNORE INTO workspace VALUES(1,0,NULL,NULL,NULL);
 CREATE TABLE IF NOT EXISTS revisions(revision INTEGER PRIMARY KEY,payload TEXT NOT NULL,updated TEXT NOT NULL,actor TEXT NOT NULL,operation TEXT UNIQUE NOT NULL,hash TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,username TEXT NOT NULL,csrf TEXT NOT NULL,expires INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS attempts(bucket TEXT PRIMARY KEY,n INTEGER NOT NULL,expires INTEGER NOT NULL);`);
 const getState=()=>db.prepare('SELECT revision,payload,updated,actor FROM workspace WHERE id=1').get();
 const json=(res,status,value,headers={})=>{const raw=JSON.stringify(value);res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin',...headers});res.end(raw);};
 const body=async(req,limit=MAX)=>{if(!String(req.headers['content-type']||'').startsWith('application/json'))throw error(415,'Se requiere JSON.');let size=0,chunks=[];for await(const chunk of req){size+=chunk.length;if(size>limit)throw error(413,'El archivo supera el límite permitido; no se guardó.');chunks.push(chunk);}try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw error(400,'JSON no válido.');}};
 const session=req=>{const token=String(req.headers.cookie||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(COOKIE+'='))?.slice(COOKIE.length+1);if(!token||!/^[0-9a-f]{64}$/.test(token))return null;const s=db.prepare('SELECT * FROM sessions WHERE token=? AND expires>?').get(digest(token),now());if(!s)return null;const u=users.find(x=>x.username.toLowerCase()===s.username);return u?{...s,user:{username:u.username,name:u.name||u.username,role:u.role}}:null;};
 const origin=req=>{if(!origins.includes(String(req.headers.origin||'')))throw error(403,'Origen no permitido.');};
 const auth=req=>{const s=session(req);if(!s)throw error(401,'Inicia sesión para ver la información compartida.');return s;};
 const csrf=(req,s)=>{origin(req);if(req.headers['x-eb-csrf']!==s.csrf)throw error(403,'La sesión debe actualizarse.');};
 const attempt=(bucket,limit)=>{const r=db.prepare('SELECT * FROM attempts WHERE bucket=? AND expires>?').get(bucket,now());if(r&&r.n>=limit)throw error(429,'Demasiados intentos. Espera 15 minutos e inténtalo de nuevo.');db.prepare('INSERT INTO attempts VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET n=CASE WHEN expires>? THEN n+1 ELSE 1 END,expires=CASE WHEN expires>? THEN expires ELSE excluded.expires END').run(bucket,now()+15*60e3,now(),now());};
 const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webmanifest':'application/manifest+json','.svg':'image/svg+xml'};
 const documents=require('./documents-store.cjs').createDocuments({db,auth,csrf,json,body});
 const handler=async(req,res)=>{try{
  const url=new URL(req.url,'http://internal'),route=url.pathname;
  if(route==='/healthz'){db.prepare('SELECT revision FROM workspace').get();return json(res,200,{ok:true,shared:true,version:'shared-v1'});}
  if(route==='/api/session'&&req.method==='GET'){const s=session(req);return json(res,200,s?{authenticated:true,user:s.user,csrf:s.csrf}:{authenticated:false});}
  if(route==='/api/login'&&req.method==='POST'){
   origin(req);const input=await body(req),username=String(input.username||'').trim().toLowerCase(),password=String(input.password||'');
   if(username.length>100||password.length>128)throw error(400,'Revisa usuario y contraseña.');
   attempt('u:'+digest(username),10);attempt('ip:'+digest(req.socket.remoteAddress||'shared'),100);
   const u=users.find(x=>x.username.toLowerCase()===username),fallback=users[0];
   const hash=await scrypt(password,Buffer.from((u||fallback).salt,'hex'),64,{N:32768,r:8,p:1,maxmem:64*1024*1024});
   if(!u||!crypto.timingSafeEqual(hash,Buffer.from(u.hash,'hex')))throw error(401,'Usuario o contraseña incorrectos.');
   db.prepare('DELETE FROM attempts WHERE bucket=?').run('u:'+digest(username));
   const token=crypto.randomBytes(32).toString('hex'),c=crypto.randomBytes(24).toString('hex'),ttl=input.remember===false?12*3600e3:30*86400e3;
   db.prepare('DELETE FROM sessions WHERE expires<?').run(now());db.prepare('INSERT INTO sessions VALUES(?,?,?,?)').run(digest(token),username,c,now()+ttl);
   return json(res,200,{authenticated:true,user:{username:u.username,name:u.name||u.username,role:u.role},csrf:c},{'Set-Cookie':`${COOKIE}=${token}; Path=/; HttpOnly; SameSite=Strict${secure?'; Secure':''}${input.remember===false?'':'; Max-Age='+Math.floor(ttl/1000)}`});
  }
  if(route==='/api/logout'&&req.method==='POST'){const s=auth(req);csrf(req,s);db.prepare('DELETE FROM sessions WHERE token=?').run(s.token);return json(res,200,{ok:true},{'Set-Cookie':`${COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0${secure?'; Secure':''}`});}
  if(route==='/api/state'&&req.method==='GET'){auth(req);const row=getState();if(url.searchParams.get('since')===String(row.revision))return json(res,200,{unchanged:true,revision:row.revision});return json(res,200,{revision:row.revision,data:row.payload?JSON.parse(row.payload):null,updated:row.updated,actor:row.actor});}
  if(route==='/api/state'&&req.method==='PUT'){
   const s=auth(req);csrf(req,s);if(s.user.role!=='editor')throw error(403,'EB2 tiene acceso solo de consulta.');
   const input=await body(req),payload=parseState(input.data),op=String(input.operation||''),hash=digest(payload);
   if(!Number.isSafeInteger(input.revision)||input.revision<0||!/^[a-zA-Z0-9_-]{16,100}$/.test(op))throw error(400,'Falta la versión o referencia del guardado.');
   db.exec('BEGIN IMMEDIATE');let row;
   try{
    const prior=db.prepare('SELECT revision,hash FROM revisions WHERE operation=?').get(op);
    if(prior){if(prior.hash!==hash)throw error(409,'Referencia de guardado duplicada.');db.exec('COMMIT');return json(res,200,{ok:true,revision:prior.revision});}
    row=getState();if(input.revision!==row.revision)throw error(409,'Otro dispositivo guardó cambios. Se conservó tu captura, sin sobrescribir la base compartida.');
    if(!row.payload&&input.initialize!==true)throw error(409,'Primero conecta la PC con tus datos actuales.');
    if(!row.payload&&!Object.values(input.data).some(v=>Array.isArray(v)&&v.length))throw error(400,'No se publicará una base vacía.');
    const updated=new Date().toISOString(),rev=row.revision+1;
    db.prepare('INSERT INTO revisions VALUES(?,?,?,?,?,?)').run(rev,payload,updated,s.user.username,op,hash);
    db.prepare('UPDATE workspace SET revision=?,payload=?,updated=?,actor=? WHERE id=1').run(rev,payload,updated,s.user.username);
    db.prepare('DELETE FROM revisions WHERE revision>1 AND revision<?').run(Math.max(1,rev-99));
    db.exec('COMMIT');return json(res,200,{ok:true,revision:rev,updated});
   }catch(e){try{db.exec('ROLLBACK');}catch{}throw e;}
  }
  if(await documents(req,res,url))return;
  if(route.startsWith('/api/'))throw error(404,'No encontrado.');
  if(!['GET','HEAD'].includes(req.method))throw error(405,'Método no permitido.');
  let relative;try{relative=decodeURIComponent(route);}catch{throw error(400,'Ruta no válida.');}
  if(relative==='/'||relative==='/index.html')relative='/index.html';
  const target=path.resolve(root,'.'+relative),ext=path.extname(target);
  if(!target.startsWith(root+path.sep)||!types[ext]||relative.split('/').some(x=>x.startsWith('.')))throw error(404,'No encontrado.');
  let stat;try{stat=fs.statSync(target);}catch{throw error(404,'No encontrado.');}if(!stat.isFile())throw error(404,'No encontrado.');
  res.writeHead(200,{'Content-Type':types[ext],'Content-Length':stat.size,'Cache-Control':ext==='.html'?'no-store':'no-cache','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','X-Frame-Options':'DENY'});if(req.method==='HEAD')res.end();else fs.createReadStream(target).pipe(res);
 }catch(e){if(!res.headersSent)json(res,e.status||500,{error:e.status?e.message:'No se pudo completar la operación. Tus registros anteriores se conservan.'});else res.end();}};
 const server=http.createServer(handler);server.requestTimeout=30000;server.headersTimeout=15000;
 return {server,db,close:()=>{server.close();db.close();}};
}
module.exports={createApp,parseState};
if(require.main===module){const app=createApp();app.server.listen(Number(process.env.PORT||80),'0.0.0.0',()=>console.log('Entre Besos shared store ready'));process.on('SIGTERM',()=>app.server.close(()=>{app.db.close();process.exit(0);}));}
