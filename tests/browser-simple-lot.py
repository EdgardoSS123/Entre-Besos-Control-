"""New default UI, isolated browser contexts, no user's stored records."""
import os,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path(os.environ.get('EB_SCREENSHOTS','/mnt/data/eb-simple-screens'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844),(375,812)]:
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE,wait_until='networkidle');expect(page.locator('h1')).to_have_text('Mis lotes');assert page.locator('#lot-id').count()==0;page.locator('#list-new').click();page.locator('#lot-id').wait_for()
  page.locator('#lot-id').fill('SIMPLE-CI');page.locator('#producedLiters').fill('1036.8');page.locator('#liquid').fill('200')
  page.locator('#open-lot-stock').click();page.locator('#simple-count-tab').wait_for()
  page.locator('#simple-location').select_option('USA');page.locator('#simple-amount').fill('3');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click()
  assert page.locator('#simple-current').inner_text()=='1,440'
  page.locator('#simple-sale-tab').click();page.locator('#simple-amount').fill('0.5');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-price').fill('6000');page.locator('#simple-save').click()
  assert page.locator('#simple-current').inner_text()=='1,200';assert page.locator('#simple-sold').inner_text()=='240';assert page.locator('#simple-difference').inner_text()=='0'
  assert '2.5 pallets' in page.locator('[data-place="USA"]').inner_text()
  page.locator('#simple-move-tab').click();page.locator('#simple-destination').select_option('CDMX');page.locator('#simple-amount').fill('0.5');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click()
  assert page.locator('#simple-current').inner_text()=='1,200';assert '960' in page.locator('[data-place="USA"]').inner_text();assert '240' in page.locator('[data-place="CDMX"]').inner_text()
  page.locator('#simple-count-tab').click();page.locator('#simple-location').select_option('USA');page.locator('#simple-amount').fill('1.5');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click()
  assert page.locator('#simple-current').inner_text()=='960';assert page.locator('#simple-difference').inner_text()=='240'
  page.locator('#simple-sale-tab').click();page.locator('#simple-form .simple-details > summary').click();page.locator('#simple-history').check();page.locator('#simple-amount').fill('0.5');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click()
  assert page.locator('#simple-current').inner_text()=='960';assert page.locator('#simple-difference').inner_text()=='0'
  page.locator('#simple-count-tab').click();page.locator('#simple-location').select_option('USA');page.locator('#simple-amount').fill('1,5');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click()
  assert page.locator('#simple-current').inner_text()=='960'
  snapshot=page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")
  assert len(snapshot['lotSales'])==2 and snapshot['lotSales'][1]['priceKnown'] is False
  page.screenshot(path=str(OUT/f'simple-lot-{width}.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Horizontal overflow'
  page.reload(wait_until='networkidle');expect(page.locator('h1')).to_have_text('Mis lotes');assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")==snapshot
  page.locator('[data-simple-open]').click();page.locator('#simple-current').wait_for();assert page.locator('#simple-current').inner_text()=='960'
  page.locator('#simple-move-tab').click();page.locator('#simple-amount').fill('10');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click();assert page.locator('#simple-error').is_visible()
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")==snapshot
  page.evaluate('window.print=()=>{}');page.locator('#simple-print').click();assert 'Por aclarar' in page.locator('#print-view').inner_text()
  assert not errors,errors
  print('PASS SIMPLE BROWSER',width,'default entry; decimals/comma; 3-0.5=2.5 pallets; immediate move; correction; past sale without origin/price/date; reconcile; reload; safe overflow; preserved invalid action; report.')
  ctx.close()
 browser.close()
