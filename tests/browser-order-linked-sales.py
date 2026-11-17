"""Disposable SQLite and browser; synthetic recipients only. No production access."""
import json,os,shutil,subprocess,tempfile,time,urllib.request,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path(os.environ.get('EB_LINKED_REVIEW','/tmp/eb-linked-review'));OUT.mkdir(exist_ok=True,parents=True)
PUB=Path(tempfile.mkdtemp(prefix='eb-linked-public-'));BASE='http://127.0.0.1:8891/'
for f in ROOT.iterdir():
 if f.suffix in ['.html','.js','.css','.jpg','.png','.webmanifest']:shutil.copy(f,PUB/f.name)
for name in ['vendor','icons']:shutil.copytree(ROOT/name,PUB/name)
shutil.copy(ROOT/'control.html',PUB/'index.html')
seed={'orderSalesVersion':1,'lots':[{'id':'ESP','p':0,'bottles':120,'ml':720,'unitCost':200,'totalCost':24000},{'id':'CUP','p':1,'bottles':60,'ml':720,'unitCost':300,'totalCost':18000}],'moves':[],'contacts':[],'materials':[],'supplies':[],'inventoryOpenings':[{'lotId':id,'asOf':'2026-11-01','rows':[{'location':'CDMX','tag':'Por clasificar','quantity':n,'sampleQuantity':0}],'inputRows':[],'complete':True} for id,n in [('ESP',120),('CUP',60)]]}
code=r'''const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');const {createApp}=require('./server.cjs');const salt='32'.repeat(16),hash=crypto.scryptSync('synthetic-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');const users=['esalazars','rsalazarm','msaenzc'].map(username=>({username,name:username,role:'editor',salt,hash}));users.push({username:'socioEB2',name:'Reader',role:'reader',salt,hash});createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'linked-db-')),root:process.env.TEST_PUBLIC,users,origins:['http://127.0.0.1:8891'],secure:false}).server.listen(8891,'127.0.0.1');'''
proc=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'TEST_PUBLIC':str(PUB)},stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
for _ in range(60):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
def ready(p):p.wait_for_function("()=>window.EBShared&&!EBShared.pending&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=15000)
def cloud(ctx):return ctx.request.get(BASE+'api/state').json()['data']
try:
 with sync_playwright() as pw:
  engine=os.environ.get('EB_BROWSER','chromium');browser=getattr(pw,engine).launch(**({'executable_path':shutil.which('chromium') or shutil.which('google-chrome'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  ctx=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
  auth=ctx.request.post(BASE+'api/login',data={'username':'esalazars','password':'synthetic-only'},headers={'Origin':BASE[:-1]}).json();csrf=auth['csrf']
  r=ctx.request.put(BASE+'api/state',data={'revision':0,'initialize':True,'operation':str(uuid.uuid4()),'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':csrf});assert r.ok,r.text()
  p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(BASE+'orders.html?partner=ricardo');ready(p)
  p.locator('#order-new').click();p.locator('#order-customer').fill('Synthetic recipient');p.locator('[data-amount]').fill('2');p.locator('#order-status').select_option('delivered');p.locator('#order-save').click();expect(p.locator('#order-dialog')).to_have_count(0,timeout=20000);ready(p)
  d=cloud(ctx);sale=d['lotSales'][0];sid=sale['id'];assert sale['quantity']==12 and sale['priceKnown'] is False and sale['stockEffect'] is False
  assert sum(-a['delta'] for a in d['lotStockAdjustments'] if a.get('status')!='cancelled')==12
  p.goto(BASE);ready(p);p.locator('[data-simple-open="ESP"]').click();expect(p.locator('#simple-current')).to_have_text('108');expect(p.locator('#simple-sold')).to_have_text('12');expect(p.locator('#simple-difference')).to_have_text('0')
  p.locator('.simple-history').evaluate('(e)=>e.open=true');expect(p.locator('[data-record-edit="'+sid+'"]').first).to_be_visible()
  filled=p.evaluate("()=>{let i=0;try{for(;i<1000;i++)localStorage.setItem('synthetic-fill-'+i,'x'.repeat(32000));}catch(e){return {keys:i,name:e.name};}throw Error('quota not reached')}");assert filled['name']=='QuotaExceededError'
  p.evaluate("()=>{let low=0,high=64000;while(low+1<high){const mid=Math.floor((low+high)/2);try{localStorage.setItem('synthetic-tail','x'.repeat(mid));low=mid;}catch(e){if(e.name!=='QuotaExceededError')throw e;high=mid;}}}");p.locator('[data-record-edit="'+sid+'"]').first.click();p.locator('#edit-price').fill('850');p.locator('#edit-payment-known').select_option('yes',force=True);p.locator('dialog[open] [data-save]').click();expect(p.locator('dialog[open]')).to_have_count(0,timeout=20000);ready(p)
  now=cloud(ctx);assert now['lotSales'][0]['totalCents']==1020000;assert now['lotStockAdjustments']==d['lotStockAdjustments'];expect(p.locator('#simple-current')).to_have_text('108')
  p.locator('.simple-history').evaluate('(e)=>e.open=true');failed={'on':True}
  def route(r):
   if r.request.method=='PUT' and failed['on']:r.fulfill(status=503,content_type='application/json',body='{"error":"Synthetic offline save"}')
   else:r.continue_()
  p.route('**/api/state',route)
  p.locator('[data-record-delete="'+sid+'"]').first.click();p.locator('dialog[open] [data-save]').click();expect(p.locator('dialog[open] [data-error]')).not_to_have_class('alert hidden',timeout=15000);expect(p.locator('dialog[open]')).to_be_visible();assert cloud(ctx)['partnerOrders'][0]['status']=='delivered'
  p.screenshot(path=str(OUT/(engine+'-delete-retained.png')),full_page=True)
  failed['on']=False;p.locator('dialog[open] [data-save]').click();expect(p.locator('dialog[open]')).to_have_count(0,timeout=20000);ready(p)
  expect(p.locator('#simple-current')).to_have_text('120');expect(p.locator('#simple-sold')).to_have_text('0');expect(p.locator('#simple-difference')).to_have_text('0')
  now=cloud(ctx);assert now['partnerOrders'][0]['status']=='cancelled';assert all(a.get('status')=='cancelled' for a in now['lotStockAdjustments']);assert sum(1 for h in now['editHistory'] if h.get('deleted'))==1
  hid=next(h['id'] for h in now['editHistory'] if h.get('deleted'));p.evaluate('window.EBEditUI.history()');p.locator('[data-undo="'+hid+'"]').click();expect(p.locator('dialog[open]')).to_have_count(0,timeout=20000);ready(p)
  p.locator('[data-simple-open="ESP"]').click();expect(p.locator('#simple-current')).to_have_text('108');expect(p.locator('#simple-sold')).to_have_text('12');now=cloud(ctx);assert now['partnerOrders'][0]['status']=='delivered';assert now['partnerOrderHistory'][-1]['action']=='undo-sale-correction';assert now['lotSales'][0]['totalCents']==1020000
  p.screenshot(path=str(OUT/(engine+'-linked-sale-restored.png')),full_page=True)
  second=browser.new_context();second.request.post(BASE+'api/login',data={'username':'rsalazarm','password':'synthetic-only'},headers={'Origin':BASE[:-1]});assert cloud(second)['lotSales']==now['lotSales']
  reader=browser.new_context();reader.request.post(BASE+'api/login',data={'username':'socioEB2','password':'synthetic-only'},headers={'Origin':BASE[:-1]});assert reader.request.get(BASE+'api/state').status==403;assert reader.request.get(BASE+'api/partner-report').status==200
  assert not errors,errors
  print('PASS '+engine+': delivered order -> linked sale, single debit, price-only edit, storage quota, failed-delete retention, retry once, shared undo, partner audit history and EB2 denial')
  second.close();reader.close();ctx.close();browser.close()
finally:
 proc.terminate();proc.wait(timeout=8)
