import json,os,shutil,subprocess,tempfile,time,urllib.request,base64
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path(os.environ.get('EB_DOC_SCREENSHOTS','/tmp/eb-documents-review'));OUT.mkdir(exist_ok=True,parents=True)
PUB=Path(tempfile.mkdtemp(prefix='eb-doc-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.html','.js','.css','.jpg','.webmanifest']:shutil.copy(f,PUB/f.name)
shutil.copy(ROOT/'index.html',PUB/'legacy.html');shutil.copy(ROOT/'control.html',PUB/'index.html')
for name in ['vendor','icons']:
 if (ROOT/name).exists():shutil.copytree(ROOT/name,PUB/name)
BASE='http://127.0.0.1:8783/'
code="const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='56'.repeat(16),hash=crypto.scryptSync('only-test-password',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=[{username:'test-editor',name:'Prueba EB1',role:'editor',salt,hash},{username:'test-reader',name:'Prueba EB2',role:'reader',salt,hash}];createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-doc-ui-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8783'],secure:false}).server.listen(8783,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(PUB)})
for _ in range(50):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
seed={'lots':[{'id':'DOC-TEST','p':0,'bottles':60,'unitCost':200,'totalCost':12000,'ml':720}],'moves':[],'contacts':[],'materials':[],'supplies':[],'documents':[{'name':'Anterior conservado','type':'CRM','link':'https://example.test/previous'}]}
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jGZkAAAAASUVORK5CYII=')
file=OUT/'certificado-prueba.png';file.write_bytes(png)
def login(page,user='test-editor'):
 expect(page.locator('#eb-user')).to_be_visible();page.locator('#eb-user').fill(user);page.locator('#eb-password').fill('only-test-password');page.locator('#eb-enter').click()
def ready(page):
 page.wait_for_function("()=>window.EBShared&&document.getElementById('eb-cloud-state')?.textContent.startsWith('Actualizado')")
 expect(page.locator('#docs-categories .docs-category')).to_have_count(5)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
  desktop=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);a=desktop.new_page();errors=[];a.on('pageerror',lambda e:errors.append(str(e)))
  desktop.add_init_script("if(!localStorage.getItem('eb-v1'))localStorage.setItem('eb-v1',"+json.dumps(json.dumps(seed))+");")
  a.goto(BASE+'documents.html');login(a);a.locator('#eb-publish').click();ready(a)
  a.locator('[data-category="Certificados"]').click();a.locator('#docs-new').click();expect(a.locator('#doc-category')).to_have_value('Certificados');a.locator('#doc-file').set_input_files(str(file));a.locator('#doc-title').fill('Certificado CRM · Prueba');a.locator('.docs-optional summary').click();a.locator('#doc-lot').select_option('DOC-TEST');a.locator('#doc-expiry').fill('2020-01-01');a.locator('#doc-notes').fill('Datos de prueba aislados, no productivos.');a.locator('#doc-save').click()
  expect(a.locator('#docs-dialog')).to_have_count(0);expect(a.locator('.docs-file')).to_have_count(1);expect(a.locator('#docs-alerts')).to_contain_text('1 vencido');expect(a.locator('.docs-file')).to_contain_text('Vencido')
  with a.expect_download() as e:a.locator('.docs-file a',has_text='Descargar').click()
  assert Path(e.value.path()).read_bytes()==png
  a.locator('[data-edit-doc]').click();a.locator('#doc-category').select_option('IMPI');a.locator('#doc-title').fill('Registro de marca · Prueba');a.locator('#doc-expiry').fill('2028-01-01');a.locator('#doc-save').click();expect(a.locator('#docs-dialog')).to_have_count(0);expect(a.locator('#docs-title')).to_have_text('Certificados');expect(a.locator('.docs-file')).to_have_count(0);a.locator('[data-category="IMPI"]').click();expect(a.locator('.docs-file')).to_contain_text('Vigente');expect(a.locator('#docs-title')).to_have_text('IMPI')
  a.locator('[data-category="Certificados"]').click();expect(a.locator('.docs-file')).to_have_count(0);a.locator('#docs-all').click();expect(a.locator('.docs-file')).to_have_count(1)
  a.screenshot(path=str(OUT/'documents-desktop.png'),full_page=True)
  phone=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,accept_downloads=True);b=phone.new_page();b.on('pageerror',lambda e:errors.append(str(e)));b.goto(BASE+'documents.html');login(b);ready(b);expect(b.locator('.docs-file')).to_contain_text('Registro de marca · Prueba')
  b.locator('[data-category="Análisis de laboratorio"]').click();b.locator('#docs-new').click();b.locator('#doc-file').set_input_files(str(file));b.locator('#doc-title').fill('Análisis de lote · Prueba');b.locator('.docs-optional summary').click();today=b.evaluate("new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())");b.locator('#doc-expiry').fill(today)
  b.screenshot(path=str(OUT/'documents-upload-mobile.png'),full_page=True);b.locator('#doc-save').click();expect(b.locator('#docs-dialog')).to_have_count(0);expect(b.locator('#docs-alerts')).to_contain_text('1 por vencer');a.locator('#docs-refresh').click();expect(a.locator('.docs-file')).to_have_count(2)
  b.locator('#docs-all').click();assert b.evaluate('document.documentElement.scrollWidth <= innerWidth');b.screenshot(path=str(OUT/'documents-mobile.png'),full_page=True)
  b.on('dialog',lambda d:d.accept());b.locator('[data-delete-doc]').first.click();expect(b.locator('.docs-file')).to_have_count(1);b.locator('#docs-trash').click();expect(b.locator('[data-restore]')).to_have_count(1);b.locator('[data-restore]').click();expect(b.locator('[data-restore]')).to_have_count(0);b.locator('#docs-all').click();expect(b.locator('.docs-file')).to_have_count(2)
  b.locator('#docs-search').fill('Registro de marca');expect(b.locator('.docs-file')).to_have_count(1);b.locator('#docs-search').fill('')
  reader=browser.new_context(viewport={'width':390,'height':844},accept_downloads=True);c=reader.new_page();c.goto(BASE+'documents.html');login(c,'test-reader');expect(c.locator('#partner-report-app')).to_be_visible();expect(c.locator('#partner-report-state')).to_contain_text('Actualizado',timeout=20000)
  assert reader.request.get(BASE+'api/documents').status==403;expect(c.locator('.docs-file')).to_have_count(0)
  assert b.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==seed
  a.goto(BASE);a.wait_for_function("()=>window.EBShared&&document.getElementById('eb-cloud-state')?.textContent.startsWith('Actualizado')");a.locator('.side-nav [data-office="documents"]').click();ready(a)
  b.goto(BASE);b.wait_for_function("()=>window.EBShared&&document.getElementById('eb-cloud-state')?.textContent.startsWith('Actualizado')");b.locator('.mobile-nav [data-office="documents"]').click();ready(b)
  assert not errors,errors
  for ctx in [desktop,phone,reader]:ctx.close()
  browser.close()
finally:server.terminate();server.wait(timeout=10)
print('PASS DOCUMENTS UI: five categories, desktop/mobile real shared backend, upload/download bytes, edits, filtering, expired/30-day alerts, trash/restore, EB2 reader, navigation and all original business data unchanged.')
