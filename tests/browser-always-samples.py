"""Authenticated disposable workspace, never real business records."""
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
  snapshot=page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))');assert len(snapshot['lotSampleActions'])==6 and len(snapshot['lotSales'])==1
  assert snapshot['lotSales'][0]['totalCents']==360000
  assert [a['type'] for a in snapshot['lotSampleActions']]==['reserve','consume','release','reserve','release','reserve']
  assert [a['quantity'] for a in snapshot['lotSampleActions']]==[12,2,6,6,6,702]
  assert all(a['income']==0 and a['receivable']==0 for a in snapshot['lotSampleActions'])
  page.screenshot(path=str(OUT/f'sample-balance-{width}.png'),full_page=True);workspace.reload(page);page.locator('[data-simple-open="SAMPLE-UI"]').click();expect(page.locator('#simple-current')).to_have_text('706');assert '1 pallet + 37 cajas + 4 botellas sueltas' in page.locator('#simple-current').locator('..').text_content();assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))')==snapshot
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors,errors
  ctx.close();print('PASS SAMPLES UI',width,'714-2-6=706, reserve/release do not change totals, transfer conserves stock, one real sale only, exact persistence')
 browser.close()
