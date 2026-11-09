import json,os,shutil,subprocess,tempfile,time,urllib.request,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE='http://127.0.0.1:8784/'
OUT=Path('/tmp/eb-orders-review');OUT.mkdir(exist_ok=True,parents=True)
root=Path.cwd();seed=json.loads(Path('/tmp/eb-orders-fixture.json').read_text());public=Path(tempfile.mkdtemp(prefix='eb-orders-public-'))
for f in root.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:shutil.copy(f,public/f.name)
shutil.copy(root/'index.html',public/'legacy.html');shutil.copy(root/'control.html',public/'index.html')
for folder in ['vendor','icons']:shutil.copytree(root/folder,public/folder,dirs_exist_ok=True)
code="const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='43'.repeat(16),hash=crypto.scryptSync('orders-test-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=[{username:'test-editor',name:'Prueba EB1',role:'editor',salt,hash},{username:'test-reader',name:'Prueba EB2',role:'reader',salt,hash}];createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-orders-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8784'],secure:false}).server.listen(8784,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(public)})
for _ in range(60):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def login(page,user='test-editor'):
 expect(page.locator('#eb-user')).to_be_visible();page.locator('#eb-user').fill(user);page.locator('#eb-password').fill('orders-test-only');page.locator('#eb-enter').click()
def synced(page):
 page.wait_for_function("()=>window.EBShared&&!window.EBShared.pending&&document.getElementById('eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=30000)
def stock(page,lot='ORD-ESP'):
 return page.evaluate('(id)=>window.EBLedger.reconciliation(JSON.parse(localStorage.getItem("eb-v1")),id)',lot)
def capture(page,name):
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),name
 page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
try:
 with sync_playwright() as p:
  errors=[];browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
  pc=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);a=pc.new_page();a.on('pageerror',lambda e:errors.append(str(e)));a.on('dialog',lambda d:d.accept())
  pc.add_init_script("if(!localStorage.getItem('eb-v1'))localStorage.setItem('eb-v1',"+json.dumps(json.dumps(seed))+");")
  a.goto(BASE);login(a);a.locator('#eb-publish').click();synced(a)
  a.locator('.sidebar [data-office="orders"]').click();synced(a);expect(a.locator('[data-partner]')).to_have_count(3);capture(a,'orders-home-desktop')
  a.locator('[data-partner="edgardo"]').click();a.locator('#order-new').click();a.locator('#order-customer').fill('Cliente de prueba PC');a.locator('[data-amount]').fill('2');expect(a.locator('[data-lot]')).to_have_value('ORD-ESP');expect(a.locator('#order-from')).to_have_value('CDMX');expect(a.locator('#order-preview')).to_contain_text('12 botellas');capture(a,'orders-form-desktop');a.locator('#order-save').click();synced(a)
  expect(a.locator('.order-record')).to_have_count(1);expect(a.locator('.order-status')).to_have_text('Entrega pendiente');assert stock(a)['total']==120
  a.locator('[data-deliver]').click();synced(a);expect(a.locator('.order-status')).to_have_text('Entregado');assert stock(a)['total']==108;assert stock(a)['orderDelivered']==12;assert stock(a)['unexplained']==0;expect(a.locator('.order-record > .order-stock-note')).to_contain_text(a.evaluate("()=>new Date().toLocaleDateString('es-MX',{day:'2-digit',month:'short',year:'numeric',timeZone:'America/Mexico_City'})"));capture(a,'orders-delivered-desktop')
  webkit=p.webkit.launch(headless=True);phone=webkit.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,accept_downloads=True);z=phone.new_page();z.on('pageerror',lambda e:errors.append(str(e)));z.on('dialog',lambda d:d.accept())
  z.goto(BASE+'orders.html?partner=edgardo');login(z);synced(z);expect(z.locator('.order-status')).to_have_text('Entregado');assert stock(z)['total']==108;capture(z,'orders-delivered-mobile')
  z.locator('[data-pending]').click();synced(z);assert stock(z)['total']==120
  a.wait_for_function("()=>window.EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'ORD-ESP').total===120",timeout=20000)
  z.locator('[data-edit-order]').click();z.locator('[data-amount]').fill('3');z.locator('#order-status').select_option('delivered');expect(z.locator('#order-preview')).to_contain_text('18 botellas');capture(z,'orders-edit-mobile');z.locator('#order-save').click();synced(z);assert stock(z)['total']==102
  a.wait_for_function("()=>window.EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'ORD-ESP').total===102",timeout=20000)
  z.locator('[data-cancel-order]').click();synced(z);assert stock(z)['total']==120;assert stock(z)['unexplained']==0;expect(z.locator('.order-status')).to_have_text('Cancelado')
  z.locator('[data-partner="ricardo"]').click();expect(z.locator('.order-record')).to_have_count(0);z.locator('#order-new').click();z.locator('#order-customer').fill('Cliente de Ricardo');z.locator('#order-from').select_option('Oaxaca');z.locator('[data-product]').select_option('1');expect(z.locator('[data-lot]')).to_have_value('ORD-CUP');z.locator('[data-amount]').fill('1');z.locator('[data-unit]').select_option('bottle');z.locator('#order-status').select_option('delivered');z.locator('#order-save').click();synced(z);assert stock(z,'ORD-CUP')['total']==59
  z.locator('[data-partner="mario"]').click();z.locator('#order-new').click();z.locator('#order-customer').fill('Cliente de Mario');z.locator('[data-amount]').fill('1');z.locator('#order-add-line').click();z.locator('[data-product]').nth(1).select_option('1');z.locator('[data-amount]').nth(1).fill('2');z.locator('[data-unit]').nth(1).select_option('bottle');expect(z.locator('#order-preview')).to_contain_text('8 botellas');capture(z,'orders-mixed-mobile');z.locator('#order-save').click();synced(z);assert stock(z)['total']==120;assert stock(z,'ORD-CUP')['total']==59
  z.locator('[data-order-filter="pending"]').click();expect(z.locator('.order-record')).to_have_count(1);z.locator('[data-order-filter="delivered"]').click();expect(z.locator('.order-record')).to_have_count(0);z.locator('[data-order-filter="all"]').click()
  z.locator('.order-dates summary').click();z.locator('#orders-filter-from').fill('2099-01-01');expect(z.locator('.order-record')).to_have_count(0);z.locator('#orders-filter-from').fill('');expect(z.locator('.order-record')).to_have_count(1)
  # Invalid fractional bottles cannot be submitted; quantity is preserved for correction.
  z.locator('[data-edit-order]').click();z.locator('[data-unit]').first.select_option('bottle');z.locator('[data-amount]').first.fill('0.5');z.locator('#order-save').click();expect(z.locator('#order-error')).to_contain_text('completas');z.locator('#order-discard').click()
  saved=z.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')
  for k in ['lots','moves','contacts','materials','supplies','expenses','documents']:assert saved.get(k)==seed.get(k),k
  assert not saved.get('lotSales'),'Delivery did not invent a sale';assert not saved.get('lotSampleActions')
  reader=browser.new_context(viewport={'width':390,'height':844});r=reader.new_page();r.goto(BASE+'orders.html?partner=mario');login(r,'test-reader');expect(r.locator('#partner-report-app')).to_be_visible();expect(r.locator('#partner-report-state')).to_contain_text('Actualizado',timeout=20000);expect(r.locator('#order-new')).to_have_count(0);expect(r.locator('[data-deliver]')).to_have_count(0);expect(r.locator('.order-record')).to_have_count(0)
  # Both client platforms generate the aggregate report with a distinct order-exit section.
  a.goto(BASE+'orders.html?partner=ricardo');synced(a)
  for page,label in [(a,'PC'),(z,'iPhone')]:
   with page.expect_download() as event:page.locator('#eb-report-pdf').click()
   path=OUT/('orders-summary-'+label+'.pdf');event.value.save_as(str(path));page.locator('#eb-pdf-ready button',has_text='Volver').click()
   import pymupdf
   doc=pymupdf.open(path);text=' '.join(pg.get_text() for pg in doc);assert 'Salidas por pedidos' in text
   for i,pg in enumerate(doc):
    if 'Salidas por pedidos' in pg.get_text():pg.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(OUT/('orders-report-'+label+'.png'))
  # Lot view uses the same balance and explains deliveries instead of artificial differences.
  a.goto(BASE);synced(a);a.evaluate("window.EBSimpleUI.open('ORD-CUP')");expect(a.locator('#simple-current')).to_have_text('59');expect(a.locator('#simple-difference')).to_have_text('0');expect(a.locator('.simple-account-note')).to_contain_text('Entregadas por pedido: 1');capture(a,'orders-lot-balance')
  assert not errors,errors
  print('PASS ORDERS BROWSER: pending/delivered/edit/revert/cancel; 3 partners; mixed varieties; date/status filters; real PC-WebKit sync; EB2 read-only; same lot stock; PDF aggregate; no unrelated data changes.')
  pc.close();phone.close();reader.close();webkit.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
