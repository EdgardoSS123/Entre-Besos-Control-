"""Isolated browser storage only; never uses a user's account or captured records."""
import os,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-commerce-screens'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844),(375,812)]:
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'?check=commerce1',wait_until='networkidle');page.locator('#lot-id').wait_for()
  page.locator('#lot-id').fill('CI-COMMERCE');page.locator('#producedLiters').fill('432');page.locator('#liquid').fill('200')
  page.locator('#open-lot-stock').click();page.locator('#opening-panel').wait_for()
  rows=page.locator('.opening-row')
  rows.nth(0).locator('[data-tag]').select_option('Nacional');rows.nth(0).locator('[data-amount]').fill('60');rows.nth(0).locator('[data-unit]').select_option('box')
  rows.nth(3).locator('[data-tag]').select_option('Exportación');rows.nth(3).locator('[data-amount]').fill('2');rows.nth(3).locator('[data-unit]').select_option('box');rows.nth(3).locator('[data-sample]').check()
  page.locator('#opening-complete').check();page.locator('#save-opening').click()
  bal=lambda:page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'CI-COMMERCE')")
  assert bal()['total']==372 and bal()['sampleTotal']==12
  page.locator('#open-commerce').click();page.locator('#sale-price').wait_for()
  page.locator('#sale-customer').fill('Cliente CI');page.locator('#sale-amount').fill('10');page.locator('#sale-price').fill('6600');page.locator('#sale-payment-state').select_option('partial');page.locator('#sale-paid').fill('16500')
  page.screenshot(path=str(OUT/f'commerce-sale-form-{width}.png'),full_page=True)
  page.locator('#save-sale').click()
  assert bal()['total']==312 and bal()['sampleTotal']==12
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lotSales[0].totalCents")==6600000
  assert 'pago parcial' in page.locator('.sale-record').first.inner_text().lower()
  assert page.evaluate("EBLedger.saleStatus(JSON.parse(localStorage.getItem('eb-v1')).lotSales[0],new Date().toISOString().slice(0,10)).status")=="Pago parcial"
  page.locator('[data-payment]').click();page.locator('#payment-amount').fill('49500');page.locator('dialog [data-save]').click()
  assert bal()['total']==312
  assert 'pagada' in page.locator('.sale-record').first.inner_text().lower()
  assert page.evaluate("EBLedger.saleStatus(JSON.parse(localStorage.getItem('eb-v1')).lotSales[0],new Date().toISOString().slice(0,10)).status")=="Pagada"
  page.locator('#tab-samples').click();page.locator('#sample-location').select_option('Oaxaca');page.locator('#sample-tag').select_option('Nacional');page.locator('#sample-amount').fill('6');page.locator('#save-sample').click()
  assert bal()['total']==312 and bal()['sampleTotal']==18
  page.locator('#sample-location').select_option('Singapur');page.locator('#sample-tag').select_option('Exportación');page.locator('#sample-action').select_option('consume');page.locator('#sample-amount').fill('1');page.locator('#sample-notes').fill('Muestra de degustación');page.locator('#save-sample').click()
  assert bal()['total']==311 and bal()['sampleTotal']==17
  page.screenshot(path=str(OUT/f'commerce-samples-{width}.png'),full_page=True)
  page.locator('#commerce-back').click();page.locator('#new-shipment').click();page.locator('#ship-kind').select_option('client');page.locator('#new-destination').click();page.locator('#destination-name').fill('Cliente de envío CI');page.locator('dialog [data-ok]').click()
  page.locator('#ship-purpose').select_option('sale');page.locator('#ship-tag').select_option('Nacional');page.locator('#ship-amount').fill('5');page.locator('#ship-status').select_option('received');page.locator('#save-shipment').click()
  assert bal()['total']==281
  page.locator('[data-sale-price]').click();assert page.locator('#sale-mode').input_value()=='shipment';page.locator('#sale-price').fill('7000');page.locator('#save-sale').click()
  assert bal()['total']==281
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lotSales.length")==2
  page.locator('#sale-mode').select_option('historical');page.locator('#sale-amount').fill('2');page.locator('#sale-price').fill('6000');page.locator('#sale-customer').fill('Cliente histórico CI');page.locator('#save-sale').click();assert bal()['total']==281
  page.locator('#sale-amount').fill('10000');page.locator('#sale-customer').fill('No guardar');page.locator('#sale-price').fill('6000');page.locator('#save-sale').click()
  assert 'Solo hay' in page.locator('#commerce-errors').inner_text();assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lotSales.length")==3
  page.evaluate('window.print=()=>{}');page.locator('#commerce-print').click();report=page.locator('#print-view').inner_text();assert 'Cliente CI' in report and 'Ingreso $0' in report and '66,000.00' in report
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Horizontal overflow'
  snapshot=page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")
  page.reload();page.locator('#lot-id').wait_for();assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")==snapshot
  assert not errors,errors
  print('PASS BROWSER',width,'sales by lot, box pricing, partial and full payments, opening samples, classification, consumption, linked price without double discount, historical sale, report, reload and no overflow')
  ctx.close()
 browser.close()
