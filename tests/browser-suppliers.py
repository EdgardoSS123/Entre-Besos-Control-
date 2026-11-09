"""Synthetic supplier data and temporary SQLite only. Never accesses production records."""
import json,os,shutil,subprocess,tempfile,time,urllib.request,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path('/tmp/eb-suppliers-review');OUT.mkdir(exist_ok=True,parents=True)
BASE='http://127.0.0.1:8797/';PUB=Path(tempfile.mkdtemp(prefix='eb-supplier-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:shutil.copy(f,PUB/f.name)
shutil.copy(ROOT/'control.html',PUB/'index.html');shutil.copy(ROOT/'index.html',PUB/'legacy.html')
for folder in ['vendor','icons']:shutil.copytree(ROOT/folder,PUB/folder,dirs_exist_ok=True)
seed={'lots':[{'id':'SUP-TEST','p':0,'bottles':12,'ml':720,'unitCost':200,'totalCost':2400}],'moves':[],'contacts':[{'id':'c','country':'USA','name':'No modificar'}],'materials':[{'name':'Gorras','qty':5,'totalCost':150,'loc':'CDMX'}],'supplies':[{'name':'Separadores de prueba','qty':8,'totalCost':100,'loc':'Oaxaca'}],'expenses':[],'partnerOrders':[],'documents':[]}
code="const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='43'.repeat(16),hash=crypto.scryptSync('supplier-test-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=[{username:'test-editor',name:'Prueba EB1',role:'editor',salt,hash},{username:'test-reader',name:'Prueba EB2',role:'reader',salt,hash}];createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-supplier-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8797'],secure:false}).server.listen(8797,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(PUB)},stdout=subprocess.DEVNULL)
for _ in range(60):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def ready(page):page.wait_for_function("()=>window.EBShared&&!window.EBShared.pending&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=20000)
def login(ctx,user='test-editor'):
 r=ctx.request.post(BASE+'api/login',data={'username':user,'password':'supplier-test-only'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
def shot(page,name):
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),name
 if page.locator('#supplier-dialog').count():assert page.locator('#supplier-dialog').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1'),name
 page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
  pc=browser.new_context(viewport={'width':1440,'height':1000});csrf=login(pc)
  r=pc.request.put(BASE+'api/state',data={'revision':0,'operation':str(uuid.uuid4()),'initialize':True,'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':csrf});assert r.ok,r.text()
  errors=[];page=pc.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
  page.goto(BASE);ready(page);page.locator('.sidebar [data-office="suppliers"]').click();ready(page);expect(page.locator('h1')).to_have_text('Proveedores')
  page.locator('#supplier-new').click()
  for f in ['name','phone','email','contact','place']:expect(page.locator('#supplier-'+f)).to_have_value('')
  assert 'Separadores de prueba' in page.locator('#supplier-item').inner_text()
  page.locator('#supplier-name').fill('Proveedor de prueba');page.locator('#supplier-item').select_option('Botellas vacías');page.locator('#supplier-item').select_option('Tapones');page.locator('#supplier-item').select_option('__other__');expect(page.locator('#supplier-other')).to_have_value('');page.locator('#supplier-other').fill('Empaques de prueba');page.locator('#supplier-add-other').click();expect(page.locator('.supplier-picked')).to_have_count(3)
  page.locator('#supplier-contact').fill('Persona de prueba');page.locator('#supplier-phone').fill('+52 555 555 0100');page.locator('#supplier-email').fill('proveedor@example.test');page.locator('#supplier-place').fill('Oaxaca');shot(page,'supplier-form-desktop')
  page.locator('#supplier-save').click();expect(page.locator('#supplier-dialog')).to_have_count(0);ready(page);expect(page.locator('.supplier-card')).to_have_count(1);expect(page.locator('#supplier-message')).to_contain_text('Confirmado',timeout=20000);shot(page,'supplier-list-desktop')
  data=pc.request.get(BASE+'api/state').json()['data'];assert len(data['suppliers'])==1
  for k in seed:assert data[k]==seed[k],k
  page.reload();ready(page);expect(page.locator('.supplier-card')).to_have_count(1)
  page.locator('#supplier-filter').select_option('Tapones');page.locator('#supplier-search').fill('Proveedor');page.locator('[data-supplier-edit]').click();page.locator('#supplier-contact').fill('Contacto corregido');page.locator('#supplier-save').click();expect(page.locator('#supplier-dialog')).to_have_count(0);ready(page);expect(page.locator('#supplier-filter')).to_have_value('Tapones');expect(page.locator('#supplier-search')).to_have_value('Proveedor');expect(page.locator('.supplier-card')).to_contain_text('Contacto corregido')
  # Duplicate and invalid records retain the form; original record is unchanged.
  page.locator('#supplier-new').click();page.locator('#supplier-name').fill('Proveedor de prueba');page.locator('#supplier-place').fill('Oaxaca');page.locator('#supplier-item').select_option('Tapones');page.locator('#supplier-save').click();expect(page.locator('#supplier-error')).to_contain_text('ya está registrado');expect(page.locator('#supplier-dialog')).to_be_visible();page.locator('#supplier-cancel').click()
  # Simulated storage failure must keep the user's input, not close or alter saved data.
  page.locator('[data-supplier-edit]').click();page.locator('#supplier-phone').fill('99999');page.evaluate("()=>{window.supplierTestSet=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='eb-v1')throw new DOMException('Sin espacio','QuotaExceededError');return window.supplierTestSet.call(this,k,v)};}")
  page.locator('#supplier-save').click();expect(page.locator('#supplier-error')).to_contain_text('No se guardó');expect(page.locator('#supplier-phone')).to_have_value('99999');page.evaluate('()=>{Storage.prototype.setItem=window.supplierTestSet;delete window.supplierTestSet;}');page.locator('#supplier-cancel').click()
  webkit=p.webkit.launch(headless=True);mobile=webkit.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);login(mobile)
  phone=mobile.new_page();phone.on('pageerror',lambda e:errors.append(str(e)));phone.on('dialog',lambda d:d.accept());phone.goto(BASE+'suppliers.html');ready(phone);expect(phone.locator('.supplier-card')).to_have_count(1);expect(phone.locator('.supplier-card')).to_contain_text('Contacto corregido');shot(phone,'supplier-list-mobile')
  phone.locator('[data-supplier-edit]').click();expect(phone.locator('#supplier-phone')).to_have_value('+52 555 555 0100');phone.locator('#supplier-item').select_option('Etiquetas');phone.locator('#supplier-contact').fill('Editado desde celular');shot(phone,'supplier-form-mobile');phone.locator('#supplier-save').click();expect(phone.locator('#supplier-dialog')).to_have_count(0);ready(phone)
  page.wait_for_function("()=>JSON.parse(localStorage.getItem('eb-v1')).suppliers[0].contact==='Editado desde celular'",timeout=20000);expect(page.locator('.supplier-card')).to_contain_text('Editado desde celular')
  phone.locator('[data-supplier-delete]').click();ready(phone);expect(phone.locator('.supplier-card')).to_have_count(0);phone.locator('#supplier-trash').click();expect(phone.locator('.supplier-card')).to_have_count(1);phone.locator('[data-supplier-restore]').click();ready(phone);expect(phone.locator('.supplier-card')).to_have_count(0);phone.locator('#supplier-trash').click();expect(phone.locator('.supplier-card')).to_have_count(1)
  phone.locator('#supplier-filter').select_option('Empaques de prueba');expect(phone.locator('.supplier-card')).to_have_count(1);phone.locator('#supplier-filter').select_option('Corrugados');expect(phone.locator('.supplier-card')).to_have_count(0);phone.locator('#supplier-filter').select_option('');shot(phone,'supplier-restored-mobile')
  # An unadded Otros value is included at Save; no concept is silently discarded.
  phone.locator('#supplier-new').click();phone.locator('#supplier-name').fill('Proveedor 2');phone.locator('#supplier-item').select_option('__other__');phone.locator('#supplier-other').fill('Concepto nuevo sin agregar');phone.locator('#supplier-save').click();expect(phone.locator('#supplier-dialog')).to_have_count(0);ready(phone);expect(phone.locator('.supplier-card')).to_have_count(2)
  reader=browser.new_context(viewport={'width':390,'height':844});token=login(reader,'test-reader');rp=reader.new_page();rp.goto(BASE+'suppliers.html');ready(rp);expect(rp.locator('.supplier-card')).to_have_count(2)
  for selector in ['#supplier-new','[data-supplier-edit]','[data-supplier-delete]','#supplier-trash']:expect(rp.locator(selector)).to_have_count(0)
  current=reader.request.get(BASE+'api/state').json();denied=reader.request.put(BASE+'api/state',data={'revision':current['revision'],'operation':str(uuid.uuid4()),'data':current['data']},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert denied.status==403
  for k in seed:assert current['data'][k]==seed[k],k
  assert not errors,errors
  print('PASS SUPPLIERS UI: real isolated PC/WebKit shared store, multi-insumo and Otros, save-close-return, filters, retry safety, invalid/failed saves retain input, reload, delete/restore, EB2 read-only and unchanged business records.')
  pc.close();mobile.close();reader.close();webkit.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
