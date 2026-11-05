import json,os,shutil,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE='http://127.0.0.1:8770/'
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-shared-checks'));OUT.mkdir(exist_ok=True,parents=True)
seed=json.loads(Path('/tmp/eb-report-fixture.json').read_text())
root=Path.cwd();public=Path(tempfile.mkdtemp(prefix='eb-public-'))
for f in root.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:shutil.copy(f,public/f.name)
shutil.copy(root/'index.html',public/'legacy.html');shutil.copy(root/'control.html',public/'index.html')
for d in ['vendor','icons']:shutil.copytree(root/d,public/d,dirs_exist_ok=True)
code="const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='34'.repeat(16),hash=crypto.scryptSync('only-test-password',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=[{username:'test-editor',name:'Socio prueba',role:'editor',salt,hash},{username:'test-reader',name:'Consulta prueba',role:'reader',salt,hash}];createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-ui-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8770'],secure:false}).server.listen(8770,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(public)})
for _ in range(50):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def login(page,user='test-editor'):
 expect(page.locator('#eb-user')).to_be_visible();page.locator('#eb-user').fill(user);page.locator('#eb-password').fill('only-test-password');page.locator('#eb-enter').click()
def wait_synced(page):
 page.wait_for_function("()=>window.EBShared && !window.EBShared.pending && document.getElementById('eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=20000)
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
  pc=b.new_context(viewport={'width':1440,'height':1000});phone=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);reader=b.new_context(viewport={'width':390,'height':844})
  a=pc.new_page();z=phone.new_page();r=reader.new_page();errors=[]
  for page in [a,z,r]:page.on('pageerror',lambda e:errors.append(str(e)))
  pc.add_init_script("if(!localStorage.getItem('eb-v1'))localStorage.setItem('eb-v1',"+json.dumps(json.dumps(seed))+");");a.goto(BASE);login(a)
  expect(a.locator('#eb-publish')).to_be_visible();a.locator('#eb-publish').click();wait_synced(a)
  expect(a.locator('#saved-list')).to_contain_text('PRUEBA-PDF');assert a.evaluate('JSON.parse(localStorage.getItem("eb-before-shared-v1"))')==seed
  z.goto(BASE);login(z);wait_synced(z);assert z.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==seed
  expect(z.locator('#saved-list')).to_contain_text('PRUEBA-PDF')
  a.locator('.sidebar [data-materials="marketing"]').click();wait_synced(a)
  a.locator('#material-name').fill('Prueba sincronizada PC');a.locator('#material-location').select_option('CDMX');a.locator('#material-qty').fill('33');a.locator('#material-cost').fill('3300');a.locator('#material-save').click();wait_synced(a)
  z.wait_for_function("()=>JSON.parse(localStorage.getItem('eb-v1')).materials.some(x=>x.name==='Prueba sincronizada PC')",timeout=20000)
  z.locator('.mobile-nav [data-materials="supplies"]').click();wait_synced(z)
  z.locator('#material-name').select_option('Tapones');z.locator('#material-location').select_option('Oaxaca');z.locator('#material-qty').fill('600');z.locator('#material-cost').fill('4800');z.locator('#material-save').click();wait_synced(z)
  a.wait_for_function("()=>JSON.parse(localStorage.getItem('eb-v1')).supplies.some(x=>x.name==='Tapones'&&x.qty===600)",timeout=20000)
  assert a.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==z.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')
  a.reload();wait_synced(a);z.reload();wait_synced(z);assert a.evaluate('localStorage.getItem("eb-v1")')==z.evaluate('localStorage.getItem("eb-v1")')
  r.goto(BASE);login(r,'test-reader');wait_synced(r);expect(r.locator('#saved-list')).to_contain_text('PRUEBA-PDF')
  assert r.evaluate("(()=>{try{const d=JSON.parse(localStorage.getItem('eb-v1'));d.lots=[];localStorage.setItem('eb-v1',JSON.stringify(d));return false;}catch{return true;}})()")
  expect(r.locator('#list-new')).not_to_be_visible()
  old=b.new_context();old.add_init_script("if(!localStorage.getItem('eb-v1'))localStorage.setItem('eb-v1',"+json.dumps(json.dumps(seed))+");");o=old.new_page();o.goto(BASE);login(o);expect(o.locator('#eb-use-cloud')).to_be_visible();o.locator('#eb-use-cloud').click();wait_synced(o)
  assert o.evaluate('JSON.parse(localStorage.getItem("eb-before-shared-v1"))')==seed
  phone.set_offline(True);z.locator('[data-edit-material="1"]').click();z.locator('#material-qty').fill('610');z.locator('#material-cost').fill('4880');z.locator('#material-save').click()
  z.wait_for_function('()=>window.EBShared.pending');phone.set_offline(False);z.evaluate("dispatchEvent(new Event('online'))");wait_synced(z)
  a.wait_for_function("()=>JSON.parse(localStorage.getItem('eb-v1')).supplies.some(x=>x.name==='Tapones'&&x.qty===610)",timeout=20000)
  for page,name in [(a,'pc-marketing'),(z,'mobile-insumos'),(r,'mobile-consulta')]:
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),name
   page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
  # Generate PDFs from the same shared snapshot in both sessions.
  import pymupdf
  for page,name in [(a,'pc'),(z,'mobile')]:
   page.goto(BASE);wait_synced(page)
   with page.expect_download() as event:page.locator('#eb-report-pdf').click()
   pdf=OUT/(name+'-shared.pdf');event.value.save_as(str(pdf));doc=pymupdf.open(pdf);text=' '.join(' '.join(x.get_text().split()) for x in doc)
   assert 'Prueba sincronizada PC' in text and '610' in text and 'PRUEBA-PDF' in text
   if name=='pc':reference=text
   else:assert text==reference
  assert not errors,errors
  print('PASS TWO DEVICES: initial PC migration, automatic phone read, bidirectional edits, refresh persistence, EB2 read-only, old-copy protection, offline recovery and equal PDF data.')
  for ctx in [pc,phone,reader,old]:ctx.close()
  b.close()
finally:
 server.terminate();server.wait(timeout=10)
