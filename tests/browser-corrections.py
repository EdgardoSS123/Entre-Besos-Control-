"""Isolated contexts only. No account or real user data access."""
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from workspace_test import Workspace
workspace=Workspace()
URL=workspace.base
OUT=Path(os.environ.get('EB_SCREENSHOTS','/mnt/data/eb-editable-screens'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844)]:
  ctx=workspace.context(browser,viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  workspace.goto(page,URL,wait_until='networkidle');page.locator('#list-new').click();page.locator('#lot-id').fill('EDIT-TEST');page.locator('#producedLiters').fill('1440');page.locator('#liquid').fill('200');page.locator('#save-lot').click();page.locator('[data-simple-open="EDIT-TEST"]').click()
  page.locator('#simple-location').select_option('USA');page.locator('#simple-amount').fill('3');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-save').click()
  page.locator('#simple-sale-tab').click();page.locator('#simple-amount').fill('0.5');page.locator('#simple-unit').select_option('pallet');page.locator('#simple-price').fill('600');page.locator('#simple-save').click()
  page.locator('#simple-move-tab').click();page.locator('#simple-destination').select_option('CDMX');page.locator('#simple-amount').fill('10');page.locator('#simple-unit').select_option('box');page.locator('#simple-save').click()
  assert page.locator('#simple-current').inner_text()=='1,200'
  page.locator('#simple-costs').click();expect(page.locator('#lot-id')).to_be_editable()
  page.locator('#lot-id').fill('RENAMED');page.locator('[data-product="2"]').click();page.locator('#producedLiters').fill('500');page.locator('#amount-0').fill('20');page.locator('#lot-date').fill('2024-11-03')
  page.screenshot(path=str(OUT/f'edit-lot-{width}.png'),full_page=True)
  page.locator('#save-lot').click();expect(page.locator('#app .heading h1')).to_have_text('RENAMED');assert page.locator('#simple-current').inner_text()=='1,200';assert page.locator('#simple-difference').inner_text()=='726'
  data=page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")
  assert data['lots'][0]['p']==2 and data['lots'][0]['bottles']==714
  assert all(x['lotId']=='RENAMED' for x in data['lotSales']+data['lotShipments']+data['lotStockAdjustments'])
  page.locator('.simple-history').evaluate('(e)=>e.open=true')
  page.locator('[data-record-edit][data-kind="sale"]').click();page.locator('#edit-amount').fill('0.25');page.locator('#edit-unit').select_option('pallet');page.locator('#edit-price').fill('650');page.locator('#edit-customer').fill('Cliente corregido');page.locator('dialog [data-save]').click()
  assert page.locator('#simple-current').inner_text()=='1,320'
  page.locator('.simple-history').evaluate('(e)=>e.open=true');page.locator('[data-simple-payment]').click();page.locator('#simple-pay-amount').fill('1000');page.locator('dialog [data-save]').click()
  page.locator('.simple-history').evaluate('(e)=>e.open=true');page.locator('.record-payments > summary').click();page.locator('[data-record-edit][data-kind="payment"]').click();page.locator('#edit-payment').fill('500');page.locator('dialog [data-save]').click()
  data=page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))");assert data['lotSales'][0]['payments'][0]['amountCents']==50000
  page.locator('.simple-history').evaluate('(e)=>e.open=true');page.locator('[data-record-edit][data-kind="move"]').click();page.locator('#edit-to').select_option('EB1-1 · Edgardo');page.locator('#edit-amount').fill('5');page.locator('dialog [data-save]').click()
  assert page.locator('#simple-current').inner_text()=='1,320'
  page.locator('.simple-history').evaluate('(e)=>e.open=true');page.screenshot(path=str(OUT/f'edit-records-{width}.png'),full_page=True)
  # Cancel never changes persisted state.
  snapshot=page.evaluate("localStorage.getItem('eb-v1')")
  page.locator('[data-record-delete][data-kind="sale"]').click();page.locator('dialog [data-cancel]').click();assert page.evaluate("localStorage.getItem('eb-v1')")==snapshot
  page.locator('[data-record-delete][data-kind="sale"]').click();page.locator('dialog [data-save]').click();assert page.locator('#simple-current').inner_text()=='1,440'
  # Delete only one bucket, not the whole lot, and recover it.
  page.locator('[data-stock-delete]').first.click();page.locator('dialog [data-save]').click();assert page.locator('#simple-current').inner_text()=='30'
  page.locator('#simple-back').click();page.locator('#correction-history').click();page.locator('dialog [data-undo]').first.click();page.locator('[data-simple-open="RENAMED"]').click();assert page.locator('#simple-current').inner_text()=='1,440'
  # Delete all lot records requires typing and is reversible.
  page.locator('#simple-delete-lot').click();page.locator('dialog [data-save]').click();assert page.locator('dialog [data-error]').is_visible();assert len(page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots"))==1
  page.locator('#delete-lot-confirm').fill('RENAMED');page.locator('dialog [data-save]').click();assert len(page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots"))==0
  page.locator('#correction-history').click();page.locator('dialog [data-undo]').first.click();page.locator('[data-simple-open="RENAMED"]').click();assert page.locator('#simple-current').inner_text()=='1,440'
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Horizontal overflow'
  snapshot=page.evaluate("localStorage.getItem('eb-v1')");workspace.reload(page,wait_until='networkidle');assert page.evaluate("localStorage.getItem('eb-v1')")==snapshot
  assert not errors,errors
  print('PASS EDITABLE',width,': editable code/product/production/date/cost with existing stock, linked rename, price/quantity/customer/payment/move editing, cancel, deletion reversal, bucket removal, lot confirmation/recovery and reload.')
  ctx.close()
 browser.close()
