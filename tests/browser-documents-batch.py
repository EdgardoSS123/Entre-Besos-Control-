"""Independent disposable database; no production records or credentials."""
import json,os,shutil,subprocess,tempfile,time,urllib.request,base64
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path('/tmp/eb-doc-batch-review');OUT.mkdir(exist_ok=True,parents=True);BASE='http://127.0.0.1:8863/'
public=Path(tempfile.mkdtemp(prefix='eb-doc-batch-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.html','.js','.css','.jpg','.png','.webmanifest']:shutil.copy(f,public/f.name)
shutil.copy(ROOT/'control.html',public/'index.html')
for folder in ['vendor','icons']:shutil.copytree(ROOT/folder,public/folder)
seed={'lots':[{'id':'BATCH-LOT','p':0,'bottles':6,'ml':720,'unitCost':200,'totalCost':1200}],'moves':[],'contacts':[{'name':'Keep original'}],'supplies':[{'name':'Keep caps','loc':'Oaxaca','qty':100,'totalCost':50}],'materials':[]}
code="const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');const {createApp}=require('./server.cjs');const salt='11'.repeat(16),hash=crypto.scryptSync('batch-test-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const a=createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-batch-db-')),root:process.env.TEST_PUBLIC,users:[{username:'editor',name:'Test EB1',role:'editor',salt,hash},{username:'reader',name:'Test EB2',role:'reader',salt,hash}],origins:['http://127.0.0.1:8863'],secure:false});a.db.prepare('UPDATE workspace SET revision=1,payload=?,updated=?,actor=? WHERE id=1').run(process.env.TEST_SEED,new Date().toISOString(),'test');a.server.listen(8863,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'TEST_PUBLIC':str(public),'TEST_SEED':json.dumps(seed)},stdout=subprocess.DEVNULL)
for _ in range(60):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jGZkAAAAASUVORK5CYII=')
def file(name,content=png):return {'name':name,'mimeType':'image/png','buffer':content}
def login(ctx,user='editor'):
 r=ctx.request.post(BASE+'api/login',data={'username':user,'password':'batch-test-only'},headers={'Origin':BASE[:-1]});assert r.ok,r.text()
def documents(ctx):
 r=ctx.request.get(BASE+'api/documents');assert r.ok,r.text();return r.json()['documents']
def shot(p,name):
 assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),name
 if p.locator('#docs-dialog').count():assert p.locator('#docs-dialog').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'),name
 p.screenshot(path=str(OUT/(name+'.png')),full_page=True)
try:
 with sync_playwright() as pw:
  engine=os.environ.get('EB_BROWSER','chromium');browser=getattr(pw,engine).launch(**({'executable_path':shutil.which('google-chrome') or shutil.which('chromium'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  ctx=browser.new_context(viewport={'width':390 if engine=='webkit' else 1440,'height':900},has_touch=engine=='webkit',is_mobile=engine=='webkit');login(ctx)
  p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(BASE+'documents.html');expect(p.locator('[data-category]')).to_have_count(10);shot(p,engine+'-ten-categories')
  for cat in ['COMERCAM','AMMA','FDA','COFEPRIS','Contratos']:expect(p.locator('[data-category="'+cat+'"]').first).to_be_visible()
  p.locator('[data-category="Asambleas"]').click();p.locator('#docs-new').click();expect(p.locator('#doc-file')).to_have_attribute('multiple','');p.locator('#doc-file').set_input_files([file('asamblea-'+str(i)+'.png') for i in range(1,13)]+[file('vacio.png',b'')]);expect(p.locator('.doc-batch-item')).to_have_count(13);p.locator('#doc-title').fill('Asamblea inicial');p.locator('.docs-optional summary').click();p.locator('#doc-lot').select_option('BATCH-LOT');p.locator('#doc-expiry').fill('2028-12-01');p.locator('#doc-notes').fill('Prueba aislada');shot(p,engine+'-batch-selected');p.locator('#doc-save').click()
  expect(p.locator('#doc-batch-progress')).to_contain_text('12 de 13 guardados',timeout=30000);expect(p.locator('[data-state="saved"]')).to_have_count(12);expect(p.locator('[data-state="error"]')).to_have_count(1);stored=documents(ctx);assert len(stored)==12 and all(d['category']=='Asambleas' and d['lot']=='BATCH-LOT' for d in stored);shot(p,engine+'-partial-complete')
  p.locator('[data-batch-remove="12"]').click();p.locator('#doc-save').click();expect(p.locator('#docs-dialog')).to_have_count(0);expect(p.locator('.docs-file')).to_have_count(12);assert len(documents(ctx))==12
  # One connection failure pauses the queue; only unconfirmed rows retry.
  p.locator('[data-category="FDA"]').click();p.locator('#docs-new').click();p.locator('#doc-file').set_input_files([file('fda-'+str(i)+'.png') for i in range(1,4)]);posts=[];failed=[False]
  def interrupt(route):
   req=route.request
   if req.method=='POST':
    payload=req.post_data_json;posts.append(payload['filename'])
    if payload['filename']=='fda-2.png' and not failed[0]:failed[0]=True;route.abort();return
   route.continue_()
  p.route('**/api/documents',interrupt);p.locator('#doc-save').click();expect(p.locator('#doc-batch-progress')).to_contain_text('1 de 3 guardados',timeout=20000);expect(p.locator('#doc-save')).to_be_enabled(timeout=20000);p.unroute('**/api/documents',interrupt);assert len(documents(ctx))==13;p.locator('#doc-save').click();expect(p.locator('#docs-dialog')).to_have_count(0,timeout=20000);assert len(documents(ctx))==15;assert posts.count('fda-1.png')==1
  # Committed upload with lost response is recovered by its stable ID.
  p.locator('[data-category="COMERCAM"]').click();p.locator('#docs-new').click();p.locator('#doc-file').set_input_files(file('comercam.png'));count=[0]
  def lost_reply(route):
   if route.request.method=='POST':count[0]+=1;response=route.fetch();assert response.ok;route.abort()
   else:route.continue_()
  p.route('**/api/documents',lost_reply);p.locator('#doc-save').click();expect(p.locator('#docs-dialog')).to_have_count(0,timeout=20000);p.unroute('**/api/documents',lost_reply);assert count[0]==1 and len(documents(ctx))==16
  for cat in ['AMMA','COFEPRIS','Contratos']:
   p.locator('[data-category="'+cat+'"]').click();p.locator('#docs-new').click();p.locator('#doc-file').set_input_files([file(cat+'-uno.png'),file(cat+'-dos.png')]);p.locator('#doc-save').click();expect(p.locator('#docs-dialog')).to_have_count(0,timeout=20000);expect(p.locator('.docs-file')).to_have_count(2)
  assert len(documents(ctx))==22
  other=browser.new_context();login(other);q=other.new_page();q.goto(BASE+'documents.html?category=Asambleas');expect(q.locator('.docs-file')).to_have_count(12);row=documents(other)[0];download=other.request.get(BASE+'api/documents/'+row['id']+'/file');assert download.ok and download.body()==png
  # Existing individual editing and reversible deletion remain available.
  p.locator('[data-edit-doc]').first.click();p.locator('#doc-title').fill('Contrato corregido');p.locator('#doc-save').click();expect(p.locator('#docs-dialog')).to_have_count(0);expect(p.locator('.docs-file',has_text='Contrato corregido')).to_have_count(1)
  p.locator('.docs-file',has_text='Contrato corregido').locator('[data-delete-doc]').click();expect(p.locator('.docs-file')).to_have_count(1);p.locator('#docs-trash').click();expect(p.locator('[data-restore]')).to_have_count(1);p.locator('[data-restore]').click();expect(p.locator('[data-restore]')).to_have_count(0)
  assert ctx.request.get(BASE+'api/state').json()['data']==seed
  readonly=browser.new_context();login(readonly,'reader');assert readonly.request.get(BASE+'api/documents').status==403
  assert not errors,errors
  print('PASS DOCUMENT BATCH '+engine+': ten categories, twelve uploads together, per-file names, invalid file isolation, pending-only retry, lost response recovered without duplicate, all new categories, cross-device bytes, edit/delete/restore, EB2 denied and business records identical.',flush=True)
  readonly.close();other.close();ctx.close();browser.close()
finally:server.terminate();server.wait(timeout=10)
