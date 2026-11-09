'use strict';
/* Private document files live in the existing persistent SQLite database, never public/ or localStorage. */
const crypto=require('node:crypto'),path=require('node:path');
const CATEGORIES=['Certificados','Análisis de laboratorio','Asambleas','Acta constitutiva','IMPI'];
const FILE_LIMIT=10*1024*1024,STORAGE_LIMIT=500*1024*1024;
const MIME={'.pdf':'application/pdf','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp','.heic':'image/heic','.heif':'image/heif','.doc':'application/msword','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','.xls':'application/vnd.ms-excel','.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'};
const fields='id,title,category,lot,expiry,notes,filename,mime,size,sha256,revision,created,updated,actor,deleted';
const err=(status,message)=>Object.assign(Error(message),{status});
function metadata(input){
 if(!input||typeof input!=='object'||Array.isArray(input))throw err(400,'Revisa los datos del documento.');
 const text=(k,max)=>{const v=String(input[k]??'').trim();if(v.length>max||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(v))throw err(400,'Revisa el campo '+k+'.');return v;};
 const m={title:text('title',160),category:text('category',80),lot:text('lot',160),expiry:text('expiry',10),notes:text('notes',2000)};
 if(!m.title)throw err(400,'Escribe el nombre del documento.');
 if(!CATEGORIES.includes(m.category))throw err(400,'Elige una categoría del menú.');
 if(m.expiry&&(!/^\d{4}-\d{2}-\d{2}$/.test(m.expiry)||!Number.isFinite(Date.parse(m.expiry+'T12:00:00Z'))||new Date(m.expiry+'T12:00:00Z').toISOString().slice(0,10)!==m.expiry))throw err(400,'La fecha de vencimiento no es válida.');
 return m;
}
function file(input){
 const filename=String(input.filename||'').normalize('NFC').trim();
 if(!filename||filename.length>180||/[\x00-\x1f\x7f/\\:]/.test(filename)||filename.startsWith('.'))throw err(400,'El nombre del archivo no es válido.');
 const ext=path.extname(filename).toLowerCase();if(!MIME[ext])throw err(400,'Usa PDF, imagen, Word o Excel.');
 const b64=input.base64;if(typeof b64!=='string'||b64.length>Math.ceil(FILE_LIMIT/3)*4||!b64.length||b64.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(b64))throw err(400,'El archivo no es válido o supera 10 MB.');
 const bytes=Buffer.from(b64,'base64');if(!bytes.length||bytes.length>FILE_LIMIT||bytes.toString('base64')!==b64)throw err(400,'El archivo no es válido o supera 10 MB.');
 const head=bytes.subarray(0,16),hex=head.toString('hex');let valid=false;
 if(ext==='.pdf')valid=bytes.subarray(0,5).toString()==='%PDF-';
 if(['.jpg','.jpeg'].includes(ext))valid=hex.startsWith('ffd8ff');
 if(ext==='.png')valid=hex.startsWith('89504e470d0a1a0a');
 if(ext==='.webp')valid=head.subarray(0,4).toString()==='RIFF'&&head.subarray(8,12).toString()==='WEBP';
 if(['.heic','.heif'].includes(ext))valid=head.subarray(4,8).toString()==='ftyp'&&['heic','heix','hevc','hevx','mif1','msf1'].includes(head.subarray(8,12).toString());
 if(['.doc','.xls'].includes(ext))valid=hex.startsWith('d0cf11e0a1b11ae1');
 if(['.docx','.xlsx'].includes(ext))valid=hex.startsWith('504b0304')&&bytes.includes(Buffer.from('[Content_Types].xml'))&&bytes.includes(Buffer.from(ext==='.docx'?'word/document.xml':'xl/workbook.xml'));
 if(!valid)throw err(400,'El contenido no corresponde a la extensión. Revisa el archivo.');
 return{filename,mime:MIME[ext],size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes};
}
function createDocuments({db,auth,csrf,json,body}){
 db.exec(`CREATE TABLE IF NOT EXISTS document_files(id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,lot TEXT NOT NULL,expiry TEXT NOT NULL,notes TEXT NOT NULL,filename TEXT NOT NULL,mime TEXT NOT NULL,size INTEGER NOT NULL,sha256 TEXT NOT NULL,bytes BLOB NOT NULL,revision INTEGER NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL,actor TEXT NOT NULL,deleted INTEGER NOT NULL DEFAULT 0);
 CREATE TABLE IF NOT EXISTS document_events(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id TEXT NOT NULL,action TEXT NOT NULL,at TEXT NOT NULL,actor TEXT NOT NULL,before_json TEXT,after_json TEXT NOT NULL);
 CREATE INDEX IF NOT EXISTS document_category ON document_files(category,deleted);`);
 const get=id=>db.prepare('SELECT '+fields+' FROM document_files WHERE id=?').get(id);
 const used=()=>db.prepare('SELECT COALESCE(SUM(size),0) AS n FROM document_files').get().n;
 const audit=(id,action,actor,before,after)=>db.prepare('INSERT INTO document_events(document_id,action,at,actor,before_json,after_json) VALUES(?,?,?,?,?,?)').run(id,action,new Date().toISOString(),actor,before?JSON.stringify(before):null,JSON.stringify(after));
 function revision(input,row){if(!Number.isSafeInteger(input.revision)||input.revision!==row.revision)throw err(409,'Otra persona modificó este documento. Actualiza la lista antes de guardar.');}
 return async function handle(req,res,url){
  if(url.pathname!=='/api/documents'&&!url.pathname.startsWith('/api/documents/'))return false;
  const s=auth(req);if(s.user.role!=='editor')throw err(403,'EB2 solo puede consultar el reporte para socios.');const match=/^\/api\/documents\/([0-9a-f-]{36})(?:\/(file|restore))?$/.exec(url.pathname);
  if(url.pathname!=='/api/documents'&&!match)throw err(404,'Documento no encontrado.');
  const id=match?.[1],action=match?.[2];
  if(['GET','HEAD'].includes(req.method)){
   if(!id){
    const trash=url.searchParams.get('trash')==='1';if(trash&&s.user.role!=='editor')throw err(403,'La papelera requiere acceso EB1.');
    const docs=db.prepare('SELECT '+fields+' FROM document_files WHERE deleted=? ORDER BY updated DESC,id').all(trash?1:0);
    json(res,200,{documents:docs,categories:CATEGORIES,usedBytes:used(),storageLimit:STORAGE_LIMIT,fileLimit:FILE_LIMIT});return true;
   }
   const doc=get(id);if(!doc||doc.deleted)throw err(404,'Documento no disponible.');
   if(action!=='file'){if(action)throw err(405,'Método no permitido.');json(res,200,{document:doc});return true;}
   const bytes=Buffer.from(db.prepare('SELECT bytes FROM document_files WHERE id=?').get(id).bytes);
   const inline=url.searchParams.get('inline')==='1'&&['application/pdf','image/jpeg','image/png','image/webp'].includes(doc.mime);
   const safe=doc.filename.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^A-Za-z0-9._ -]/g,'_');
   const encoded=encodeURIComponent(doc.filename).replace(/[!'()*]/g,c=>'%'+c.charCodeAt(0).toString(16).toUpperCase());
   const headers={'Content-Type':doc.mime,'Content-Disposition':(inline?'inline':'attachment')+'; filename="'+safe+'"; filename*=UTF-8\'\''+encoded,'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'",'Referrer-Policy':'no-referrer','Accept-Ranges':'bytes'};
   let start=0,end=bytes.length-1,code=200;
   if(req.headers.range){const r=/^bytes=(\d*)-(\d*)$/.exec(req.headers.range);if(!r||(!r[1]&&!r[2]))throw err(416,'Rango no válido.');if(!r[1])start=Math.max(0,bytes.length-Number(r[2]));else{start=Number(r[1]);if(r[2])end=Math.min(end,Number(r[2]));}if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>end||start>=bytes.length)throw err(416,'Rango no válido.');code=206;headers['Content-Range']='bytes '+start+'-'+end+'/'+bytes.length;}
   headers['Content-Length']=end-start+1;res.writeHead(code,headers);req.method==='HEAD'?res.end():res.end(bytes.subarray(start,end+1));return true;
  }
  csrf(req,s);if(s.user.role!=='editor')throw err(403,'EB2 solo permite consultar y descargar documentos.');
  if(!['POST','PATCH','DELETE'].includes(req.method))throw err(405,'Método no permitido.');
  const input=await body(req,!id?15*1024*1024:16*1024);if(!input||typeof input!=='object'||Array.isArray(input))throw err(400,'Revisa los datos del documento.');const stamp=new Date().toISOString(),actor=s.user.username;
  if(!id&&req.method==='POST'){
   if(typeof input.id!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(input.id))throw err(400,'Falta la referencia del archivo.');
   const m=metadata(input),f=file(input),prior=get(input.id);
   if(prior){if(prior.sha256!==f.sha256||Object.keys(m).some(k=>m[k]!==prior[k])||prior.filename!==f.filename||prior.deleted)throw err(409,'Esa referencia de archivo ya se utilizó.');json(res,200,{document:prior,repeated:true});return true;}
   db.exec('BEGIN IMMEDIATE');
   try{
    if(used()+f.size>STORAGE_LIMIT)throw err(413,'El archivo documental alcanzó su límite de 500 MB. No se guardó ni se borró nada.');
    if(db.prepare('SELECT COUNT(*) AS n FROM document_files').get().n>=5000)throw err(413,'Se alcanzó el límite de documentos.');
    db.prepare('INSERT INTO document_files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)').run(input.id,m.title,m.category,m.lot,m.expiry,m.notes,f.filename,f.mime,f.size,f.sha256,f.bytes,1,stamp,stamp,actor);
    const saved=get(input.id);audit(input.id,'create',actor,null,saved);db.exec('COMMIT');json(res,201,{document:saved});return true;
   }catch(e){db.exec('ROLLBACK');throw e;}
  }
  if(!id)throw err(405,'Método no permitido.');
  if(action&&action!=='restore')throw err(405,'Método no permitido.');
  if(action==='restore'&&req.method!=='POST'||!action&&!['PATCH','DELETE'].includes(req.method))throw err(405,'Método no permitido.');
  db.exec('BEGIN IMMEDIATE');
  try{
   const row=get(id);if(!row)throw err(404,'Documento no encontrado.');revision(input,row);
   if(action==='restore'){
    if(!row.deleted)throw err(409,'El documento ya está disponible.');
    db.prepare('UPDATE document_files SET deleted=0,revision=revision+1,updated=?,actor=? WHERE id=?').run(stamp,actor,id);
   }else{
    if(row.deleted)throw err(409,'El documento está en la papelera.');
    if(req.method==='DELETE')db.prepare('UPDATE document_files SET deleted=1,revision=revision+1,updated=?,actor=? WHERE id=?').run(stamp,actor,id);
    else{const m=metadata(input);db.prepare('UPDATE document_files SET title=?,category=?,lot=?,expiry=?,notes=?,revision=revision+1,updated=?,actor=? WHERE id=?').run(m.title,m.category,m.lot,m.expiry,m.notes,stamp,actor,id);}
   }
   const saved=get(id);audit(id,action==='restore'?'restore':req.method==='DELETE'?'delete':'update',actor,row,saved);db.exec('COMMIT');json(res,200,{document:saved});return true;
  }catch(e){db.exec('ROLLBACK');throw e;}
 };
}
module.exports={createDocuments,metadata,file,CATEGORIES,FILE_LIMIT,STORAGE_LIMIT};
