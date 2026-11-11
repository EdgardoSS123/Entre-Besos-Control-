"""Orders save regression on disposable SQLite and local HTTP only."""
import copy, json, os, shutil, subprocess, tempfile, time, urllib.request, uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path.cwd();BASE='http://127.0.0.1:8867/'
OUT=Path(os.environ.get('EB_ORDERS_SAVE_REVIEW','/tmp/eb-orders-save-review'));OUT.mkdir(parents=True,exist_ok=True)
public=Path(tempfile.mkdtemp(prefix='eb-orders-save-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.html','.js','.css','.jpg','.png','.webmanifest']:shutil.copy(f,public/f.name)
for name in ['vendor','icons']:shutil.copytree(ROOT/name,public/name)
shutil.copy(ROOT/'control.html',public/'index.html')
code=r'''
const http=require('node:http'),crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createApp}=require('./server.cjs');
const salt='61'.repeat(16),hash=crypto.scryptSync('orders-disposable-only',Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');
const users=['esalazars','rsalazarm','msaenzc'].map(username=>({username,name:username,role:'editor',salt,hash}));users.push({username:'socioEB2',name:'Test EB2',role:'reader',salt,hash});
const app=createApp({folder:fs.mkdtempSync(path.join(os.tmpdir(),'eb-orders-save-db-')),root:process.env.EB_TEST_PUBLIC,users,origins:['http://127.0.0.1:8867'],secure:false});
let mode={delay:0,fail:false,drop:false,readFail:false},stats={puts:0};
app.server.listen(0,'127.0.0.1',()=>http.createServer(async(req,res)=>{
 if(req.url==='/__stats'){res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify(stats));return;}
 const chunks=[];for await(const b of req)chunks.push(b);const bytes=Buffer.concat(chunks);
 if(req.url==='/__control'){mode={delay:0,fail:false,drop:false,readFail:false,...JSON.parse(bytes)};stats={puts:0};res.writeHead(200,{'content-type':'application/json'});res.end('{}');return;}
 const put=req.method==='PUT'&&req.url==='/api/state';if(put)stats.puts++;
 if(put&&mode.fail){res.writeHead(503,{'content-type':'application/json'});res.end(JSON.stringify({error:'Synthetic offline upload'}));return;}
 if(mode.readFail&&req.method==='GET'&&req.url==='/api/state'){res.writeHead(503,{'content-type':'application/json'});res.end(JSON.stringify({error:'Synthetic confirmation failure'}));return;}
 const delay=put?mode.delay:0,drop=put&&mode.drop;if(drop)mode.drop=false;
 setTimeout(()=>{const up=http.request({host:'127.0.0.1',port:app.server.address().port,path:req.url,method:req.method,headers:req.headers},reply=>{
  if(drop){reply.resume();reply.on('end',()=>{res.writeHead(503,{'content-type':'application/json'});res.end(JSON.stringify({error:'Synthetic lost acknowledgement'}));});return;}
  if(res.destroyed){reply.resume();return;}res.writeHead(reply.statusCode,reply.headers);reply.pipe(res);
 });up.on('error',()=>{if(!res.destroyed){res.writeHead(502);res.end();}});up.end(bytes);},delay);
}).listen(8867,'127.0.0.1'));
'''
server=subprocess.Popen(['node','--experimental-sqlite','-e',code],env={**os.environ,'EB_TEST_PUBLIC':str(public)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for _ in range(80):
 try:urllib.request.urlopen(BASE+'healthz',timeout=1);break
 except Exception:time.sleep(.1)
subprocess.run(['node','tests/orders.cjs'],env={**os.environ,'EB_ORDERS_FIXTURE':str(OUT/'fixture.json')},check=True,stdout=subprocess.DEVNULL)
seed=json.loads((OUT/'fixture.json').read_text())
def login(ctx,user='esalazars'):
 r=ctx.request.post(BASE+'api/login',data={'username':user,'password':'orders-disposable-only'},headers={'Origin':BASE[:-1]});assert r.ok,r.text();return r.json()['csrf']
def cloud(ctx):
 r=ctx.request.get(BASE+'api/state');assert r.ok,r.text();return r.json()
def control(ctx,**kwargs):assert ctx.request.post(BASE+'__control',data=kwargs).ok
def ready(p):p.wait_for_function("()=>window.EBShared&&!EBShared.pending&&!window.EBOrdersUI?.saving&&document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado')",timeout=15000)
def fill(p,name='Synthetic recipient',quantity='2'):
 p.locator('#order-new').click();p.locator('#order-customer').fill(name);p.locator('[data-amount]').fill(quantity)
def close(p):expect(p.locator('#order-dialog')).to_have_count(0,timeout=20000);ready(p)
def current(p):return p.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')
def qty(p):return p.evaluate('EBLedger.balance(JSON.parse(localStorage.getItem("eb-v1")),"ORD-ESP").total')
def mutate(ctx,token,fn):
 row=cloud(ctx);fn(row['data']);r=ctx.request.put(BASE+'api/state',data={'revision':row['revision'],'operation':str(uuid.uuid4()),'data':row['data']},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert r.ok,r.text()
try:
 with sync_playwright() as pw:
  engine=os.environ.get('EB_BROWSER','chromium')
  browser=getattr(pw,engine).launch(**({'executable_path':shutil.which('google-chrome') or shutil.which('chromium'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  ctx=browser.new_context(viewport={'width':390 if engine=='webkit' else 1440,'height':900},is_mobile=engine=='webkit',has_touch=engine=='webkit')
  token=login(ctx);r=ctx.request.put(BASE+'api/state',data={'revision':0,'initialize':True,'operation':str(uuid.uuid4()),'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert r.ok,r.text()
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept());page.goto(BASE+'orders.html?partner=edgardo');ready(page)
  if os.environ.get('EB_EXPECT_BUG')=='1':
   fill(page);control(ctx,delay=2000)
   page.evaluate('()=>{const d=JSON.parse(localStorage.getItem("eb-v1"));d.contacts.push({name:"Other pending save"});localStorage.setItem("eb-v1",JSON.stringify(d));}')
   page.locator('#order-save').click();expect(page.locator('#order-error')).to_contain_text('Termina de sincronizar');assert not current(page).get('partnerOrders');ready(page)
   print('REPRODUCED: existing unrelated upload blocks a valid new order instead of waiting.',flush=True)
   page.locator('#order-save').click();page.wait_for_timeout(200);expect(page.locator('#order-dialog')).to_have_count(0);assert not cloud(ctx)['data'].get('partnerOrders')
   print('REPRODUCED: modal closes and says saved before any order reaches SQLite.',flush=True);ready(page)
  else:
   # Useful error remains visible at the save button; correction preserves values.
   page.locator('#order-new').click();page.locator('[data-amount]').fill('2');page.locator('#order-save').click();expect(page.locator('#order-error')).to_contain_text('para quién');expect(page.locator('#order-dialog')).to_be_visible()
   page.locator('#order-customer').fill('Synthetic: pending-upload order');control(ctx,delay=1500)
   page.evaluate('()=>{const d=JSON.parse(localStorage.getItem("eb-v1"));d.contacts.push({name:"Other pending save"});localStorage.setItem("eb-v1",JSON.stringify(d));}')
   page.locator('#order-save').click();page.wait_for_timeout(200);expect(page.locator('#order-dialog')).to_be_visible();expect(page.locator('#order-save')).to_be_disabled()
   close(page);assert len(cloud(ctx)['data']['partnerOrders'])==1;assert qty(page)==120
   print('PASS waits for previous upload, saves exactly one order, closes only after cloud confirmation.',flush=True)
   # Already-running/slow save does not discard in-form edits or allow duplicate taps.
   control(ctx,delay=1800);fill(page,'Synthetic: slow order','3');page.locator('#order-save').click();page.wait_for_timeout(250);expect(page.locator('#order-dialog')).to_be_visible();expect(page.locator('#order-customer')).to_be_disabled();assert len(cloud(ctx)['data']['partnerOrders'])==1
   page.screenshot(path=str(OUT/(engine+'-confirming-save.png')),full_page=True);close(page);assert len(cloud(ctx)['data']['partnerOrders'])==2
   # Lost commit acknowledgement is confirmed by receipt; no second order.
   control(ctx,drop=True);fill(page,'Synthetic: lost response','1');page.locator('#order-save').click();close(page);assert len(cloud(ctx)['data']['partnerOrders'])==3
   # Failed upload retains modal. Retry the same ID/version, never a new debit.
   control(ctx,fail=True);fill(page,'Synthetic: offline retry','2');page.locator('#order-status').select_option('delivered');page.locator('#order-save').click()
   expect(page.locator('#order-error')).to_contain_text('este dispositivo',timeout=10000);expect(page.locator('#order-dialog')).to_be_visible();expect(page.locator('#order-customer')).to_have_value('Synthetic: offline retry');assert len(cloud(ctx)['data']['partnerOrders'])==3
   pending=current(page)['partnerOrders'][-1];assert pending['quantity']==12;assert qty(page)==108
   page.screenshot(path=str(OUT/(engine+'-retained-on-failure.png')),full_page=True);control(ctx);page.locator('#order-save').click();close(page)
   now=cloud(ctx)['data'];assert len(now['partnerOrders'])==4;assert now['partnerOrders'][-1]['id']==pending['id'];assert now['partnerOrders'][-1]['version']==pending['version'];assert qty(page)==108
   print('PASS slow/lost/failed uploads, same-ID retry, no duplicate inventory exits.',flush=True)
   # Existing filters and recipient-only edits are preserved without rededucting.
   page.locator('[data-order-filter="delivered"]').click();before=cloud(ctx)['data']['lotStockAdjustments'];page.locator('[data-edit-order]').click();page.locator('#order-customer').fill('Synthetic: corrected recipient');page.locator('#order-save').click();close(page)
   expect(page.locator('[data-order-filter="delivered"]')).to_have_class('selected');assert cloud(ctx)['data']['lotStockAdjustments']==before
   page.locator('[data-pending]').click();ready(page);expect(page.locator('.order-record')).to_have_count(0,timeout=10000);assert qty(page)==120
   page.locator('[data-order-filter="all"]').click()
   # A second EB1 creates unrelated data while the first form is open.
   other=browser.new_context();other_token=login(other,'rsalazarm');fill(page,'Synthetic: shared change preserved','1')
   mutate(other,other_token,lambda d:d['contacts'].append({'name':'Second partner contact'}))
   page.locator('#order-save').click();close(page);assert cloud(ctx)['data']['contacts'][-1]['name']=='Second partner contact';assert len(cloud(ctx)['data']['partnerOrders'])==5
   # Editing the same order from another device must not be overwritten.
   order_id=cloud(ctx)['data']['partnerOrders'][0]['id'];page.locator('[data-edit-order="'+order_id+'"]').click();page.locator('#order-customer').fill('Synthetic: should not overwrite')
   def change_order(d):
    row=next(x for x in d['partnerOrders'] if x['id']==order_id);row['customer']='Remote partner edit';row['version']+=1
   mutate(other,other_token,change_order);page.locator('#order-save').click();expect(page.locator('#order-error')).to_contain_text('otro dispositivo');expect(page.locator('#order-dialog')).to_be_visible();expect(page.locator('#order-customer')).to_have_value('Synthetic: should not overwrite');page.locator('#order-discard').click()
   assert cloud(ctx)['data']['partnerOrders'][0]['customer']=='Remote partner edit'
   print('PASS fresh cloud snapshot preserves other partner changes; same-order conflict retains form without overwriting.',flush=True)
   # All three EB1 accounts can capture and another device observes their saves.
   for user,partner in [('rsalazarm','ricardo'),('msaenzc','mario')]:
    device=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True);login(device,user);mobile=device.new_page();mobile.on('dialog',lambda d:d.accept());mobile.on('pageerror',lambda e:errors.append(str(e)));mobile.goto(BASE+'orders.html?partner='+partner);ready(mobile);fill(mobile,'Synthetic: '+partner,'1');mobile.locator('#order-save').click();close(mobile);assert cloud(device)['data']['partnerOrders'][-1]['partner']==partner
    assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth');mobile.screenshot(path=str(OUT/(engine+'-'+partner+'-saved-mobile.png')),full_page=True);device.close()
   reader=browser.new_context();reader_token=login(reader,'socioEB2');rp=reader.new_page();rp.goto(BASE+'orders.html');expect(rp.locator('#partner-report-app')).to_be_visible();expect(rp.locator('#order-save,#order-new')).to_have_count(0);assert reader.request.get(BASE+'api/state').status==403
   assert reader.request.put(BASE+'api/state',data={'revision':99,'data':seed,'operation':str(uuid.uuid4())},headers={'Origin':BASE[:-1],'X-EB-CSRF':reader_token}).status==403
   final=cloud(ctx)['data'];assert len(final['partnerOrders'])==7
   for k in ['lots','moves','materials','supplies','expenses','documents']:assert final[k]==seed[k],k
   assert not errors,errors;print('PASS all three EB1 accounts; EB2 report-only; lots/costs/supplies/documents untouched; '+engine,flush=True)
   other.close();reader.close()
  ctx.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
