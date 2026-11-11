"""Actual localStorage exhaustion; disposable HTTP, SQLite and accounts only."""
from pathlib import Path
setup=Path(__file__).with_name('browser-orders-save.py').read_text().split('try:\n with sync_playwright() as pw:')[0]
exec(compile(setup,'orders-quota-setup','exec'))
if os.environ.get('EB_QUOTA_BASELINE'):
 for name in ['shared.js','orders-ui.js']:shutil.copy(Path(os.environ['EB_QUOTA_BASELINE'])/name,public/name)
def fill_storage(page):
 return page.evaluate('''()=>{let count=0;const chunk='x'.repeat(16384);for(let i=0;i<10000;i++){try{localStorage.setItem('__quota_fill_'+i,chunk);count++;}catch(e){if(e.name!=='QuotaExceededError')throw e;break;}}let low=0,high=32768;while(low+1<high){const mid=Math.floor((low+high)/2);try{localStorage.setItem('__quota_tail','x'.repeat(mid));low=mid;}catch(e){if(e.name!=='QuotaExceededError')throw e;high=mid;}}return count;}''')
def backups(page):return page.evaluate('''()=>Object.fromEntries(Object.keys(localStorage).filter(k=>k.startsWith('__quota_')||k.startsWith('eb-before-')).map(k=>[k,localStorage.getItem(k)]))''')
def journal_count(page):return page.evaluate('''async()=>new Promise((resolve,reject)=>{const r=indexedDB.open('entre-besos-save-journal',1);r.onsuccess=()=>{const db=r.result,t=db.transaction('saves','readonly'),q=t.objectStore('saves').get('pending');q.onsuccess=()=>{const v=q.result;db.close();resolve(v?1:0);};q.onerror=()=>reject(q.error);};r.onerror=()=>reject(r.error);})''')
try:
 with sync_playwright() as pw:
  engine=os.environ.get('EB_BROWSER','chromium');browser=getattr(pw,engine).launch(**({'executable_path':shutil.which('google-chrome') or shutil.which('chromium'),'args':['--no-sandbox']} if engine=='chromium' else {}))
  ctx=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True);token=login(ctx,'rsalazarm')
  r=ctx.request.put(BASE+'api/state',data={'revision':0,'initialize':True,'operation':str(uuid.uuid4()),'data':seed},headers={'Origin':BASE[:-1],'X-EB-CSRF':token});assert r.ok
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept());page.goto(BASE+'orders.html?partner=ricardo');ready(page)
  page.evaluate("localStorage.setItem('eb-before-test-quota','RESGUARDO ORIGINAL QUE NO SE BORRA')")
  assert fill_storage(page)>100;kept=backups(page);fill(page,'Varios · quota test','4')
  if os.environ.get('EB_QUOTA_BASELINE'):
   page.locator('#order-save').click();expect(page.locator('#order-error')).to_contain_text('quota',ignore_case=True);expect(page.locator('#order-dialog')).to_be_visible();assert not cloud(ctx)['data'].get('partnerOrders')
   page.screenshot(path=str(OUT/(engine+'-quota-reproduced.png')),full_page=True)
   print('REPRODUCED: full localStorage rejects valid four-box order before shared save.',flush=True)
  else:
   page.locator('#order-save').click();close(page);now=cloud(ctx)['data'];assert len(now['partnerOrders'])==1 and now['partnerOrders'][0]['quantity']==24 and qty(page)==120
   assert backups(page)==kept;assert journal_count(page)==0;expect(page.locator('.order-record')).to_contain_text('Varios');page.screenshot(path=str(OUT/(engine+'-quota-saved.png')),full_page=True)
   page.reload();ready(page);expect(page.locator('.order-record')).to_have_count(1);assert backups(page)==kept
   print('PASS full localStorage, cloud confirmation, modal return, four boxes, reload; all original keys retained.',flush=True)
   control(ctx,delay=1200);fill(page,'Quota delivered','2');page.locator('#order-status').select_option('delivered');page.locator('#order-save').click();page.wait_for_timeout(150);expect(page.locator('#order-save')).to_be_disabled();close(page);assert qty(page)==108
   control(ctx,fail=True);fill(page,'Quota durable retry','1');page.locator('#order-status').select_option('delivered');page.locator('#order-save').click();expect(page.locator('#order-error')).to_contain_text('este dispositivo',timeout=15000);assert journal_count(page)==1
   pending=current(page)['partnerOrders'][-1];expect(page.locator('#order-customer')).to_have_value('Quota durable retry');assert len(cloud(ctx)['data']['partnerOrders'])==2
   page.screenshot(path=str(OUT/(engine+'-quota-offline-retained.png')),full_page=True)
   control(ctx);page.reload();ready(page);now=cloud(ctx)['data'];assert len(now['partnerOrders'])==3;assert now['partnerOrders'][-1]['id']==pending['id'];assert now['partnerOrders'][-1]['version']==pending['version'];assert qty(page)==102;assert journal_count(page)==0;assert backups(page)==kept
   print('PASS durable quota journal after failed response and reload; exact ID retry, no duplicate stock deductions.',flush=True)
   for user,partner in [('esalazars','edgardo'),('msaenzc','mario')]:
    device=browser.new_context(viewport={'width':390,'height':844});login(device,user);other=device.new_page();other.on('pageerror',lambda e:errors.append(str(e)));other.goto(BASE+'orders.html?partner='+partner);ready(other);assert len(current(other)['partnerOrders'])==len(cloud(ctx)['data']['partnerOrders']);fill_storage(other);fill(other,'Quota '+partner,'1');other.locator('#order-save').click();close(other);assert cloud(device)['data']['partnerOrders'][-1]['partner']==partner;device.close()
   login(ctx,'socioEB2');page.reload();expect(page.locator('#partner-report-app')).to_be_visible();expect(page.locator('#order-new')).to_have_count(0);assert ctx.request.get(BASE+'api/state').status==403
   admin=browser.new_context();login(admin);final=cloud(admin)['data'];assert len(final['partnerOrders'])==5
   for k in ['lots','moves','materials','supplies','expenses','documents']:assert final[k]==seed[k],k
   admin.close();assert not errors,errors
   print('PASS three EB1 editors, report-only EB2, shared visibility and unrelated records unchanged: '+engine,flush=True)
  ctx.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
