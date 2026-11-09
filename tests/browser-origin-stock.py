"""Isolated browser storage only. No accounts and no actual business records."""
import os,shutil,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from workspace_test import Workspace
workspace=Workspace()
BASE=workspace.base
OUT=Path(os.environ.get('EB_SCREENSHOTS','/mnt/data/eb-stock-checks'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844),(375,812)]:
  ctx=workspace.context(browser,viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  workspace.goto(page,BASE,wait_until='networkidle');expect(page.locator('#app h1')).to_have_text('Mis lotes');assert page.locator('#lot-id').count()==0;page.locator('#list-new').click();page.locator('#lot-id').wait_for()
  page.locator('#lot-id').fill('ORIGIN-TEST');page.locator('[data-product="2"]').click();page.locator('#producedLiters').fill('500');page.locator('#liquid').fill('200')
  page.locator('#origin-warehouse').select_option('CDMX')
  page.screenshot(path=str(OUT/f'origin-editor-{width}.png'),full_page=True)
  page.locator('#open-lot-stock').click();page.locator('#simple-current').wait_for()
  expect(page.locator('#simple-current')).to_have_text('714');expect(page.locator('#simple-produced')).to_have_text('714');assert '1 pallet + 39 cajas + 0 botellas sueltas' in page.locator('.simple-metrics').text_content()
  # Saving the same lot again never duplicates the origin balance.
  page.locator('#simple-costs').click();page.locator('#open-lot-stock').click();expect(page.locator('#simple-current')).to_have_text('714')
  page.locator('#simple-sale-tab').click();page.locator('#simple-amount').fill('25');page.locator('#simple-unit').select_option('bottle');page.locator('#simple-price').fill('1000');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('689');expect(page.locator('#simple-sold')).to_have_text('25');expect(page.locator('#simple-produced')).to_have_text('714');expect(page.locator('#simple-difference')).to_have_text('0')
  assert '1 pallet + 34 cajas + 5 botellas sueltas' in page.locator('#simple-current').locator('..').text_content();assert '0 pallets + 4 cajas + 1 botella suelta' in page.locator('#simple-sold').locator('..').text_content()
  page.screenshot(path=str(OUT/f'stock-after-sale-{width}.png'),full_page=True)
  # Single-step sample delivery from unreserved commercial stock.
  page.locator('#simple-sample-tab').click();page.locator('#simple-amount').fill('6');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('683');expect(page.locator('#simple-samples-used')).to_have_text('6');expect(page.locator('#simple-produced')).to_have_text('714');expect(page.locator('#simple-difference')).to_have_text('0')
  # A warehouse move changes only each location, not the general balance.
  page.locator('#simple-move-tab').click();page.locator('#simple-destination').select_option('EB1-1 · Edgardo');page.locator('#simple-amount').fill('10');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('683');assert '60' in page.locator('[data-place="EB1-1 · Edgardo"]').inner_text();assert '623' in page.locator('[data-place="CDMX"]').inner_text()
  page.locator('#simple-sample-tab').click();page.locator('#simple-source').select_option(json.dumps(['EB1-1 · Edgardo','Por clasificar'],ensure_ascii=False,separators=(',',':')));page.locator('#simple-sample-action').select_option('reserve');page.locator('#simple-amount').fill('60');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('683');expect(page.locator('#simple-samples-used')).to_have_text('6')
  page.locator('#simple-sample-tab').click();page.locator('#simple-source').select_option(json.dumps(['EB1-1 · Edgardo','Por clasificar'],ensure_ascii=False,separators=(',',':')));page.locator('#simple-amount').fill('2');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('681');expect(page.locator('#simple-samples-used')).to_have_text('8');expect(page.locator('#simple-produced')).to_have_text('714')
  # Backdated, already-excluded sale stays non-deducting; screenshot mistake can be explicitly repaired.
  page.locator('#simple-sale-tab').click();page.locator('#simple-form .simple-details > summary').click();page.locator('#simple-history').check();page.locator('#simple-amount').fill('5');page.locator('#simple-unit').select_option('bottle');page.locator('#simple-price').fill('1000');page.locator('#simple-save').click()
  expect(page.locator('#simple-current')).to_have_text('681');expect(page.locator('#simple-difference')).to_have_text('5')
  page.locator('#review-undiscounted').click();page.locator('[data-apply-sale]').click();page.locator('dialog [data-apply]').click()
  expect(page.locator('#simple-current')).to_have_text('676');expect(page.locator('#simple-sold')).to_have_text('30');expect(page.locator('#simple-difference')).to_have_text('0');assert page.locator('[data-apply-sale]').count()==0
  # Report, reload, exact values, no invisible overflow, and no mutation of foreign records.
  snapshot=page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')
  assert len(snapshot['lotSales'])==2 and len(snapshot['lotSampleActions'])==3
  assert all(x['income']==0 and x['receivable']==0 for x in snapshot['lotSampleActions'])
  with page.expect_download() as event:page.locator('#simple-print').click()
  pdf=OUT/f'report-{width}.pdf';event.value.save_as(pdf)
  import pymupdf
  text=' '.join(pg.get_text() for pg in pymupdf.open(pdf));assert all(term in text for term in ['676', 'ORIGIN-TEST', 'Muestras'])
  page.locator('#eb-pdf-ready button').filter(has_text='Volver a la app').click()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Horizontal overflow'
  workspace.reload(page,wait_until='networkidle');expect(page.locator('#app h1')).to_have_text('Mis lotes');assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==snapshot
  page.locator('[data-simple-open]').click();expect(page.locator('#simple-current')).to_have_text('676')
  assert not errors,errors
  print('PASS ORIGIN BROWSER',width,': origin seed once, fixed production, 714-25=689, exact corrugados, direct/reserved samples, warehouse transfer, repair once, report/reload/no overflow')
  ctx.close()
 browser.close()
