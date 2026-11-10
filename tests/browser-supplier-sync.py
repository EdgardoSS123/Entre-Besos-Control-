"""Disposable SQLite and synthetic contacts only. Never sends data to production."""
import json, os, shutil, subprocess, tempfile, time, urllib.request, uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path.cwd(); BASE='http://127.0.0.1:8819/'; OUT=Path('/tmp/eb-supplier-sync'); OUT.mkdir(exist_ok=True,parents=True)
public=Path(tempfile.mkdtemp(prefix='eb-sync-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.html','.js','.css','.jpg','.png','.webmanifest']:shutil.copy(f,public/f.name)
shutil.copy(ROOT/'control.html',public/'index.html')
for name in ['vendor','icons']:shutil.copytree(ROOT/name,public/name)
seed={'lots':[],'moves':[],'contacts':[{'name':'Conservar contacto'}],'materials':[{'name':'Conservar material','qty':4}],'supplies':[],'partnerOrders':[]}
code="const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='43'.repeat(16),hash=crypto.scryptSync('sync-test-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=[{username:'test-editor',name:'EB1 test',role:'editor',salt,hash},{username:'test-other',name:'Other EB1 test',role:'editor',salt,hash},{username:'test-reader',name:'EB2 test',role:'reader',salt,hash}];createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-sync-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8819'],secure:false}).server.listen(8819,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(public)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for _ in range(60):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def login(ctx,user='test-editor'):
 r=ctx.request.post(BASE+'api/login',data={'username':user,'password':'sync-test-only'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
def ready(page):page.wait_for_function("()=>window.EBShared&&!window.EBShared.pending&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=25000)
def fill(page,name):
 page.locator('#supplier-new').click();page.locator('#supplier-name').fill(name);page.locator('#supplier-item').select_option('Tapones');page.locator('#supplier-place').fill('Oaxaca');page.locator('#supplier-dialog .supplier-notes summary').click();page.locator('#supplier-notes').fill('PROVEEDOR DE PRUEBA AISLADA')
def closed(page):
 expect(page.locator('#supplier-dialog')).to_have_count(0,timeout=25000);ready(page)
def data(ctx):
 r=ctx.request.get(BASE+'api/state');assert r.ok,r.text();return r.json()['data']
try:
 with sync_playwright() as p:
  engine=os.environ.get('EB_BROWSER','chromium');b=getattr(p,engine).launch(**({'executable_path':shutil.which('chromium') or shutil.which('google-chrome'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  ctx=b.new_context(viewport={'width':390 if engine=='webkit' else 1440,'height':900},is_mobile=engine=='webkit',has_touch=engine=='webkit');token=login(ctx)
  r=ctx.request.put(BASE+'api/state',data={'revision':0,'operation':str(uuid.uuid4()),'initialize':True,'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert r.ok,r.text()
  page=ctx.new_page();page.on('dialog',lambda d:d.accept());errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'suppliers.html');ready(page);fill(page,'Proveedor sesión renovada')
  # Same-account login in another tab replaces the cookie, leaving this form's CSRF stale.
  login(ctx);page.locator('#supplier-save').click()
  if os.environ.get('EB_EXPECT_BROKEN')=='1':
   expect(page.locator('#supplier-error')).to_contain_text('vuelve a generar el PDF',timeout=25000)
   assert page.evaluate('EBShared.pending') and not data(ctx).get('suppliers')
   page.screenshot(path=str(OUT/'before-pending.png'),full_page=True)
   print('REPRODUCED: supplier remains local; stale same-account session produces screenshot error about PDF; server has no supplier.',flush=True)
  else:
   closed(page);saved=data(ctx);assert len(saved['suppliers'])==1
   expect(page.locator('.supplier-card')).to_contain_text('Proveedor sesión renovada')
   for k in seed:assert saved[k]==seed[k],k
   print('PASS same-account session renewal: one cloud supplier; form closes.',flush=True)
   # Multiple confirmation calls wait behind the same real browser lock.
   blocker=ctx.new_page();blocker.goto(BASE+'suppliers.html');ready(blocker)
   blocker.evaluate("()=>{window.lockReady=false;window.hold=navigator.locks.request('entre-besos-sync',()=>new Promise(resolve=>{window.releaseSync=resolve;window.lockReady=true}));}")
   blocker.wait_for_function('()=>window.lockReady')
   page.locator('#supplier-filter').select_option('Tapones');page.locator('#supplier-search').fill('sesión');page.locator('[data-supplier-edit]').click();page.locator('#supplier-contact').fill('Contacto corregido');page.locator('#supplier-save').click()
   page.evaluate("()=>{window.snapshotDone=false;window.snapshotError=null;window.snapshotTest=EBShared.snapshot().then(()=>{window.snapshotDone=true},e=>{window.snapshotError=e.message});}")
   page.wait_for_timeout(300);expect(page.locator('#supplier-dialog')).to_be_visible();assert page.evaluate('!snapshotDone && !snapshotError')
   blocker.evaluate('()=>window.releaseSync()');closed(page);page.wait_for_function('()=>snapshotDone');assert page.evaluate('snapshotError') is None
   expect(page.locator('#supplier-search')).to_have_value('sesión');expect(page.locator('#supplier-filter')).to_have_value('Tapones');assert data(ctx)['suppliers'][0]['contact']=='Contacto corregido';blocker.close()
   page.locator('#supplier-search').fill('');page.locator('#supplier-filter').select_option('')
   # Slow request and double Save cannot duplicate or close before acknowledgement.
   page.evaluate("()=>{window.originalFetch=window.fetch;window.fetch=async function(u,o){if(String(u).endsWith('/api/state')&&o?.method==='PUT')await new Promise(r=>setTimeout(r,800));return window.originalFetch.call(this,u,o)};}")
   fill(page,'Proveedor conexión lenta');page.evaluate("()=>{document.querySelector('#supplier-save').click();document.querySelector('#supplier-save').click();}")
   expect(page.locator('#supplier-name')).to_be_disabled();expect(page.locator('#supplier-dialog')).to_be_visible();closed(page);assert len(data(ctx)['suppliers'])==2
   page.evaluate('()=>{window.fetch=window.originalFetch;}');print('PASS queued/slow saves: waits for acknowledgement, returns with filters, no duplicate.',flush=True)
   # Server commits, but its response is lost. Retry must replay exactly once.
   lost={'done':False}
   def lose_ack(route):
    if route.request.method=='PUT' and not lost['done']:
     lost['done']=True;response=route.fetch();assert response.ok;route.abort('failed')
    else:route.continue_()
   page.route('**/api/state',lose_ack);fill(page,'Proveedor acuse interrumpido');page.locator('#supplier-save').click()
   closed(page);assert len(data(ctx)['suppliers'])==3;page.unroute('**/api/state',lose_ack)
   print('PASS lost acknowledgement automatically confirmed by authenticated receipt; no second save required.',flush=True)
   # Offline failure retains inputs. Reconnection + retry uses the same supplier ID.
   page.locator('[data-supplier-edit]').filter(has_text='Editar').last.click();page.locator('#supplier-contact').fill('Conservar durante desconexión');ctx.set_offline(True);page.locator('#supplier-save').click()
   expect(page.locator('#supplier-error')).to_contain_text('conexión',timeout=20000);expect(page.locator('#supplier-contact')).to_have_value('Conservar durante desconexión');assert 'PDF' not in page.locator('#supplier-error').inner_text()
   ctx.set_offline(False);page.locator('#supplier-save').click();closed(page);assert len(data(ctx)['suppliers'])==3
   print('PASS lost acknowledgement/offline retries: fields preserved and cloud record not duplicated.',flush=True)
   # Recover an existing outbox after reload, as in the user's already-saved capture.
   def block_put(route):
    if route.request.method=='PUT':route.abort('failed')
    else:route.continue_()
   page.route('**/api/state',block_put);fill(page,'Proveedor pendiente recuperado');page.locator('#supplier-save').click();expect(page.locator('#supplier-error')).to_contain_text('no se confirmó',timeout=20000)
   pending=page.evaluate('localStorage.getItem("eb-shared-outbox-v1")');assert pending
   page.unroute('**/api/state',block_put);page.reload();ready(page);assert len(data(ctx)['suppliers'])==4
   assert sum(s['name']=='Proveedor pendiente recuperado' for s in data(ctx)['suppliers'])==1
   # A cookie change to EB2 must NOT be silently repaired as an EB1 write.
   fill(page,'No enviar como EB2');login(ctx,'test-reader');page.locator('#supplier-save').click()
   expect(page.locator('#supplier-error')).to_contain_text('EB2',timeout=20000);assert page.evaluate('EBShared.pending')
   observer=b.new_context();login(observer);assert len(data(observer)['suppliers'])==4;assert ctx.request.get(BASE+'api/state').status==403
   login(ctx);page.reload();ready(page);assert len(data(ctx)['suppliers'])==5
   # Concurrent editing remains protected; never overwrite another device's data.
   other=observer.new_page();other.goto(BASE+'suppliers.html');ready(other)
   page.locator('[data-supplier-edit]').first.click();page.locator('#supplier-contact').fill('BORRADOR NO SOBRESCRIBIR')
   fill(other,'Proveedor de otro dispositivo');other.locator('#supplier-save').click();closed(other)
   page.locator('#supplier-save').click();expect(page.locator('#eb-use-cloud')).to_be_attached(timeout=20000)
   assert len(data(observer)['suppliers'])==6 and all(s.get('contact')!='BORRADOR NO SOBRESCRIBIR' for s in data(observer)['suppliers'])
   assert 'BORRADOR NO SOBRESCRIBIR' in page.evaluate('localStorage.getItem("eb-v1")')
   for k in seed:assert data(observer)[k]==seed[k],k
   observer.close();print('PASS outbox recovery, EB2 denial, cross-device conflict preservation and unrelated records unchanged.',flush=True)
   assert not errors,errors
   print('PASS SUPPLIER SYNC COMPLETE',engine,flush=True)
  ctx.close();b.close()
finally:
 server.terminate();server.wait(timeout=10)
