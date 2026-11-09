import json,os,shutil,subprocess,tempfile,time,urllib.request,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE='http://127.0.0.1:8773/'
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-office-review'));OUT.mkdir(exist_ok=True,parents=True)
root=Path.cwd();seed=json.loads(Path('/tmp/eb-office-fixture.json').read_text());public=Path(tempfile.mkdtemp(prefix='eb-office-public-'))
seed['sales']=[{'client':'PRIVATE-LEGACY-BUYER','amount':321,'currency':'MXN'}]
for f in root.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:shutil.copy(f,public/f.name)
shutil.copy(root/'index.html',public/'legacy.html');shutil.copy(root/'control.html',public/'index.html')
for d in ['vendor','icons']:shutil.copytree(root/d,public/d,dirs_exist_ok=True)
code="const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='45'.repeat(16),hash=crypto.scryptSync('only-test-password',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=[{username:'test-editor',name:'Prueba EB1',role:'editor',salt,hash},{username:'test-reader',name:'Prueba EB2',role:'reader',salt,hash}];createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-office-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8773'],secure:false}).server.listen(8773,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(public)})
for _ in range(60):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def login(page,user='test-editor'):
 expect(page.locator('#eb-user')).to_be_visible();page.locator('#eb-user').fill(user);page.locator('#eb-password').fill('only-test-password');page.locator('#eb-enter').click()
def synced(page):
 page.wait_for_function("()=>window.EBShared&&!window.EBShared.pending&&document.getElementById('eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=25000)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
  pc=browser.new_context(viewport={'width':1440,'height':1000});a=pc.new_page();errors=[];a.on('pageerror',lambda e:errors.append(str(e)))
  pc.add_init_script("if(!localStorage.getItem('eb-v1'))localStorage.setItem('eb-v1',"+json.dumps(json.dumps(seed))+");")
  a.goto(BASE);login(a);a.locator('#eb-publish').click();synced(a)
  a.locator('.sidebar [data-office="summary"]').click();synced(a)
  expect(a.locator('#office-app h1')).to_have_text('Dónde estamos parados')
  expect(a.locator('#office-app')).to_contain_text('1,483')
  for t in ['Ventas por cliente','Prueba México','Prueba USA','PRIVATE-LEGACY-BUYER']:expect(a.locator('#office-app')).not_to_contain_text(t)
  with a.expect_download() as event:a.locator('#office-pdf').click()
  event.value.save_as(str(OUT/'resumen-prueba-PC.pdf'));expect(a.locator('#eb-pdf-ready')).to_be_visible();expect(a.locator('#eb-pdf-ready a[download]')).to_have_attribute('download',re.compile(r'.*resumen-general.*\.pdf'))
  a.locator('#eb-pdf-ready button',has_text='Volver').click();a.screenshot(path=str(OUT/'resumen-pc.png'),full_page=True)
  a.locator('.sidebar [data-office="contacts"]').click();synced(a)
  a.locator('#contact-new').click();expect(a.locator('#contact-name')).to_have_value('');a.locator('#contact-country').select_option('USA');a.locator('#contact-name').fill('Jane Contacto');a.locator('#contact-place').fill('Austin');a.locator('#contact-email').fill('jane@example.test');a.locator('#contact-phone').fill('+1 512 555 0101');a.locator('#contact-save').click();synced(a)
  expect(a.locator('#contact-list')).to_contain_text('Jane Contacto');expect(a.locator('#contact-list')).not_to_contain_text('Tienda vieja')
  wb=p.webkit.launch(headless=True);phone=wb.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);z=phone.new_page();z.on('pageerror',lambda e:errors.append(str(e)))
  z.goto(BASE+'office.html?section=contacts');login(z);synced(z);z.locator('[data-country="USA"]').click();expect(z.locator('#contact-list')).to_contain_text('Jane Contacto');z.locator('[data-contact-edit="1"]').click();z.locator('#contact-phone').fill('+1 512 555 0102');z.locator('#contact-save').click();synced(z)
  a.wait_for_function("()=>JSON.parse(localStorage.getItem('eb-v1')).contacts.some(x=>x.phone==='+1 512 555 0102')",timeout=20000)
  expect(a.locator('#contact-list')).to_contain_text('+1 512 555 0102')
  z.locator('[data-country="Singapur"]').click();expect(z.locator('.empty')).to_be_visible();z.locator('#contact-new').click();z.locator('#contact-name').fill('Singapur prueba');z.locator('#contact-place').fill('East West · prueba');z.locator('#contact-save').click();synced(z)
  z.locator('[data-country="Todos"]').click();expect(z.locator('.office-contact')).to_have_count(3)
  z.locator('#contact-search').fill('Austin');expect(z.locator('.office-contact')).to_have_count(1);z.locator('#contact-search').fill('')
  assert z.evaluate('document.documentElement.scrollWidth <= innerWidth');z.screenshot(path=str(OUT/'contactos-iphone.png'),full_page=True)
  z.goto(BASE+'office.html?section=summary');synced(z)
  with z.expect_download() as event:z.locator('#office-pdf').click()
  event.value.save_as(str(OUT/'resumen-prueba-iPhone.pdf'));expect(z.locator('#eb-pdf-ready a',has_text='Abrir PDF')).to_be_visible();z.locator('#eb-pdf-ready button',has_text='Volver').click();z.screenshot(path=str(OUT/'resumen-iphone.png'),full_page=True)
  saved=z.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')
  for k in ['lots','moves','lotSales','lotSampleActions','materials','supplies','expenses','sales']:assert saved.get(k)==seed.get(k),k
  import pymupdf
  for name in ['PC','iPhone']:
   doc=pymupdf.open(OUT/('resumen-prueba-'+name+'.pdf'));text=' '.join((' '.join(page.get_text() for page in doc)).split())
   for t in ['Dónde estamos parados','1,483','Ventas','10,000.00','250.00','Gorras','Tapones','USD','México']:assert t in text,(name,t)
   for t in ['Dinero: ventas y cobranza','Cobrado registrado','Por cobrar conocido','Pago por aclarar','Ventas y saldos por cliente','Por cobrar','Pagada','Pendiente','Por aclarar','Ventas por cliente','Prueba México','Prueba USA','PRIVATE-LEGACY-BUYER','Jane Contacto','Tienda vieja','jane@example.test']:assert t not in text,(name,'Unexpected buyer or collection information',t)
   assert len(doc)>=2
   for i,page in enumerate(doc):
    for block in page.get_text('dict')['blocks']:
     if 'lines' not in block:continue
     for line in block['lines']:
      x0,y0,x1,y1=line['bbox'];assert x0>=0 and y0>=0 and x1<=612.5 and y1<=792.5,(i,line['bbox'])
    page.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(OUT/('pdf-'+name+'-'+str(i+1)+'.png'))
  reader=browser.new_context(viewport={'width':390,'height':844});r=reader.new_page();r.goto(BASE+'office.html?section=contacts');login(r,'test-reader');expect(r.locator('#partner-report-app')).to_be_visible();expect(r.locator('#partner-report-state')).to_contain_text('Actualizado',timeout=20000);expect(r.locator('#contact-new')).to_have_count(0);expect(r.locator('[data-contact-edit]')).to_have_count(0);expect(r.locator('.office-contact')).to_have_count(0);assert reader.request.get(BASE+'api/state').status==403
  a.goto(BASE+'legacy.html');synced(a);a.evaluate("go('Reporte socios')");a.wait_for_url('**/office.html?section=summary');synced(a)
  a.goto(BASE+'materials.html?kind=supplies');synced(a)
  with a.expect_download() as event:a.locator('#eb-report-pdf').click()
  event.value.save_as(str(OUT/'resumen-desde-insumos.pdf'))
  assert not errors,errors
  print('PASS OFFICE: partner PDF has aggregate sales only, with no buyer list or collection statuses; original buyers/payments/inventories preserved; PC/WebKit downloads, contacts, bidirectional sync, EB2 read-only, navigation and page bounds.')
  pc.close();phone.close();reader.close();wb.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
