"""Synthetic providers in a disposable server; never reads or writes production data."""
import json,os,shutil,subprocess,tempfile,time,urllib.request,uuid,sys
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path('/tmp/eb-supplier-save');OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8801/';PUB=Path(tempfile.mkdtemp(prefix='eb-supplier-save-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.html','.js','.css','.jpg','.png','.webmanifest']:shutil.copy(f,PUB/f.name)
for folder in ['vendor','icons']:shutil.copytree(ROOT/folder,PUB/folder,dirs_exist_ok=True)
shutil.copy(ROOT/'control.html',PUB/'index.html');shutil.copy(ROOT/'index.html',PUB/'legacy.html')
seed={'lots':[{'id':'SUP-SAVE-SENTINEL','p':0,'bottles':12,'ml':720,'unitCost':100,'totalCost':1200}],'moves':[],'contacts':[{'id':'sentinel','name':'Do not alter'}],'materials':[],'supplies':[],'partnerOrders':[],'expenses':[],'documents':[]}
code="const fs=require('fs'),os=require('os'),path=require('path'),crypto=require('crypto');const salt='43'.repeat(16),hash=crypto.scryptSync('synthetic-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=['test-edgardo','test-ricardo','test-mario','test-eb2'].map((username,i)=>({username,name:username,role:i===3?'reader':'editor',salt,hash}));const app=require('./server.cjs').createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-supplier-save-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8801'],secure:false});app.server.listen(8801,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(PUB)},stdout=subprocess.DEVNULL)
for _ in range(50):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def login(ctx,user='test-edgardo'):
 r=ctx.request.post(BASE+'api/login',data={'username':user,'password':'synthetic-only'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
def state(ctx):return ctx.request.get(BASE+'api/state').json()
def ready(page):page.wait_for_function("()=>window.EBShared&&!window.EBShared.pending&&document.getElementById('eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=30000)
def returned(page):
 expect(page.locator('#supplier-dialog')).to_have_count(0,timeout=30000);ready(page);expect(page.locator('#suppliers-app h1')).to_have_text('Proveedores');expect(page.locator('#supplier-message')).to_contain_text('Confirmado')
def visible_error(page,text):
 expect(page.locator('#supplier-error')).to_contain_text(text);expect(page.locator('#supplier-error')).to_be_in_viewport();expect(page.locator('#supplier-dialog')).to_be_visible();expect(page.locator('#supplier-save')).to_be_enabled()
try:
 with sync_playwright() as p:
  modes=[('chromium',390)] if '--baseline' in sys.argv else [('chromium',1440),('webkit',390)]
  for engine,width in modes:
   browser=(p.webkit.launch(headless=True) if engine=='webkit' else p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox']))
   ctx=browser.new_context(viewport={'width':width,'height':844},is_mobile=width<700,has_touch=width<700);csrf=login(ctx);before=state(ctx)
   r=ctx.request.put(BASE+'api/state',data={'revision':before['revision'],'operation':str(uuid.uuid4()),'initialize':True,'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':csrf});assert r.ok,r.text()
   page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept());page.goto(BASE+'suppliers.html');ready(page)
   if '--baseline' in sys.argv:
    page.locator('#supplier-new').click();page.locator('#supplier-name').fill('Proveedor baseline');page.locator('#supplier-item').select_option('Tapones');page.locator('#supplier-item').select_option('__other__');page.locator('#supplier-save').click();expect(page.locator('#supplier-error')).to_contain_text('Escribe un insumo');assert not state(ctx)['data'].get('suppliers')
    page.locator('#supplier-item').select_option('Tapones');page.locator('#supplier-email').fill('correo no valido');page.locator('#supplier-save').click();expect(page.locator('#supplier-dialog')).to_be_visible();assert page.locator('#supplier-error').inner_text()=='';assert not state(ctx)['data'].get('suppliers')
    print('REPRODUCED: blank optional Otros blocks valid selected supply; native invalid email blocks submit without an app error message.',flush=True)
    ctx.close();browser.close();continue
   # Errors must be clear, in view, and must retain fields.
   page.locator('#supplier-new').click();page.locator('#supplier-save').click();visible_error(page,'nombre del proveedor')
   page.locator('#supplier-name').fill('Proveedor Alpha');page.locator('#supplier-save').click();visible_error(page,'al menos un insumo')
   page.locator('#supplier-item').select_option('Tapones');page.locator('#supplier-email').fill('correo no valido');page.locator('#supplier-save').click();visible_error(page,'correo');expect(page.locator('#supplier-name')).to_have_value('Proveedor Alpha');assert not state(ctx)['data'].get('suppliers')
   page.screenshot(path=str(OUT/f'validation-{engine}.png'),full_page=True)
   page.locator('#supplier-email').fill('contacto@example.test');page.locator('#supplier-item').select_option('__other__');page.locator('#supplier-save').click();returned(page);assert state(ctx)['data']['suppliers'][0]['items']==['Tapones']
   # Save closes into the exact prior filtered list; all data has reached the server.
   page.locator('#supplier-filter').select_option('Tapones');page.locator('#supplier-search').fill('Alpha');page.locator('[data-supplier-edit]').click();page.locator('#supplier-contact').fill('Contacto corregido');page.locator('#supplier-save').click();returned(page);expect(page.locator('#supplier-filter')).to_have_value('Tapones');expect(page.locator('#supplier-search')).to_have_value('Alpha');expect(page.locator('.supplier-card')).to_contain_text('Contacto corregido')
   assert state(ctx)['data']['suppliers'][0]['contact']=='Contacto corregido'
   page.screenshot(path=str(OUT/f'returned-{engine}.png'),full_page=True)
   # Store failure retains inputs and does not claim saved or close.
   page.locator('[data-supplier-edit]').click();page.locator('#supplier-phone').fill('99999');old=state(ctx)
   page.evaluate("()=>{window.testSupplierSet=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='eb-v1')throw Error('Simulated storage failure');return window.testSupplierSet.call(this,k,v)};}")
   page.locator('#supplier-save').click();visible_error(page,'Simulated storage failure');expect(page.locator('#supplier-phone')).to_have_value('99999');assert state(ctx)==old
   page.evaluate('()=>{Storage.prototype.setItem=window.testSupplierSet;delete window.testSupplierSet;}');page.locator('#supplier-save').click();returned(page)
   # A selected option without a native change event must still be captured.
   page.locator('#supplier-filter').select_option('');page.locator('#supplier-search').fill('');page.locator('#supplier-new').click();page.locator('#supplier-name').fill('Proveedor Pending Select');page.locator('#supplier-item').evaluate("e=>e.value='Botellas vacías'");page.locator('#supplier-save').click();returned(page)
   assert state(ctx)['data']['suppliers'][1]['items']==['Botellas vacías']
   # Unadded custom concept is not lost. Repeated submit does not create duplicates.
   page.locator('#supplier-new').click();page.locator('#supplier-name').fill('Proveedor Custom');page.locator('#supplier-item').select_option('__other__');page.locator('#supplier-other').fill('Cajas personalizadas');page.evaluate("()=>{const f=document.getElementById('supplier-form');f.requestSubmit();f.requestSubmit();}");returned(page)
   current=state(ctx);assert len(current['data']['suppliers'])==3;assert current['data']['suppliers'][2]['items']==['Cajas personalizadas']
   # Cloud confirmation failure retains capture. Retry uses the same id/version.
   page.locator('[data-supplier-edit]').first.click();page.locator('#supplier-place').fill('Nueva ubicación');page.evaluate("()=>{window.testSupplierSnapshot=EBShared.snapshot;EBShared.snapshot=async()=>{throw Error('Simulated verification failure')}}")
   page.locator('#supplier-save').click();visible_error(page,'Simulated verification failure');expect(page.locator('#supplier-place')).to_have_value('Nueva ubicación');assert len(state(ctx)['data']['suppliers'])==3
   page.evaluate('()=>{EBShared.snapshot=window.testSupplierSnapshot;delete window.testSupplierSnapshot;}');page.locator('#supplier-save').click();expect(page.locator('#supplier-dialog')).to_have_count(0);ready(page);assert len(state(ctx)['data']['suppliers'])==3
   # Other EB1 partners edit the same supplier; no creator-only restriction.
   for user in ['test-ricardo','test-mario']:
    other=browser.new_context(viewport={'width':width,'height':844});login(other,user);q=other.new_page();q.goto(BASE+'suppliers.html');ready(q);q.locator('[data-supplier-edit]').first.click();q.locator('#supplier-contact').fill(user);q.locator('#supplier-save').click();returned(q);other.close()
   # EB2 cannot open provider controls or read the full workspace.
   reader=browser.new_context();login(reader,'test-eb2');q=reader.new_page();q.goto(BASE+'suppliers.html');expect(q.locator('#partner-report-app')).to_be_visible();expect(q.locator('#supplier-new')).to_have_count(0);assert reader.request.get(BASE+'api/state').status==403;reader.close()
   final=state(ctx)['data']
   for k in seed:assert final[k]==seed[k],k
   assert not errors,errors;assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   ctx.close();browser.close();print('PASS',engine,width,'blank Otros, selected supply, visible validation, confirmed save-close-return, all 3 editors, retry safety, original data preserved.',flush=True)
finally:
 server.terminate();server.wait(timeout=10)
