from pathlib import Path

def patch(path,old,new):
 p=Path(path);s=p.read_text()
 if new in s:return
 assert s.count(old)==1,(path,old[:60],s.count(old))
 p.write_text(s.replace(old,new,1))

# Shared-browser caches are not authority to export data. Revalidate EB1 session
# before all backup/import actions, including the public install landing page.
patch('pwa.js', '  function backup(){\n    try{const raw=', '''  async function requireEditor(){
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
    try{const r=await fetch('/api/session',{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(!r.ok)throw Error('Conéctate e inicia sesión con un socio EB1.');const s=await r.json();if(!s.authenticated||s.user?.role!=='editor')throw Error('Respaldo e importación requieren una sesión EB1. EB2 solo puede consultar el reporte.');}finally{clearTimeout(timer);}
  }
  async function backup(){
    try{await requireEditor();const raw=''')
patch('pwa.js', "try{if(file.size>10*1024*1024)", "try{await requireEditor();if(file.size>10*1024*1024)")
patch('pwa.js', '  function restore(){if(restoreBusy||!pending)return;restoreBusy=true;\n    try{if(capturePending())', '  async function restore(){if(restoreBusy||!pending)return;restoreBusy=true;\n    try{await requireEditor();if(capturePending())')
patch('shared.js', "function backup(raw=get(KEY),name='Entre-Besos-respaldo'){\n if(!raw)return;", "async function backup(raw=get(KEY),name='Entre-Besos-respaldo'){\n try{const s=await api('session');if(!s.authenticated||s.user?.role!=='editor')throw Error('Inicia sesión con un socio EB1 para obtener un respaldo.');}catch(e){fail('No se exportó información. '+e.message);return;}\n if(!raw)return;")

patch('tests/browser-audit.py', "  assert not errors,errors\n  print('PASS AUDIT UI:", '''  # Same browser moves from an editor to a reader without granting cache export.
  switched=editors[0][0];a.reload();ready(a);a.locator('#eb-cloud-account').click();a.locator('[data-out]').click();expect(a.locator('#eb-login')).to_be_visible()
  a.locator('#eb-user').fill('socioEB2');a.locator('#eb-password').fill('audit-synthetic-password');a.locator('#eb-enter').click();expect(a.locator('#partner-report-state')).to_contain_text('Actualizado',timeout=20000)
  assert switched.request.get(BASE+'api/state').status==403
  expect(a.locator('#order-new,#eb-cloud-account')).to_have_count(0)
  a.goto(BASE+'instalar.html');downloads=[];a.on('download',lambda d:downloads.append(d));before=a.evaluate('localStorage.getItem("eb-v1")');assert before is not None
  a.locator('#eb-app-backup').click();expect(a.locator('#eb-app-status')).to_contain_text('No se pudo generar el respaldo')
  assert not downloads and a.evaluate('localStorage.getItem("eb-v1")')==before
  a.locator('#eb-backup-file').set_input_files({'name':'reader-blocked.json','mimeType':'application/json','buffer':json.dumps(seed).encode()});expect(a.locator('#eb-app-status')).to_contain_text('requieren una sesión EB1');assert not downloads and a.evaluate('localStorage.getItem("eb-v1")')==before
  print('PASS SAME BROWSER: editor logout, EB2 login, report only, server denies full state, install-page backup/import denied despite old cache; no records altered')
  assert not errors,errors
  print('PASS AUDIT UI:''')
if Path('.git').exists():
 import subprocess
 subprocess.run(['git','add','pwa.js','shared.js'],check=True)
print('PASS guarded cached-data exports and same-browser EB2 regression installed')

# Queue report snapshots behind a save already holding the browser lock.
patch('shared.js', "async function flush(){if(navigator.locks)return navigator.locks.request('entre-besos-sync',{ifAvailable:true},lock=>lock?sendPending():undefined);return sendPending();}", "async function flush(wait=false){if(navigator.locks)return navigator.locks.request('entre-besos-sync',wait?{}:{ifAvailable:true},lock=>lock?sendPending():undefined);if(wait){const until=Date.now()+20000;while(sending&&Date.now()<until)await new Promise(r=>setTimeout(r,50));}return sendPending();}")
patch('shared.js', "if(!ready||!who)throw Error('Inicia sesión para generar el reporte.');\n await flush();", "if(!ready||!who)throw Error('Inicia sesión para generar el reporte.');\n await flush(true);")
patch('shared.js', "partnerReport:async()=>{if(who?.role==='editor'){await flush();", "partnerReport:async()=>{if(who?.role==='editor'){await flush(true);")

p=Path('tests/browser-history-filter.py');s=p.read_text().replace("page.locator('dialog')", "page.locator('dialog[open]')").replace("document.querySelector('dialog')", "document.querySelector('dialog[open]')").replace("dialog [data-error]:not(.hidden)","dialog[open] [data-error]:not(.hidden)");p.write_text(s)
patch('tests/browser-navigation.py', "page.locator('#resume-draft').click();expect(page.locator('#amount-0')).to_have_value('15.50')\n  page.locator('#save-lot').click();expect(page.locator('#app h1')).to_have_text('Mis lotes');", "page.locator('#resume-draft').click();expect(page.locator('#amount-0')).to_have_value('15.50')\n  page.locator('#save-lot').click();expect(page.locator('#app h1')).to_have_text('PENDING');page.locator('#simple-back').click();expect(page.locator('#app h1')).to_have_text('Mis lotes');")
patch('tests/browser-origin-stock.py', "page.locator('#simple-count-tab').click();page.locator('#simple-location').select_option('EB1-1 · Edgardo');page.locator('#simple-all-samples').check();page.locator('#simple-save').click()", "page.locator('#simple-sample-tab').click();page.locator('#simple-source').select_option(json.dumps(['EB1-1 · Edgardo','Por clasificar'],ensure_ascii=False,separators=(',',':')));page.locator('#simple-sample-action').select_option('reserve');page.locator('#simple-amount').fill('60');page.locator('#simple-save').click()")
patch('tests/browser-origin-stock.py', "len(snapshot['lotSampleActions'])==2", "len(snapshot['lotSampleActions'])==3")
# Fail with the actual PDF message rather than hiding it behind a download timeout.
patch('tests/browser-reports.py', "    with page.expect_download(timeout=60000) as event:page.evaluate('window.EBReports.download(window.EBReports.context())')", "    with page.expect_download(timeout=60000) as event:\n        result=page.evaluate('async()=>!!(await window.EBReports.download(window.EBReports.context()))')\n        assert result,page.locator('#eb-pdf-status').inner_text()")

# Exercise the present dedicated samples UI: reserve, consume, release,
# warehouse transfer, sale of reserved product, and classifying the remainder.
Path('tests/browser-always-samples.py').write_text('''"""Authenticated disposable workspace, never real business records."""
import os,shutil,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from workspace_test import Workspace
workspace=Workspace();BASE=workspace.base
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-samples'));OUT.mkdir(parents=True,exist_ok=True)
def pair(loc):return json.dumps([loc,'Por clasificar'],ensure_ascii=False,separators=(',',':'))
def samples(page,operation,location,quantity):
 page.locator('#simple-sample-tab').click();page.locator('#simple-sample-action').select_option(operation);page.locator('#simple-source').select_option(pair(location));page.locator('#simple-amount').fill(str(quantity));page.locator('#simple-save').click()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
 for width in [1440,390,375]:
  ctx=workspace.context(browser,viewport={'width':width,'height':900},is_mobile=width<700,has_touch=width<700);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  workspace.goto(page,BASE);page.locator('#list-new').click();page.locator('#lot-id').fill('SAMPLE-UI');page.locator('[data-product="2"]').click();page.locator('#producedLiters').fill('500');page.locator('#liquid').fill('200');page.locator('#origin-warehouse').select_option('CDMX');page.locator('#open-lot-stock').click()
  expect(page.locator('#simple-current')).to_have_text('714');expect(page.locator('#simple-sample-tab')).to_be_visible()
  samples(page,'reserve','CDMX',12)
  b=page.evaluate('EBLedger.balance(JSON.parse(localStorage.getItem("eb-v1")),"SAMPLE-UI")');assert b['sampleTotal']==12 and b['commercialTotal']==702 and b['total']==714
  samples(page,'consume','CDMX',2);expect(page.locator('#simple-current')).to_have_text('712');expect(page.locator('#simple-samples-used')).to_have_text('2')
  samples(page,'release','CDMX',6)
  b=page.evaluate('EBLedger.balance(JSON.parse(localStorage.getItem("eb-v1")),"SAMPLE-UI")');assert b['sampleTotal']==4 and b['commercialTotal']==708 and b['total']==712
  page.locator('#simple-move-tab').click();page.locator('#simple-source').select_option(pair('CDMX'));page.locator('#simple-destination').select_option('Singapur');page.locator('#simple-amount').fill('1');page.locator('#simple-unit').select_option('box');page.locator('#simple-save').click();expect(page.locator('#simple-current')).to_have_text('712')
  samples(page,'reserve','Singapur',6)
  assert page.evaluate('(JSON.parse(localStorage.getItem("eb-v1")).lotSales||[]).length')==0
  page.locator('#simple-sale-tab').click();page.locator('#simple-source').select_option(pair('Singapur'));page.locator('#simple-amount').fill('1');page.locator('#simple-price').fill('600');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('706');expect(page.locator('#simple-sold')).to_have_text('6');expect(page.locator('#simple-samples-used')).to_have_text('2');expect(page.locator('#simple-difference')).to_have_text('0')
  samples(page,'reserve','CDMX',702)
  b=page.evaluate('EBLedger.balance(JSON.parse(localStorage.getItem("eb-v1")),"SAMPLE-UI")');assert b['sampleTotal']==706 and b['commercialTotal']==0 and b['total']==706
  snapshot=page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))');assert len(snapshot['lotSampleActions'])==5 and len(snapshot['lotSales'])==1
  assert snapshot['lotSales'][0]['totalCents']==360000
  page.screenshot(path=str(OUT/f'sample-balance-{width}.png'),full_page=True);workspace.reload(page);page.locator('[data-simple-open="SAMPLE-UI"]').click();expect(page.locator('#simple-current')).to_have_text('706');assert '1 pallet + 37 cajas + 4 botellas sueltas' in page.locator('#simple-current').locator('..').inner_text();assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==snapshot
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors,errors
  ctx.close();print('PASS SAMPLES UI',width,'714-2-6=706, reserve/release do not change totals, transfer conserves stock, one real sale only, exact persistence')
 browser.close()
''')
if Path('.git').exists():
 import subprocess
 subprocess.run(['git','add','shared.js','pwa.js'],check=True)
print('PASS report-save queue and current sample/navigation/visible-dialog regressions installed')
