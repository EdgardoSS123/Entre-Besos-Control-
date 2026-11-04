"""Synthetic lots in isolated storage; never accesses a user account."""
import os, shutil, json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
URL=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path(os.environ.get('EB_SCREENSHOTS','/mnt/data/eb-origin-screens'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844),(375,812)]:
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(URL,wait_until='networkidle');page.locator('#lot-id').fill('ORIGIN-TEST');page.locator('[data-product="2"]').click();page.locator('#producedLiters').fill('500');page.locator('#liquid').fill('200');page.locator('#lot-origin').select_option('Oaxaca')
  page.screenshot(path=str(OUT/f'origin-editor-{width}.png'),full_page=True)
  page.reload(wait_until='networkidle');expect(page.locator('#lot-origin')).to_have_value('Oaxaca')
  page.locator('#mobile-save-button' if width<700 else '#save-lot').click()
  expect(page.locator('#simple-current')).to_have_text('714');expect(page.locator('#simple-move-tab')).to_have_class('active');assert 'Oaxaca' in page.locator('#simple-source').input_value()
  page.locator('#simple-destination').select_option('CDMX');page.locator('#simple-amount').fill('10');page.locator('#simple-save').click()
  balance=lambda:page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'ORIGIN-TEST')")
  assert balance()['total']==714
  assert {r['location']:r['quantity'] for r in balance()['rows']}=={'Oaxaca':654,'CDMX':60}
  page.screenshot(path=str(OUT/f'origin-movement-{width}.png'),full_page=True)
  page.locator('#simple-sale-tab').click();page.locator('#simple-source').select_option(json.dumps(['CDMX','Por clasificar'],ensure_ascii=False,separators=(',',':')));page.locator('#simple-amount').fill('1');page.locator('#simple-price').fill('6000');page.locator('#simple-save').click();assert balance()['total']==708
  page.locator('#simple-costs').click();page.locator('#lot-id').fill('ORIGIN-RENAMED');page.locator('#lot-origin').select_option('USA');page.locator('#mobile-save-button' if width<700 else '#save-lot').click()
  assert page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'ORIGIN-RENAMED').total")==708
  assert page.evaluate("EBLedger.available(JSON.parse(localStorage.getItem('eb-v1')),'ORIGIN-RENAMED','USA','Por clasificar')")==0
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lotSales[0].lotId")=='ORIGIN-RENAMED'
  snapshot=page.evaluate("localStorage.getItem('eb-v1')");page.reload(wait_until='networkidle');assert page.evaluate("localStorage.getItem('eb-v1')")==snapshot
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Horizontal overflow'
  assert not errors, errors
  ctx.close()
  # Existing lot from before this feature, without stock: explicit origin only.
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700);page=ctx.new_page();page.goto(URL,wait_until='networkidle')
  old={'lots':[{'id':'LEGACY-ORIGIN','p':2,'ml':700,'bottles':714,'unitCost':218.13,'date':'2024-11-03'}],'moves':[],'contacts':[{'name':'Keep'}],'documents':[{'keep':True}]}
  page.evaluate('(d)=>localStorage.setItem("eb-v1",JSON.stringify(d))',old);page.reload(wait_until='networkidle');page.locator('#show-lots').click();page.locator('[data-simple-open="LEGACY-ORIGIN"]').click();expect(page.locator('#simple-current')).to_have_text('0')
  page.locator('#lot-origin-select').select_option('CDMX');page.locator('#save-lot-origin').click();expect(page.locator('#simple-current')).to_have_text('714');assert 'CDMX' in page.locator('#simple-source').input_value()
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).contacts")==old['contacts']
  page.locator('#simple-back').click();page.locator('#correction-history').click();page.locator('dialog [data-undo]').first.click();page.locator('[data-simple-open="LEGACY-ORIGIN"]').click();expect(page.locator('#simple-current')).to_have_text('0')
  ctx.close();print('PASS ORIGIN BROWSER',width,'draft, initial stock, direct movement, sale, rename, no duplicate, existing lot, undo, preserved data and mobile layout')
 browser.close()
