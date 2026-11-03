"""Each test uses a clean browser profile, never the user's browser storage."""
import os, shutil, json
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('EB_TEST_URL','https://entre-besos-web-production.up.railway.app/')
OUT=os.environ.get('EB_SCREENSHOTS','/tmp/eb-screens')
Path(OUT).mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844),(375,812)]:
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'?check=bodegas33',wait_until='networkidle')
  page.locator('#lot-id').wait_for()
  assert page.evaluate('EBCosts.version')=='eb-costos-3.4'
  assert page.locator('aside.summary').count()==0
  assert page.locator('#pin-summary').count()==0
  assert page.locator('#palletSize').get_attribute('type')=='hidden'
  assert page.locator('#palletSize').input_value()=='480'
  assert page.locator('#boxSize').input_value()=='6'
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.wait_for_function('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)')
  page.locator('#lot-id').fill('TEST-LOT-01');page.locator('#producedLiters').fill('500');page.locator('#lossLiters').fill('10');page.locator('#liquid').fill('200')
  assert page.locator('#bottles').input_value()=='680'
  assert '1 pallet + 33 cajas sueltas + 2 botellas sueltas' in page.locator('#pack-description').inner_text()
  page.locator('#producedLiters').fill('518.4');page.locator('#lossLiters').fill('0');page.locator('#pack-halves').check()
  assert '1 pallet + 1 medio pallet'==page.locator('#pack-description').inner_text()
  page.locator('#producedLiters').fill('500');page.locator('#lossLiters').fill('10');page.locator('#amount-0').fill('20')
  save='#mobile-save-button' if width<700 else '#save-lot'
  page.screenshot(path=OUT+'/editor-'+str(width)+'.png',full_page=True)
  page.locator(save).click();assert page.locator('.saved-lot').count()==1
  initial_cost=page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots[0].unitCost")
  page.get_by_role('button',name='Registrar dónde está').click()
  assert page.locator('#opening-panel').count()==1
  row=page.locator('.opening-row')
  row.nth(0).locator('[data-tag]').select_option('Nacional');row.nth(0).locator('[data-amount]').fill('1');row.nth(0).locator('[data-unit]').select_option('pallet')
  row.nth(1).locator('[data-tag]').select_option('Exportación');row.nth(1).locator('[data-amount]').fill('20');row.nth(1).locator('[data-unit]').select_option('box')
  page.locator('#opening-complete').check();page.locator('#save-opening').click()
  assert page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'TEST-LOT-01').total")==600
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).moves.length")==0
  page.locator('#new-shipment').click()
  page.locator('#ship-tag').select_option('Nacional');page.locator('#ship-amount').fill('10');page.locator('#ship-unit').select_option('box')
  page.locator('#ship-cost-known').check();page.locator('#ship-cost').fill('1500');page.locator('#save-shipment').click()
  b=page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'TEST-LOT-01')")
  assert b['total']==540 and b['transit']==60 and b['knownTotal']==600
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots[0].unitCost")==initial_cost
  page.locator('[data-receive]').click();page.locator('dialog [data-ok]').click()
  b=page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'TEST-LOT-01')")
  assert b['total']==600 and b['transit']==0
  assert page.locator('#edit-opening').is_disabled()
  page.locator('#new-shipment').click();page.locator('#ship-tag').select_option('Nacional');page.locator('#ship-amount').fill('421');page.locator('#save-shipment').click()
  assert 'Solo hay 420' in page.locator('#inventory-errors').inner_text()
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lotShipments.length")==1
  page.locator('#ship-history').check();page.locator('#ship-amount').fill('');page.locator('#ship-cost-known').check();page.locator('#ship-cost').fill('100');page.locator('#ship-currency').select_option('USD');page.locator('#ship-cost-included').check();page.locator('#save-shipment').click()
  assert page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'TEST-LOT-01').total")==600
  assert page.evaluate("EBLedger.costTotals(JSON.parse(localStorage.getItem('eb-v1')),'TEST-LOT-01').byCurrency.MXN")==1500
  assert page.evaluate("EBLedger.costTotals(JSON.parse(localStorage.getItem('eb-v1')),'TEST-LOT-01').included.USD")==100
  page.screenshot(path=OUT+'/stock-'+str(width)+'.png',full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.evaluate('window.print=()=>{}');page.locator('#stock-print').click();assert 'En bodegas: 600' in page.locator('#print-view').inner_text()
  page.locator('#nav-warehouses' if width>950 else '#mobile-warehouses').click();page.locator('#warehouse-filter').select_option('CDMX');assert '180' in page.locator('.warehouse-lots').inner_text()
  page.reload();page.locator('#lot-id').wait_for()
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).inventoryOpenings.length")==1
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots[0].unitCost")==initial_cost
  page.locator('#producedLiters').fill('1000');page.locator(save).click();assert 'inventario inicial' in page.locator('#form-errors').inner_text()
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lots[0].bottles")==680
  assert not errors,errors
  print('PASS BROWSER',width,': top summary, 80x6, halves, initial balance, labels, transit, receiving, historical costs, report, reload, preservation, no overflow')
  ctx.close()
 ctx=browser.new_context();page=ctx.new_page()
 old={'lots':[{'id':'OLD','p':0,'date':'2026-11-01','ml':720,'bottles':600,'liters':432,'liquid':200,'boxSize':6,'palletSize':600,'costingVersion':3,'unitCost':197.5,'totalCost':118500}], 'moves':[], 'contacts':[], 'costs':{},'documents':[{'keep':'unchanged'}]}
 page.add_init_script('localStorage.setItem("eb-v1",'+json.dumps(json.dumps(old))+');')
 page.goto(BASE,wait_until='networkidle');page.locator('#show-lots').click();page.locator('[data-edit="OLD"]').click()
 assert page.locator('#palletSize').input_value()=='600'
 assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")==old
 assert 'Empaque histórico conservado' in page.locator('.pack-rule').inner_text()
 print('PASS: historical capacities and unrelated records preserved')
 ctx.close();browser.close()
