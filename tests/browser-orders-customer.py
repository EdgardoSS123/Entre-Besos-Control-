import json, os, shutil, subprocess, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
BASE='http://127.0.0.1:8785/'
ROOT=Path.cwd(); OUT=Path(os.environ.get('EB_CUSTOMER_REVIEW','/tmp/eb-orders-customer-review')); OUT.mkdir(parents=True,exist_ok=True)
seed=json.loads(Path('/tmp/eb-orders-fixture.json').read_text())
seed['contacts']=[{'country':'México','name':'Ana Prueba','place':'Restaurante Prueba','email':'ana@example.test','phone':''}]
public=Path(tempfile.mkdtemp(prefix='eb-customer-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']: shutil.copy(f,public/f.name)
shutil.copy(ROOT/'control.html',public/'index.html')
for folder in ['vendor','icons']: shutil.copytree(ROOT/folder,public/folder,dirs_exist_ok=True)
code="const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='56'.repeat(16),hash=crypto.scryptSync('recipient-test-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=[{username:'test-editor',name:'Prueba EB1',role:'editor',salt,hash},{username:'test-reader',name:'Prueba EB2',role:'reader',salt,hash}];createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-customer-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8785'],secure:false}).server.listen(8785,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(public)})
for _ in range(60):
 try: urllib.request.urlopen(BASE+'healthz',timeout=1); break
 except Exception: time.sleep(.1)
def synced(p):
 p.wait_for_function("()=>window.EBShared&&!window.EBShared.pending&&document.getElementById('eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=25000)
def login(p,user='test-editor'):
 p.locator('#eb-user').fill(user);p.locator('#eb-password').fill('recipient-test-only');p.locator('#eb-enter').click()
def state(p): return p.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
  pc=browser.new_context(viewport={'width':1440,'height':1000});a=pc.new_page();errors=[];a.on('pageerror',lambda e:errors.append(str(e)));a.on('dialog',lambda d:d.accept())
  pc.add_init_script("if(!localStorage.getItem('eb-v1'))localStorage.setItem('eb-v1',"+json.dumps(json.dumps(seed))+");")
  a.goto(BASE+'orders.html?partner=edgardo');login(a);a.locator('#eb-publish').click();synced(a)
  a.locator('#order-new').click();expect(a.locator('#order-customer')).to_have_value('');a.locator('[data-amount]').fill('2');a.locator('#order-save').click();expect(a.locator('#order-dialog')).to_be_visible();assert not state(a).get('partnerOrders')
  expect(a.locator('#order-customers option')).to_have_attribute('value','Ana Prueba · Restaurante Prueba')
  a.locator('#order-customer').fill('Ana Prueba · Restaurante Prueba');a.screenshot(path=str(OUT/'customer-form-desktop.png'),full_page=True);a.locator('#order-save').click();synced(a)
  expect(a.locator('.order-recipient')).to_contain_text('Ana Prueba · Restaurante Prueba');assert state(a)['partnerOrders'][0]['partner']=='edgardo'
  a.locator('[data-deliver]').click();synced(a);before=state(a)['lotStockAdjustments'];a.locator('[data-edit-order]').click();expect(a.locator('#order-customer')).to_have_value('Ana Prueba · Restaurante Prueba');a.locator('#order-customer').fill('Empresa corregida');a.locator('#order-save').click();synced(a);assert state(a)['lotStockAdjustments']==before
  phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);z=phone.new_page();z.on('pageerror',lambda e:errors.append(str(e)));z.on('dialog',lambda d:d.accept())
  z.goto(BASE+'orders.html?partner=edgardo');login(z);synced(z);expect(z.locator('.order-recipient')).to_contain_text('Empresa corregida');z.locator('[data-edit-order]').click();expect(z.locator('#order-customer')).to_have_value('Empresa corregida');z.locator('#order-customer').fill('Cliente libre móvil');z.screenshot(path=str(OUT/'customer-form-mobile.png'),full_page=True);z.locator('#order-save').click();synced(z)
  a.wait_for_function("()=>JSON.parse(localStorage.getItem('eb-v1')).partnerOrders[0].customer==='Cliente libre móvil'",timeout=20000)
  expect(a.locator('.order-recipient')).to_contain_text('Cliente libre móvil');assert state(a)['lotStockAdjustments']==before
  z.reload();synced(z);expect(z.locator('.order-recipient')).to_contain_text('Cliente libre móvil');assert z.evaluate('document.documentElement.scrollWidth <= innerWidth')
  z.screenshot(path=str(OUT/'customer-card-mobile.png'),full_page=True)
  z.locator('[data-pending]').click();synced(z);expect(z.locator('.order-recipient')).to_contain_text('Cliente libre móvil');assert z.evaluate("window.EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'ORD-ESP').total")==120
  z.locator('[data-edit-order]').click();z.locator('#order-customer').fill('<img src=x onerror="window.customerXSS=1">');z.locator('#order-save').click();synced(z);expect(z.locator('.order-recipient img')).to_have_count(0);assert not z.evaluate('Boolean(window.customerXSS)')
  for k in ['lots','moves','contacts','materials','supplies','expenses','documents']:assert state(z).get(k)==seed.get(k),k
  assert not z.evaluate("JSON.stringify(window.EBExecutive.build(JSON.parse(localStorage.getItem('eb-v1')),window.EBLedger).sections).includes('customerXSS')")
  reader=browser.new_context(viewport={'width':390,'height':844});r=reader.new_page();r.goto(BASE+'orders.html?partner=edgardo');login(r,'test-reader');expect(r.locator('#partner-report-app')).to_be_visible();expect(r.locator('#partner-report-state')).to_contain_text('Actualizado',timeout=20000);expect(r.locator('.order-recipient')).to_have_count(0);expect(r.locator('[data-edit-order]')).to_have_count(0);assert reader.request.get(BASE+'api/state').status==403
  assert not errors,errors
  print('PASS browser recipient: blank validation, contacts suggestions/free text, save/edit/reload, PC-mobile sync, stock debits unchanged, safe HTML, PDF model excludes recipients, EB2 remains read-only.')
  reader.close();phone.close();pc.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
