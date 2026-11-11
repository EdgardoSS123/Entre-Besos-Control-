"""Read-only coverage plus order regression on disposable SQLite; no production data."""
import copy,json,os,shutil,subprocess,tempfile,time,urllib.request,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path(os.environ.get('EB_COVERAGE_REVIEW','/tmp/eb-coverage-review'));OUT.mkdir(parents=True,exist_ok=True)
public=Path(tempfile.mkdtemp(prefix='eb-coverage-public-'));BASE='http://127.0.0.1:8872/'
for f in ROOT.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:shutil.copy(f,public/f.name)
shutil.copy(ROOT/'control.html',public/'index.html')
for folder in ['vendor','icons']:shutil.copytree(ROOT/folder,public/folder)
subprocess.run(['node','tests/orders-coverage.cjs'],env={**os.environ,'EB_COVERAGE_FIXTURE':str(OUT/'fixture.json')},check=True)
seed=json.loads((OUT/'fixture.json').read_text())
code=r"""
const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createApp}=require('./server.cjs');const salt='62'.repeat(16),hash=crypto.scryptSync('coverage-isolated',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');
const users=['esalazars','rsalazarm','msaenzc'].map(username=>({username,name:username,role:'editor',salt,hash}));users.push({username:'socioEB2',name:'Test EB2',role:'reader',salt,hash});
createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-coverage-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8872'],secure:false}).server.listen(8872,'127.0.0.1');
"""
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(public)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for _ in range(80):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def login(ctx,user):
 r=ctx.request.post(BASE+'api/login',data={'username':user,'password':'coverage-isolated'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
def cloud(ctx):
 r=ctx.request.get(BASE+'api/state');assert r.ok,r.text();return r.json()
def ready(page):page.wait_for_function("()=>window.EBShared&&!EBShared.pending&&!window.EBOrdersUI?.saving&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=20000)
def metrics(page,expected):
 for i,n in enumerate(expected):expect(page.locator('.coverage-totals .coverage-cell>b').nth(i)).to_contain_text(str(n))
def close(page):expect(page.locator('#order-dialog')).to_have_count(0,timeout=20000);ready(page)
try:
 with sync_playwright() as pw:
  engine=os.environ.get('EB_BROWSER','chromium');browser=getattr(pw,engine).launch(**({'executable_path':shutil.which('google-chrome') or shutil.which('chromium'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  pc=browser.new_context(viewport={'width':1440,'height':1000});csrf=login(pc,'esalazars')
  r=pc.request.put(BASE+'api/state',data={'revision':0,'initialize':True,'operation':str(uuid.uuid4()),'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':csrf});assert r.ok,r.text()
  revision=cloud(pc)['revision'];a=pc.new_page();errors=[];a.on('pageerror',lambda e:errors.append(str(e)));a.on('dialog',lambda d:d.accept());a.goto(BASE+'orders.html');ready(a);metrics(a,[77,48,29]);expect(a.locator('#orders-coverage')).to_contain_text('3 pedidos')
  a.locator('.coverage-details>summary').click();expect(a.locator('[data-coverage-product="1"]')).to_contain_text('7 botellas');expect(a.locator('[data-coverage-product="0"]')).to_contain_text('20 disponibles');a.screenshot(path=str(OUT/(engine+'-coverage-desktop.png')),full_page=True)
  assert cloud(pc)['revision']==revision and cloud(pc)['data']==seed,'Viewing coverage must not write state'
  phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);login(phone,'rsalazarm');b=phone.new_page();b.on('pageerror',lambda e:errors.append(str(e)));b.on('dialog',lambda d:d.accept());b.goto(BASE+'orders.html?partner=ricardo');ready(b);metrics(b,[77,48,29]);b.locator('.coverage-details>summary').click();b.screenshot(path=str(OUT/(engine+'-coverage-mobile.png')),full_page=True);assert b.evaluate('document.documentElement.scrollWidth<=innerWidth')
  b.locator('[data-order-filter="delivered"]').click();metrics(b,[77,48,29]);b.locator('[data-order-filter="all"]').click();b.locator('.order-dates>summary').click();b.locator('#orders-filter-from').fill('2099-01-01');metrics(b,[77,48,29]);b.locator('#orders-filter-from').fill('')
  b.locator('#order-new').click();b.locator('#order-customer').fill('Coverage test only');b.locator('[data-amount]').fill('4');b.locator('#order-save').click();close(b);metrics(b,[101,48,53]);new_id=next(o['id'] for o in cloud(phone)['data']['partnerOrders'] if o.get('customer')=='Coverage test only')
  a.reload();ready(a);metrics(a,[101,48,53]);a.locator('[data-partner="edgardo"]').click();a.locator('[data-deliver="P1"]').click();ready(a);metrics(a,[84,31,53]);a.locator('[data-pending="P1"]').click();ready(a);metrics(a,[101,48,53])
  b.reload();ready(b);b.locator('[data-edit-order="'+new_id+'"]').click();b.locator('[data-amount]').fill('1');b.locator('#order-save').click();close(b);metrics(b,[83,48,35]);b.locator('[data-delete-order="'+new_id+'"]').click();ready(b);metrics(b,[77,48,29])
  row=cloud(pc);row['data']['inventoryOpenings'][0]['rows'][0]['quantity']=15
  r=pc.request.put(BASE+'api/state',data={'revision':row['revision'],'operation':str(uuid.uuid4()),'data':row['data']},headers={'Origin':BASE[:-1],'X-EB-CSRF':csrf});assert r.ok,r.text()
  b.reload();ready(b);metrics(b,[77,38,39]);assert b.evaluate('document.documentElement.scrollWidth<=innerWidth')
  reader=browser.new_context();login(reader,'socioEB2');e=reader.new_page();e.goto(BASE+'orders.html');expect(e.locator('#partner-report-state')).to_contain_text('Actualizado',timeout=20000);expect(e.locator('#orders-coverage,#order-new')).to_have_count(0);assert reader.request.get(BASE+'api/state').status==403
  for key in ['lots','moves','materials','supplies','contacts']:assert cloud(pc)['data'][key]==seed[key],key
  assert not errors,errors
  pc.close();phone.close();reader.close();browser.close()
 print('PASS COVERAGE BROWSER:',engine,'global totals, responsive view, read-only rendering, same-lot availability, new/edit/delete/deliver/revert, shared warehouse changes, EB2 restriction; save confirmation retained.')
finally:
 server.terminate();server.wait(timeout=10)
