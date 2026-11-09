"""Local isolated workspace only. Never accesses production or user credentials."""
import json,os,shutil,subprocess,tempfile,time,urllib.request,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path(os.environ.get('EB_REVIEW','/tmp/eb-save-return-review'));OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8791/';PUB=Path(tempfile.mkdtemp(prefix='eb-return-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:shutil.copy(f,PUB/f.name)
shutil.copy(ROOT/'control.html',PUB/'index.html');shutil.copy(ROOT/'index.html',PUB/'legacy.html')
for folder in ['vendor','icons']:shutil.copytree(ROOT/folder,PUB/folder,dirs_exist_ok=True)
seed_code="""
let I=require('./inventory-core.js');I=require('./commerce-core.js')(I);I=require('./simple-core.js')(I);I=require('./corrections-core.js')(I);
const day='2026-11-01',stamp=day+'T18:00:00Z';let d={lots:[{id:'RETURN-A',p:0,bottles:200,ml:720,unitCost:144,totalCost:28800,liquid:200,date:day,producedLiters:144,lossLiters:0,productionMode:'liters',originWarehouse:'CDMX'},{id:'RETURN-B',p:1,bottles:100,ml:720,unitCost:144,totalCost:14400,liquid:200,date:day}],moves:[],contacts:[{id:'contact-test',country:'USA',name:'Persona prueba',place:'Empresa prueba',email:'test@example.test',phone:''}],materials:[{id:'mat-1',name:'Gorras de prueba',qty:10,totalCost:300,loc:'CDMX',unit:'unidades'}],supplies:[{id:'ins-1',name:'Tapones',qty:20,totalCost:200,loc:'Oaxaca',unit:'unidades'}],expenses:[],documents:[]};
d=I.initializeOrigin(d,'RETURN-A','CDMX',day,stamp);d=I.initializeOrigin(d,'RETURN-B','Oaxaca',day,stamp);
d=I.sellStock(d,'RETURN-A',{id:'sale-return',from:'CDMX',tag:'Por clasificar',amount:3,unit:'box',price:'800',priceBasis:'bottle',currency:'MXN',customer:'Cliente prueba',payment:'pending',stamp},day);
d=I.addPayment(d,'RETURN-A','sale-return',{id:'pay-return',amount:'100',date:day,reference:'Prueba',stamp},day);
d=I.moveStock(d,'RETURN-A',{id:'move-return',from:'CDMX',to:'Oaxaca',tag:'Por clasificar',amount:6,unit:'bottle',cost:'0',currency:'MXN',stamp},day);
d=I.deliverSamples(d,'RETURN-A',{id:'sample-return',from:'CDMX',tag:'Por clasificar',amount:2,unit:'bottle',stockType:'commercial',notes:'Prueba',stamp},day);
const O=require('./orders-core.js');d=O.save(d,{partner:'edgardo',customer:'Destinatario prueba',from:'CDMX',date:day,status:'pending',notes:'Antes',lines:[{product:0,lotId:'RETURN-A',amount:1,unit:'box'}]},{id:'order-return',operation:'operation-return-test',day,stamp,actor:'test-editor'},I).data;
console.log(JSON.stringify(d));
"""
seed=json.loads(subprocess.check_output(['node','-e',seed_code],text=True))
code="const crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {createApp}=require('./server.cjs');const salt='43'.repeat(16),hash=crypto.scryptSync('save-return-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=[{username:'test-editor',name:'Prueba',role:'editor',salt,hash}];createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-return-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8791'],secure:false}).server.listen(8791,'127.0.0.1');"
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(PUB)},stdout=subprocess.DEVNULL)
for _ in range(60):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def ready(page):
 page.wait_for_function("()=>window.EBShared&&!window.EBShared.pending&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=20000)
def login(ctx):
 r=ctx.request.post(BASE+'api/login',data={'username':'test-editor','password':'save-return-only'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
def seed_state(ctx,csrf):
 r=ctx.request.get(BASE+'api/state').json();res=ctx.request.put(BASE+'api/state',data={'revision':r['revision'],'initialize':True,'operation':'seed-return-'+str(time.time_ns()),'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':csrf});assert res.ok,res.text()
def save_correction(page,field,value):
 page.locator(field).fill(value);page.locator('dialog.correction-modal [data-save]').click();expect(page.locator('dialog.correction-modal')).to_have_count(0);ready(page)
def history(page):
 page.locator('.simple-history').evaluate('(e)=>e.open=true');page.locator('#history-warehouse').select_option('CDMX')
def no_overflow(page):assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
try:
 with sync_playwright() as p:
  engines=[('chromium',p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox']))]
  if os.environ.get('EB_WEBKIT')=='1':engines.append(('webkit',p.webkit.launch(headless=True)))
  for engine,browser in engines:
   for width in ([1440,390] if engine=='chromium' else [390]):
    ctx=browser.new_context(viewport={'width':width,'height':844},is_mobile=width<700,has_touch=width<700);csrf=login(ctx);seed_state(ctx,csrf)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
    page.goto(BASE);ready(page);page.locator('[data-simple-open="RETURN-A"]').click();page.locator('#simple-move-tab').click();history(page)
    b=page.locator('[data-record-edit="sale-return"][data-kind="sale"]');b.scroll_into_view_if_needed();before=page.evaluate('scrollY');b.click();page.locator('#edit-price').fill('850');page.screenshot(path=str(OUT/f'sale-edit-{engine}-{width}.png'))
    save_correction(page,'#edit-customer','Cliente editado');expect(page.locator('#history-warehouse')).to_have_value('CDMX');expect(page.locator('#simple-move-tab')).to_have_class('active');assert page.locator('.simple-history').evaluate('(e)=>e.open');assert abs(page.evaluate('scrollY')-before)<45,(before,page.evaluate('scrollY'))
    expect(page.locator('.simple-history')).to_contain_text('Cliente editado');assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1")).lotSales[0].priceCents')==85000;page.screenshot(path=str(OUT/f'sale-return-{engine}-{width}.png'))
    # Invalid correction keeps its dialog and typed data, and never writes.
    b.click();original=page.evaluate('localStorage.getItem("eb-v1")');page.locator('#edit-amount').fill('0.5');page.locator('#edit-unit').select_option('bottle');page.locator('dialog [data-save]').click();expect(page.locator('dialog[open]')).to_have_count(1);expect(page.locator('#edit-amount')).to_have_value('0.5');assert page.evaluate('localStorage.getItem("eb-v1")')==original;page.locator('dialog [data-cancel]').click()
    # Movement, samples, payments and existing stock all close and return to history/context.
    page.locator('[data-record-edit="move-return"]').click();save_correction(page,'#edit-amount','7');assert page.locator('.simple-history').evaluate('(e)=>e.open')
    page.locator('[data-record-edit="sample-return"]').click();save_correction(page,'#edit-amount','3')
    page.locator('.record-payments').evaluate('(e)=>e.open=true');page.locator('[data-record-edit="sale-return"][data-kind="payment"]').click();save_correction(page,'#edit-payment','150');assert page.locator('.record-payments').evaluate('(e)=>e.open')
    page.locator('[data-stock-edit]').first.click();page.locator('dialog [data-save]').click();expect(page.locator('dialog.correction-modal')).to_have_count(0);ready(page)
    # Low-storage failures leave the editor open.
    page.locator('[data-record-edit="sale-return"][data-kind="sale"]').click();page.locator('#edit-customer').fill('Captura conservada');page.evaluate("()=>{window.testSet=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='eb-v1')throw Error('Sin espacio de prueba');return window.testSet.call(this,k,v)}}")
    page.locator('dialog [data-save]').click();expect(page.locator('dialog [data-error]')).to_contain_text('Sin espacio');expect(page.locator('#edit-customer')).to_have_value('Captura conservada');page.evaluate('()=>{Storage.prototype.setItem=window.testSet}');page.locator('dialog [data-cancel]').click()
    # Lot cost edit returns to detailed lot, not to Mis lotes.
    page.locator('#simple-costs').click();page.locator('#liquid').fill('201');page.locator('#save-lot').click();expect(page.locator('#simple-produced')).to_be_visible();expect(page.locator('#simple-move-tab')).to_have_class('active');ready(page)
    # Editing from a filtered lot list returns to that list and its filter.
    page.locator('#simple-back').click();page.locator('#search-lots').fill('RETURN-A');page.locator('[data-edit="RETURN-A"]').click();page.locator('#liquid').fill('202');page.locator('#save-lot').click();expect(page.locator('#search-lots')).to_have_value('RETURN-A');expect(page.locator('.saved-lot')).to_have_count(1);ready(page)
    # Contacts and both materials screens return to the same country/bodega/search.
    page.goto(BASE+'office.html?section=contacts&country=USA');ready(page);page.locator('#contact-search').fill('Persona');page.locator('[data-contact-edit="0"]').click();page.locator('#contact-phone').fill('+1 555 0100');page.locator('#contact-save').click();expect(page.locator('#contact-editor')).to_be_hidden();expect(page.locator('#contact-search')).to_have_value('Persona');ready(page)
    for kind,where,term in [('marketing','CDMX','Gorras'),('supplies','Oaxaca','Tapones')]:
     page.goto(BASE+'materials.html?kind='+kind);ready(page);page.locator('#material-filter').select_option(where);page.locator('#material-search').fill(term);page.locator('[data-edit-material="0"]').click();page.locator('#material-qty').fill('12');page.locator('#material-save').click();expect(page.locator('#material-filter')).to_have_value(where);expect(page.locator('#material-search')).to_have_value(term);expect(page.locator('#material-form-title')).to_have_text('Nueva captura');ready(page)
    # Orders: recipient-only editing neither duplicates delivery nor loses the state filter.
    page.goto(BASE+'orders.html?partner=edgardo');ready(page);page.locator('[data-order-filter="pending"]').click();page.locator('[data-edit-order]').click();page.locator('#order-customer').fill('Cliente de pedido editado');page.locator('#order-save').click();expect(page.locator('#order-dialog')).to_have_count(0);expect(page.locator('[data-order-filter="pending"]')).to_have_class('selected');ready(page)
    # Document metadata uses the same success rule, with server confirmation.
    res=ctx.request.post(BASE+'api/documents',headers={'Origin':BASE[:-1],'X-EB-CSRF':csrf},data={'id':str(uuid.uuid4()),'filename':'prueba.pdf','title':'Certificado de prueba','category':'Certificados','lot':'','expiry':'','notes':'','base64':'JVBERi0xLjQKJSBUZXN0CiUlRU9GCg=='});assert res.ok,res.text()
    page.goto(BASE+'documents.html');ready(page);page.locator('#docs-search').fill('Certificado');page.locator('#docs-status').select_option('none');page.locator('[data-edit-doc]').first.click();page.locator('#doc-title').fill('Certificado editado');page.locator('#doc-save').click();expect(page.locator('#docs-dialog')).to_have_count(0);expect(page.locator('#docs-search')).to_have_value('Certificado');expect(page.locator('#docs-status')).to_have_value('none');expect(page.locator('#docs-list')).to_contain_text('Certificado editado')
    no_overflow(page);assert not errors,errors;ctx.close();print('PASS SAVE RETURN',engine,width,flush=True)
   browser.close()
finally:server.terminate();server.wait(timeout=10)
