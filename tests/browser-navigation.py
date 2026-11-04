"""Default entry must be Mis lotes. All browser storage is synthetic and isolated."""
import json,os,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
URL=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-navigation'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844),(375,812)]:
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(URL,wait_until='networkidle')
  expect(page.locator('h1')).to_have_text('Mis lotes')
  assert page.locator('#nav-editor,#mobile-editor,#lot-id').count()==0
  assert 'Costear lote' not in page.locator('.side-nav').inner_text()
  assert page.locator('#resume-draft').count()==0
  # The cost form is entered explicitly by the only primary creation action.
  page.locator('#list-new').click();expect(page.locator('#lot-id')).to_be_visible()
  page.locator('#lot-id').fill('PENDING');page.locator('#producedLiters').fill('50');page.locator('#liquid').fill('200');page.locator('#origin-warehouse').select_option('Oaxaca')
  pending=page.evaluate('localStorage.getItem("eb-cost-draft-v3")')
  assert json.loads(pending)['id']=='PENDING'
  page.reload(wait_until='networkidle');expect(page.locator('h1')).to_have_text('Mis lotes');assert page.locator('#lot-id').count()==0
  assert page.evaluate('localStorage.getItem("eb-cost-draft-v3")')==pending
  expect(page.locator('#resume-draft')).to_be_visible()
  page.once('dialog',lambda d:d.dismiss());page.locator('#list-new').click()
  expect(page.locator('h1')).to_have_text('Mis lotes');assert page.evaluate('localStorage.getItem("eb-cost-draft-v3")')==pending
  page.locator('#resume-draft').click();expect(page.locator('#lot-id')).to_have_value('PENDING')
  expect(page.locator('#producedLiters')).to_have_value('50');expect(page.locator('#origin-warehouse')).to_have_value('Oaxaca')
  # Save returns to list; reopening never forces a cost editor.
  page.locator('#save-lot').click();expect(page.locator('h1')).to_have_text('Mis lotes');assert page.locator('#resume-draft').count()==0
  snapshot=page.evaluate('localStorage.getItem("eb-v1")')
  page.reload(wait_until='networkidle');expect(page.locator('h1')).to_have_text('Mis lotes');assert page.locator('#lot-id').count()==0
  assert page.evaluate('localStorage.getItem("eb-v1")')==snapshot
  page.screenshot(path=str(OUT/f'lots-home-{width}.png'),full_page=True)
  page.locator('[data-simple-open="PENDING"]').click();expect(page.locator('#simple-current')).to_have_text('69');assert page.locator('#lot-id').count()==0
  page.locator('#simple-costs').click();expect(page.locator('#lot-id')).to_have_value('PENDING')
  # Unsaved changes are also recovered from the list, without auto-opening them.
  page.locator('#amount-0').fill('15.50');page.locator('#show-lots').click();expect(page.locator('#resume-draft')).to_be_visible()
  page.locator('#resume-draft').click();expect(page.locator('#amount-0')).to_have_value('15.50')
  page.locator('#save-lot').click();expect(page.locator('h1')).to_have_text('Mis lotes');assert page.locator('#resume-draft').count()==0
  assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1")).lots.length')==1
  # Sidebar/bottom nav has only useful sections; new lot is always available in list.
  page.locator('#nav-warehouses' if width>950 else '#mobile-warehouses').click();expect(page.locator('h1')).to_have_text('Inventario por bodega')
  page.locator('#nav-lots' if width>950 else '#mobile-lots').click();expect(page.locator('h1')).to_have_text('Mis lotes')
  page.locator('#list-new').click();expect(page.locator('#lot-id')).to_have_value('');expect(page.locator('#producedLiters')).to_have_value('')
  assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1")).lots.length')==1
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  print('PASS NAVIGATION',width,': list first, no cost menu/form, explicit new/edit, same saved records, unsaved new/edit resume, cancelled discard, warehouses and no overflow')
  ctx.close()
 browser.close()
