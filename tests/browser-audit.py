"""Real isolated SQLite and accounts, never production data or real passwords."""
import json,os,shutil,subprocess,tempfile,time,urllib.request,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path('/tmp/eb-operational-audit');OUT.mkdir(exist_ok=True,parents=True)
BASE='http://127.0.0.1:8799/';PUB=Path(tempfile.mkdtemp(prefix='eb-audit-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:shutil.copy(f,PUB/f.name)
shutil.copy(ROOT/'control.html',PUB/'index.html');shutil.copy(ROOT/'index.html',PUB/'legacy.html')
for folder in ['vendor','icons']:shutil.copytree(ROOT/folder,PUB/folder)
code="const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');const salt='66'.repeat(16),hash=crypto.scryptSync('audit-synthetic-password',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=['esalazars','rsalazarm','msaenzc','socioEB2'].map((username,i)=>({username,role:i<3?'editor':'reader',salt,hash}));require('./server.cjs').createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-audit-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8799'],secure:false}).server.listen(8799,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(PUB)},stdout=subprocess.DEVNULL)
for _ in range(80):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
seed=json.loads(subprocess.check_output(['node','-e',"let I=require('./inventory-core.js');for(const f of ['commerce-core','simple-core','corrections-core'])I=require('./'+f+'.js')(I);let d={lots:[{id:'AUDIT',p:0,bottles:480,ml:720,unitCost:200,totalCost:96000}],moves:[],contacts:[{name:'PRIVATE_CONTACT',country:'USA',email:'secret@example.test'}],suppliers:[{name:'PRIVATE_SUPPLIER'}],materials:[],supplies:[],expenses:[{type:'Gasto',amount:100,notes:'PRIVATE_NOTES'}]};d=I.initializeOrigin(d,'AUDIT','CDMX','2026-11-09','2026-11-09T18:00:00Z');console.log(JSON.stringify(d));"],text=True))
def ready(p):p.wait_for_function("()=>window.EBShared&&!window.EBShared.pending&&!window.EBOrdersUI?.saving&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=20000)
def login(ctx,name):
 r=ctx.request.post(BASE+'api/login',data={'username':name,'password':'audit-synthetic-password'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
try:
 with sync_playwright() as p:
  chromium=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox']);webkit=p.webkit.launch()
  editors=[];errors=[]
  for name in ['esalazars','rsalazarm','msaenzc']:
   ctx=chromium.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);token=login(ctx,name);editors.append((ctx,token));page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   if name=='esalazars':
    res=ctx.request.put(BASE+'api/state',data={'revision':0,'operation':str(uuid.uuid4()),'initialize':True,'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert res.ok,res.text()
   page.goto(BASE+'orders.html?partner=edgardo');ready(page);expect(page.locator('#order-new')).to_be_visible()
  a=editors[0][0].pages[0];a.on('dialog',lambda d:d.accept());a.locator('#order-new').click();a.locator('#order-customer').fill('PRIVATE_BUYER');a.locator('[data-amount]').fill('2');a.locator('#order-status').select_option('delivered');a.locator('#order-save').click();ready(a)
  assert a.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'AUDIT').total")==468
  # Ricardo edits a record created by Edgardo, then Mario deletes and recovers it.
  b=editors[1][0].pages[0];b.reload();ready(b);b.locator('[data-edit-order]').click();b.locator('#order-customer').fill('PRIVATE_BUYER_EDITED');b.locator('#order-save').click();ready(b)
  assert b.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'AUDIT').total")==468
  c=editors[2][0].pages[0];c.on('dialog',lambda d:d.accept());c.reload();ready(c);c.locator('[data-delete-order]').click();ready(c);expect(c.locator('.order-record')).to_have_count(0)
  assert c.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'AUDIT').total")==480
  c.locator('[data-order-filter="deleted"]').click();expect(c.locator('.order-record')).to_have_count(1);c.locator('[data-restore-order]').click();ready(c);c.locator('[data-order-filter="pending"]').click();expect(c.locator('.order-record')).to_have_count(1)
  for engine,width in [(chromium,1440),(webkit,390)]:
   ctx=engine.new_context(viewport={'width':width,'height':844},is_mobile=width<700,has_touch=width<700,accept_downloads=True);login(ctx,'socioEB2');r=ctx.new_page();r.on('pageerror',lambda e:errors.append(str(e)))
   for route in ['','orders.html','documents.html','suppliers.html','materials.html?kind=supplies','office.html?section=contacts']:
    r.goto(BASE+route);expect(r.locator('#partner-report-app')).to_be_visible();expect(r.locator('#partner-report-state')).to_contain_text('Actualizado',timeout=20000)
    assert r.evaluate("localStorage.getItem('eb-v1')")==None
    assert ctx.request.get(BASE+'api/state').status==403
    assert ctx.request.get(BASE+'api/documents').status==403
    for marker in ['PRIVATE_BUYER','PRIVATE_CONTACT','PRIVATE_SUPPLIER','PRIVATE_NOTES','secret@example.test']:assert marker not in r.locator('body').inner_text()
    expect(r.locator('.side-nav,.mobile-nav,#order-new,#supplier-new,#docs-new')).to_have_count(0)
   assert r.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   r.screenshot(path=str(OUT/f'eb2-report-{width}.png'),full_page=True)
   with r.expect_download() as event:r.locator('#partner-pdf').click()
   pdf=OUT/f'partner-report-{width}.pdf';event.value.save_as(str(pdf))
   import pymupdf
   doc=pymupdf.open(pdf);text=' '.join(pg.get_text() for pg in doc)
   for marker in ['PRIVATE_BUYER','PRIVATE_CONTACT','PRIVATE_SUPPLIER','PRIVATE_NOTES','Cobrado','Por cobrar']:assert marker not in text
   assert 'Ventas' in text and 'AUDIT' in text and len(doc)>0
   doc[0].get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(OUT/f'partner-pdf-{width}.png');ctx.close()
  assert not errors,errors
  print('PASS AUDIT UI: 3 named EB1 cross-edit/delete/recover; exact 480→468→480 balance; EB2 direct module URLs return report only; no workspace cache; server denial; PC and WebKit PDF with logo excludes private buyers, directories, notes and collections.')
  for ctx,_ in editors:ctx.close()
  chromium.close();webkit.close()
finally:server.terminate();server.wait(timeout=10)
