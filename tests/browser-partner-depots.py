"""Fresh isolated browser contexts; never read or modify the user's records."""
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-partner-screens'));OUT.mkdir(parents=True,exist_ok=True)
DEPOTS=['EB1-1 · Edgardo','EB1-2 · Ricardo','EB1-3 · Mario']
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844)]:
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'?classic=1&'+'?test=minibodegas1',wait_until='networkidle');page.locator('#lot-id').fill('CI-MINIBODEGAS')
  page.locator('#producedLiters').fill('432');page.locator('#liquid').fill('200');page.locator('#open-lot-stock').click()
  row=page.locator('.opening-row').nth(1);row.locator('[data-tag]').select_option('Nacional');row.locator('[data-amount]').fill('20');row.locator('[data-unit]').select_option('box')
  options=row.locator('[data-location] option').all_text_contents()
  assert all(name in options for name in DEPOTS)
  page.locator('#opening-complete').check();page.locator('#save-opening').click()
  bal=lambda:page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'CI-MINIBODEGAS')")
  for dest in DEPOTS:
   page.locator('#new-shipment').click();page.locator('#ship-from').select_option('CDMX');page.locator('#ship-to').select_option(dest)
   page.locator('#ship-tag').select_option('Nacional');page.locator('#ship-amount').fill('2');page.locator('#ship-status').select_option('received')
   assert page.locator('#ship-purpose').input_value()=='transfer'
   page.locator('#save-shipment').click()
   assert bal()['total']==120 and bal()['transit']==0
  assert page.evaluate("(JSON.parse(localStorage.getItem('eb-v1')).lotSales||[]).length")==0
  nav='#nav-warehouses' if width>700 else '#mobile-warehouses'
  page.locator(nav).click();assert page.locator('.partner-depot').count()==4
  page.locator('[data-partner-location="'+DEPOTS[0]+'"]').click()
  assert page.locator('#warehouse-filter').input_value()==DEPOTS[0]
  assert page.locator('.warehouse-lots strong').first.inner_text()=='12'
  page.locator('[data-depot-sale]').click();assert page.locator('#sale-from').input_value()==DEPOTS[0]
  assert page.locator('#sale-tag').input_value()=='Nacional'
  page.locator('#sale-customer').fill('Cliente de prueba');page.locator('#sale-amount').fill('1');page.locator('#sale-price').fill('6600');page.locator('#save-sale').click()
  assert bal()['total']==114
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lotSales[0].from")==DEPOTS[0]
  assert page.evaluate("EBLedger.saleStatus(JSON.parse(localStorage.getItem('eb-v1')).lotSales[0],'2026-11-04').pendingCents")==660000
  page.locator(nav).click();page.locator('[data-partner-location="'+DEPOTS[0]+'"]').click()
  assert page.locator('.warehouse-lots strong').first.inner_text()=='6'
  for dest in DEPOTS[1:]:
   page.locator('[data-partner-location="'+dest+'"]').click();assert page.locator('.warehouse-lots strong').first.inner_text()=='12'
  page.locator('[data-partner-location="CDMX"]').click();assert page.locator('.warehouse-lots strong').first.inner_text()=='84'
  page.locator('[data-partner-location="'+DEPOTS[0]+'"]').click()
  page.screenshot(path=str(OUT/f'minibodegas-{width}.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Horizontal overflow'
  snapshot=page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")
  page.reload();page.locator('#lot-id').wait_for();assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")==snapshot
  assert not errors,errors
  print('PASS BROWSER',width,'3 partner depots, opening options, internal transfers, no sales on transfer, selected home sale, independent balances, preservation, no overflow')
  ctx.close()
 browser.close()
