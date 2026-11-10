"""Disposable authenticated workspaces; no real business records or production writes."""
import os,json,shutil,subprocess,tempfile,time,urllib.request,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();BASE='http://127.0.0.1:8861/';OUT=Path(os.environ.get('EB_REVIEW','/tmp/eb-material-moves-review'));OUT.mkdir(exist_ok=True,parents=True)
PUB=Path(tempfile.mkdtemp(prefix='eb-mat-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:shutil.copy(f,PUB/f.name)
shutil.copy(ROOT/'control.html',PUB/'index.html');shutil.copy(ROOT/'index.html',PUB/'legacy.html')
for folder in ['vendor','icons']:shutil.copytree(ROOT/folder,PUB/folder,dirs_exist_ok=True)
subprocess.run(['node','tests/material-moves.cjs'],env={**os.environ,'EB_MATERIAL_FIXTURE':str(OUT/'fixture.json')},check=True)
seed=json.loads((OUT/'fixture.json').read_text())
code="""const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='43'.repeat(16),hash=crypto.scryptSync('material-synthetic-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=['test-editor','test-editor2','test-reader'].map(username=>({username,name:username,role:username==='test-reader'?'reader':'editor',salt,hash}));createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-mat-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8861'],secure:false}).server.listen(8861,'127.0.0.1');"""
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(PUB)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for _ in range(80):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def login(ctx,user='test-editor'):
 r=ctx.request.post(BASE+'api/login',data={'username':user,'password':'material-synthetic-only'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
def cloud(ctx):return ctx.request.get(BASE+'api/state').json()['data']
def ready(p):p.wait_for_function("()=>window.EBShared&&!EBShared.pending&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=25000)
def saved(p):expect(p.locator('#material-move-dialog')).to_have_count(0,timeout=25000);ready(p)
def field(p,id,value):p.locator('#'+id).fill(value)
def card(p,index):return p.locator('[data-record="'+str(index)+'"]')
def shot(p,name):
 assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),name
 if p.locator('#material-move-dialog').count():assert p.locator('#material-move-dialog').evaluate('(x)=>x.scrollWidth<=x.clientWidth+1'),name
 p.screenshot(path=str(OUT/(name+'.png')),full_page=True)
try:
 with sync_playwright() as pw:
  engine=os.environ.get('EB_BROWSER','chromium');browser=getattr(pw,engine).launch(**({'executable_path':shutil.which('google-chrome') or shutil.which('chromium'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  pc=browser.new_context(viewport={'width':1440,'height':1000});token=login(pc)
  r=pc.request.put(BASE+'api/state',data={'revision':0,'operation':str(uuid.uuid4()),'initialize':True,'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert r.ok,r.text()
  p=pc.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept())
  p.goto(BASE+'materials.html?kind=supplies');ready(p)
  expect(p.locator('[data-material-move]')).to_have_count(3);expect(p.locator('[data-material-use]')).to_have_count(3)
  p.locator('#material-search').fill('Tapones');p.locator('#material-filter').select_option('CDMX');p.locator('[data-material-move="0"]').click();field(p,'mm-qty','2100');p.locator('#mm-to').select_option('USA');p.locator('#mm-status').select_option('transit');p.locator('#mm-purpose').select_option('Para retaponado');expect(p.locator('#mm-preview')).to_contain_text('4,200');shot(p,engine+'-transfer-caps')
  p.locator('#mm-save').click();saved(p);assert cloud(pc)['supplies'][0]['qty']==4200;expect(p.locator('#material-filter')).to_have_value('CDMX');expect(p.locator('#material-search')).to_have_value('Tapones');expect(p.locator('.mm-in-transit')).to_contain_text('2,100');assert len(cloud(pc)['supplies'])==3
  p.reload();ready(p);assert cloud(pc)['supplies'][0]['qty']==4200;p.locator('[data-mm-receive]').click();p.locator('#mm-save').click();saved(p);d=cloud(pc);assert d['supplies'][0]['qty']==4200;usa=next(x for x in d['supplies'] if x['loc']=='USA');assert usa['qty']==2100 and usa['totalCost']==19910
  # Second device consumes received material, and the first device sees the same result.
  phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);login(phone,'test-editor2');z=phone.new_page();z.on('pageerror',lambda e:errors.append(str(e)));z.on('dialog',lambda d:d.accept());z.goto(BASE+'materials.html?kind=supplies');ready(z)
  z.locator('[data-material-use="3"]').click();field(z,'mm-qty','2100');z.locator('#mm-purpose').select_option('Retaponado');expect(z.locator('#mm-preview')).to_contain_text('Saldo en USA: 0');shot(z,engine+'-use-caps-mobile');z.locator('#mm-save').click();saved(z);assert cloud(phone)['supplies'][3]['qty']==0;assert cloud(phone)['supplies'][0]['qty']==4200
  p.wait_for_function("()=>JSON.parse(localStorage.getItem('eb-v1')).supplies[3].qty===0",timeout=20000)
  # 700 ml consumption is tied to DB and never touches 720 ml or finished bottles.
  z.locator('[data-material-use="1"]').click();field(z,'mm-qty','500');z.locator('#mm-purpose').select_option('Envasado');z.locator('.mm-optional summary').click();z.locator('#mm-lot').select_option('DB-SYN');expect(z.locator('#mm-preview')).to_contain_text('Saldo en Oaxaca: 500');shot(z,engine+'-use-bottles-db');z.locator('#mm-save').click();saved(z)
  d=cloud(phone);assert d['supplies'][1]['qty']==500 and d['supplies'][2]['qty']==200;assert d['lots']==seed['lots'];assert len(d['materialMovements'])==3
  bottle=d['materialMovements'][-1]['id'];caps=d['materialMovements'][1]['id']
  # Edit metadata must not post another deduction; quantity edits adjust only the difference.
  z.locator('[data-mm-edit="'+bottle+'"]').click();field(z,'mm-notes','SYNTHETIC - production use');z.locator('#mm-save').click();saved(z);assert cloud(phone)['supplies'][1]['qty']==500
  z.locator('[data-mm-edit="'+bottle+'"]').click();field(z,'mm-qty','400');z.locator('#mm-save').click();saved(z);assert cloud(phone)['supplies'][1]['qty']==600
  z.locator('[data-mm-cancel="'+bottle+'"]').click();ready(z);expect(z.locator('[data-mm-restore="'+bottle+'"]')).to_be_visible();assert cloud(phone)['supplies'][1]['qty']==1000
  z.locator('[data-mm-restore="'+bottle+'"]').click();ready(z);expect(z.locator('[data-mm-edit="'+bottle+'"]')).to_be_visible();assert cloud(phone)['supplies'][1]['qty']==600
  # Invalid input retains form and stock.
  z.locator('[data-mm-edit="'+bottle+'"]').click();field(z,'mm-qty','0.5');z.locator('#mm-save').click();expect(z.locator('#mm-error')).to_contain_text('entero');assert cloud(phone)['supplies'][1]['qty']==600;z.locator('#mm-cancel').click()
  # Failed network keeps input; retry the exact same event, never duplicate or subtract twice.
  z.locator('[data-material-use="1"]').click();field(z,'mm-qty','10');z.locator('#mm-purpose').select_option('Merma')
  z.route('**/api/state',lambda route:route.abort('failed') if route.request.method=='PUT' else route.continue_())
  z.locator('#mm-save').click();expect(z.locator('#mm-error')).to_contain_text('mismo movimiento',timeout=10000);assert cloud(phone)['supplies'][1]['qty']==600;expect(z.locator('#mm-qty')).to_have_value('10')
  z.unroute('**/api/state');z.locator('#mm-save').click();saved(z);d=cloud(phone);assert d['supplies'][1]['qty']==590 and len(d['materialMovements'])==4
  # New destinations use same-item and same-presentation balances.
  z.locator('[data-material-move="1"]').click();field(z,'mm-qty','10');z.locator('#mm-to').select_option('__new__');field(z,'mm-new-location','Taller de prueba');z.locator('#mm-purpose').select_option('Otro');field(z,'mm-custom-purpose','Prueba de envasado');z.locator('#mm-save').click();saved(z);assert next(x for x in cloud(phone)['supplies'] if x['loc']=='Taller de prueba')['qty']==10
  # Marketing supports identical operations.
  z.locator('.mobile-nav [data-kind="marketing"]').click();z.locator('[data-material-use="0"]').click();field(z,'mm-qty','3');z.locator('#mm-purpose').select_option('Promoción / muestras');z.locator('#mm-save').click();saved(z);assert cloud(phone)['materials'][0]['qty']==17
  shot(z,engine+'-marketing-mobile');z.goto(BASE+'materials.html?kind=supplies');ready(z);z.locator('#material-filter').select_option('CDMX');expect(z.locator('.material-record')).to_have_count(1);expect(z.locator('.material-record')).to_contain_text('4,200');shot(z,engine+'-remaining-caps-mobile')
  # Original create, edit, delete remains usable for unlinked records.
  p.reload();ready(p);p.locator('#material-name').select_option('Etiquetas');p.locator('#material-location').select_option('CDMX');p.locator('#material-qty').fill('20');p.locator('#material-cost').fill('100');p.locator('#material-save').click();ready(p);d=cloud(pc);idx=next(i for i,x in enumerate(d['supplies']) if x['name']=='Etiquetas');p.locator('[data-edit-material="'+str(idx)+'"]').click();p.locator('#material-qty').fill('30');p.locator('#material-save').click();ready(p);assert cloud(pc)['supplies'][idx]['qty']==30;p.locator('[data-delete-material="'+str(idx)+'"]').click();ready(p);assert not any(x['name']=='Etiquetas' for x in cloud(pc)['supplies'])
  # EB2 only receives the allowed aggregate report, cannot mutate or get raw materials.
  reader=browser.new_context();login(reader,'test-reader');r=reader.new_page();r.goto(BASE+'materials.html?kind=supplies');expect(r.locator('#partner-report-state')).to_contain_text('Actualizado',timeout=25000);expect(r.locator('[data-material-use],[data-material-move],#mm-save')).to_have_count(0);assert reader.request.get(BASE+'api/state').status==403
  model=reader.request.get(BASE+'api/partner-report').json()['model'];assert any(s['title']=='Insumos y marketing utilizados' for s in model['sections']);assert 'SYNTHETIC - production use' not in json.dumps(model)
  d=cloud(pc)
  for k in ['lots','moves','contacts','suppliers','expenses','partnerOrders','documents']:assert d[k]==seed[k],k
  assert not errors,errors
  print('PASS MATERIAL MOVEMENTS BROWSER '+engine+': authenticated two-device cloud; 6300 to 4200; transit/receipt/use; 500 bottles at 700ml; source/destination; edit/cancel/restore; exact retry; filters and automatic return; marketing; preserved lots/sales; EB2 report only.',flush=True)
  pc.close();phone.close();reader.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
