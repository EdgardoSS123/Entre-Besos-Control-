"""Real HTTP server + slow proxy + disposable SQLite. No production requests."""
import json, os, shutil, subprocess, tempfile, time, urllib.request, uuid, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path.cwd();BASE='http://127.0.0.1:8849/';OUT=Path('/tmp/eb-slow-save');OUT.mkdir(exist_ok=True,parents=True)
public=Path(tempfile.mkdtemp(prefix='eb-slow-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.html','.js','.css','.jpg','.png','.webmanifest']:shutil.copy(f,public/f.name)
shutil.copy(ROOT/'control.html',public/'index.html')
for name in ['vendor','icons']:shutil.copytree(ROOT/name,public/name)
seed={'lots':[],'moves':[],'contacts':[{'name':'Synthetic preserved contact'}],'materials':[{'name':'Synthetic material','qty':7}],'supplies':[],'partnerOrders':[]}
code=r"""
const http=require('node:http'),crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createApp}=require('./server.cjs');
const salt='43'.repeat(16),hash=crypto.scryptSync('slow-test-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');
const users=[{username:'synthetic-editor',name:'Synthetic EB1',role:'editor',salt,hash},{username:'synthetic-reader',name:'Synthetic EB2',role:'reader',salt,hash}];
const app=createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-slow-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8849'],secure:false});
let mode={delay:0,drop:false},stats={puts:0,receipts:0};
app.server.listen(0,'127.0.0.1',()=>{
 http.createServer(async(req,res)=>{
  if(req.url==='/__stats'){res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify(stats));return;}
  const chunks=[];for await(const b of req)chunks.push(b);const bytes=Buffer.concat(chunks);
  if(req.url==='/__control'){mode={delay:0,drop:false,...JSON.parse(bytes)};stats={puts:0,receipts:0};res.writeHead(200,{'content-type':'application/json'});res.end('{}');return;}
  const put=req.method==='PUT'&&req.url==='/api/state';if(put)stats.puts++;if(req.url.startsWith('/api/state/receipt'))stats.receipts++;
  const delay=put?mode.delay:0,drop=put&&mode.drop;if(drop)mode.drop=false;
  setTimeout(()=>{
   const upstream=http.request({host:'127.0.0.1',port:app.server.address().port,path:req.url,method:req.method,headers:req.headers},reply=>{
    if(drop){reply.resume();reply.on('end',()=>{res.writeHead(503,{'content-type':'application/json'});res.end(JSON.stringify({error:'Synthetic gateway lost the commit acknowledgement'}));});return;}
    if(res.destroyed){reply.resume();return;}
    res.writeHead(reply.statusCode,reply.headers);reply.pipe(res);
   });upstream.on('error',()=>{if(!res.destroyed){res.writeHead(502);res.end();}});upstream.end(bytes);
  },delay);
 }).listen(8849,'127.0.0.1');
});
"""
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(public)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for _ in range(80):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def login(ctx,user='synthetic-editor'):
 r=ctx.request.post(BASE+'api/login',data={'username':user,'password':'slow-test-only'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
def read(ctx):
 r=ctx.request.get(BASE+'api/state');assert r.ok,r.text();return r.json()
def ready(p):p.wait_for_function("()=>window.EBShared&&!EBShared.pending&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=45000)
def fill(p,name):
 p.locator('#supplier-new').click();p.locator('#supplier-name').fill(name);p.locator('#supplier-item').select_option('Tapones');p.locator('#supplier-place').fill('OAXACA');p.locator('#supplier-dialog .supplier-notes summary').click();p.locator('#supplier-notes').fill('SYNTHETIC - slow confirmation regression')
def control(ctx,**kw):assert ctx.request.post(BASE+'__control',data=kw).ok
def stats(ctx):return ctx.request.get(BASE+'__stats').json()
def closed(p):expect(p.locator('#supplier-dialog')).to_have_count(0,timeout=45000);ready(p)
try:
 with sync_playwright() as pw:
  engine=os.environ.get('EB_BROWSER','chromium');browser=getattr(pw,engine).launch(**({'executable_path':shutil.which('google-chrome') or shutil.which('chromium'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  ctx=browser.new_context(viewport={'width':390 if engine=='webkit' else 1440,'height':900},has_touch=engine=='webkit',is_mobile=engine=='webkit')
  token=login(ctx);r=ctx.request.put(BASE+'api/state',data={'revision':0,'operation':str(uuid.uuid4()),'initialize':True,'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert r.ok,r.text()
  page=ctx.new_page();page.on('dialog',lambda d:d.accept());errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'suppliers.html');ready(page);fill(page,'Synthetic supplier: 22-second save');control(ctx,delay=22000)
  page.locator('#supplier-save').click()
  if os.environ.get('EB_EXPECT_SLOW_BROKEN')=='1':
   expect(page.locator('#supplier-error')).to_contain_text('no se confirmó',timeout=21000)
   assert page.evaluate('EBShared.pending');expect(page.locator('#supplier-dialog')).to_be_visible()
   page.screenshot(path=str(OUT/'before-15s-cutoff.png'),full_page=True)
   print('REPRODUCED LIVE TIMING: 22-second save aborts at old 15-second cutoff; supplier stays pending and window cannot close.',flush=True)
  else:
   page.wait_for_timeout(16000);expect(page.locator('#supplier-dialog')).to_be_visible();expect(page.locator('#supplier-save')).to_be_disabled();assert not read(ctx)['data'].get('suppliers')
   assert stats(ctx)['puts']==1,'No duplicate upload while waiting'
   closed(page);one=read(ctx);assert len(one['data']['suppliers'])==1 and one['revision']==2 and stats(ctx)['puts']==1
   assert not page.evaluate('localStorage.getItem("eb-shared-outbox-v1")')
   for k in seed:assert one['data'][k]==seed[k],k
   page.screenshot(path=str(OUT/(engine+'-saved-after-22s.png')),full_page=True)
   print('PASS real 22-second HTTP delay: no premature timeout, exactly one save, confirmed cloud record, automatic return.',flush=True)
   control(ctx);page.locator('#supplier-filter').select_option('Tapones');page.locator('#supplier-search').fill('22-second');page.locator('[data-supplier-edit]').click();page.locator('#supplier-contact').fill('Synthetic updated contact');page.locator('#supplier-save').click();closed(page)
   expect(page.locator('#supplier-search')).to_have_value('22-second');expect(page.locator('#supplier-filter')).to_have_value('Tapones');assert len(read(ctx)['data']['suppliers'])==1
   page.locator('#supplier-search').fill('');page.locator('#supplier-filter').select_option('')
   control(ctx,drop=True);fill(page,'Synthetic supplier: lost reply');page.locator('#supplier-save').click();closed(page)
   two=read(ctx);assert len(two['data']['suppliers'])==2 and stats(ctx)['puts']==1 and stats(ctx)['receipts']>=2
   print('PASS server commits but reply is lost: authenticated receipt confirms it, no second upload, no duplicate.',flush=True)
   control(ctx);now=read(ctx);raw=json.dumps(now['data'],ensure_ascii=False,separators=(',',':'));op=str(uuid.uuid4())
   ack=ctx.request.put(BASE+'api/state',data={'revision':now['revision'],'operation':op,'data':now['data']},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert ack.ok
   pending={'revision':now['revision'],'operation':op,'raw':raw}
   page.evaluate('(pending)=>{localStorage.setItem("eb-shared-outbox-v1",JSON.stringify(pending));}',pending)
   control(ctx);page.reload();ready(page);assert stats(ctx)['puts']==0 and stats(ctx)['receipts']>=1
   assert read(ctx)['revision']==ack.json()['revision'];assert not page.evaluate('EBShared.pending')
   assert len(read(ctx)['data']['suppliers'])==2
   print('PASS old pending outbox: recovers an already stored operation on reload without another PUT or lost records.',flush=True)
   receipt=ctx.request.get(BASE+'api/state/receipt?operation='+op);assert receipt.ok;rr=receipt.json();assert rr['found'] and set(rr)=={'found','revision','hash','updated'}
   assert rr['hash']==hashlib.sha256(raw.encode()).hexdigest()
   assert ctx.request.get(BASE+'api/state/receipt?operation='+str(uuid.uuid4())).json()=={'found':False}
   assert ctx.request.get(BASE+'api/state/receipt?operation=invalid').status==400
   reader=browser.new_context();login(reader,'synthetic-reader');assert reader.request.get(BASE+'api/state/receipt?operation='+op).status==403;reader.close()
   anon=browser.new_context();assert anon.request.get(BASE+'api/state/receipt?operation='+op).status==401;anon.close()
   final=read(ctx)['data'];assert len(final['suppliers'])==2
   for k in seed:assert final[k]==seed[k],k
   assert not errors,errors
   print('PASS '+engine+': cloud confirmation, edit return, legacy pending recovery, exact hash, EB1/EB2/anonymous permissions and unrelated data preservation.',flush=True)
  ctx.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
