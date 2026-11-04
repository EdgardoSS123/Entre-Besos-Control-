"""Synthetic isolated storage only, including when testing deployed static application."""
import os,shutil,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path(os.environ.get('EB_SCREENSHOTS','/mnt/data/eb-stock-checks'));OUT.mkdir(parents=True,exist_ok=True)
def pair(where):return json.dumps([where,'Por clasificar'],ensure_ascii=False,separators=(',',':'))
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844),(375,812)]:
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE,wait_until='networkidle');expect(page.locator('h1')).to_have_text('Mis lotes')
  assert page.locator('#nav-editor,#mobile-editor,#lot-id').count()==0
  page.locator('#list-new').click();page.locator('#lot-id').fill('SAMPLE-UI');page.locator('[data-product="2"]').click();page.locator('#producedLiters').fill('500');page.locator('#liquid').fill('200');page.locator('#origin-warehouse').select_option('CDMX')
  expect(page.locator('#origin-samples')).to_be_visible();page.locator('#open-lot-stock').click();expect(page.locator('#simple-current')).to_have_text('714')
  expect(page.locator('#simple-all-samples')).to_be_visible()
  # Ship unreserved product as samples to Singapore directly, without sales screens.
  page.locator('#simple-move-tab').click();expect(page.locator('#simple-move-samples')).to_be_visible()
  assert not page.locator('#simple-move-samples').evaluate('(el)=>!!el.closest("details:not([open])")')
  page.locator('#simple-source').select_option(pair('CDMX'));page.locator('#simple-destination').select_option('Singapur');page.locator('#simple-amount').fill('2');page.locator('#simple-move-samples').check()
  assert 'Ingreso $0' in page.locator('#simple-preview').inner_text()
  page.screenshot(path=str(OUT/f'sample-transfer-{width}.png'),full_page=True)
  page.locator('#simple-save').click();expect(page.locator('#simple-current')).to_have_text('714');expect(page.locator('#simple-samples-used')).to_have_text('0');expect(page.locator('#simple-sold')).to_have_text('0')
  stock=page.evaluate('EBLedger.balance(JSON.parse(localStorage.getItem("eb-v1")),"SAMPLE-UI")')
  assert stock['sampleTotal']==12 and stock['commercialTotal']==702
  assert [r for r in stock['rows'] if r['location']=='Singapur'][0]['sampleQuantity']==12
  assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1")).lotShipments[0].sampleAccounting.income')==0
  assert page.evaluate('(JSON.parse(localStorage.getItem("eb-v1")).lotSales||[]).length')==0
  # Singapore samples appear as available origins; marker is preselected on full sample stock.
  page.locator('#simple-source').select_option(pair('Singapur'));expect(page.locator('#simple-move-samples')).to_be_checked()
  page.locator('#simple-destination').select_option('USA');page.locator('#simple-amount').fill('1');page.locator('#simple-save').click();expect(page.locator('#simple-current')).to_have_text('714')
  assert page.evaluate('EBLedger.available(JSON.parse(localStorage.getItem("eb-v1")),"SAMPLE-UI","USA","Por clasificar","sample")')==6
  # Reserved stock can be sold; free deliveries use the sample tab.
  page.locator('#simple-sale-tab').click();assert page.locator('#simple-sale-sample').count()==0
  page.locator('#simple-source').select_option(pair('USA'));page.locator('#simple-amount').fill('1')
  page.locator('#simple-price').fill('600');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('708');expect(page.locator('#simple-samples-used')).to_have_text('0');expect(page.locator('#simple-sold')).to_have_text('6')
  # Dedicated sample tab remains one-step, with quantity and optional recipient.
  page.locator('#simple-sample-tab').click();page.locator('#simple-source').select_option(pair('Singapur'));page.locator('#simple-amount').fill('2');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('706');expect(page.locator('#simple-samples-used')).to_have_text('2');expect(page.locator('#simple-difference')).to_have_text('0')
  # Counts can classify existing quantities; they don't count as consumed/given.
  page.locator('#simple-count-tab').click();page.locator('#simple-location').select_option('CDMX');page.locator('#simple-all-samples').check();page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('706');expect(page.locator('#simple-samples-used')).to_have_text('2')
  assert page.evaluate('EBLedger.balance(JSON.parse(localStorage.getItem("eb-v1")),"SAMPLE-UI").commercialTotal')==0
  page.screenshot(path=str(OUT/f'sample-balance-{width}.png'),full_page=True)
  before=page.evaluate('localStorage.getItem("eb-v1")');page.reload(wait_until='networkidle');expect(page.locator('h1')).to_have_text('Mis lotes');assert page.evaluate('localStorage.getItem("eb-v1")')==before
  page.locator('[data-simple-open="SAMPLE-UI"]').click();expect(page.locator('#simple-current')).to_have_text('706')
  assert '117 corrugados + 4 bot. sueltas' in page.locator('#simple-current').locator('..').inner_text()
  assert '2 bot. sueltas' in page.locator('#simple-samples-used').locator('..').inner_text()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
  assert not errors,errors
  print('PASS ALWAYS SAMPLES BROWSER',width,': visible in counts/moves/sales, Singapore dispatch without presplit, reserved forward transfer, free delivery without price, conserved production, cases/remainders, no false revenue, reload/no overflow.')
  ctx.close()
 browser.close()
