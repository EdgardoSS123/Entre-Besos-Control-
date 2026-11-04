"""All inputs are synthetic and isolated from the user's local storage."""
import os, json, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/')
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-dispatch-screens'));OUT.mkdir(parents=True,exist_ok=True)
seed={'lots':[{'id':'PRUEBA-ENVIO','p':0,'date':'2026-11-03','bottles':960,'ml':720,'unitCost':144,'totalCost':138240}], 'moves':[], 'contacts':[], 'costs':{}, 'inventoryOpenings':[{'lotId':'PRUEBA-ENVIO','asOf':'2026-11-03','complete':True,'rows':[{'location':'Oaxaca','tag':'Nacional','quantity':480}]}], 'documents':[{'preserve':'yes'}]}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 for width,height in [(1440,1000),(390,844),(375,812)]:
  ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<700,has_touch=width<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'?classic=1',wait_until='networkidle');page.evaluate('(d)=>localStorage.setItem("eb-v1",JSON.stringify(d))',seed);page.reload();page.locator('#show-lots').click()
  page.get_by_role('button',name='Inventario y envíos',exact=True).click();page.locator('#new-shipment').click()
  assert page.locator('#ship-unit').input_value()=='box'
  page.locator('#ship-kind').select_option('distributor');page.locator('#new-destination').click()
  page.locator('#destination-name').fill('Distribuidor Demo · Georgia');page.locator('#destination-address').fill('Dirección de prueba');page.locator('#destination-contact').fill('Contacto de prueba')
  page.locator('dialog [data-ok]').click()
  assert page.locator('#ship-to').input_value()=='Distribuidor Demo · Georgia'
  page.locator('#ship-from').select_option('Oaxaca');page.locator('#ship-tag').select_option('Nacional');page.locator('#ship-amount').fill('10');page.locator('#ship-purpose').select_option('consignment')
  assert '10 cajas = 60 botellas' in page.locator('#dispatch-preview').inner_text()
  assert 'Después del envío: 420 botellas.' in page.locator('#ship-available').inner_text()
  page.locator('#ship-cost-known').check();page.locator('#ship-cost').fill('1500');page.locator('#ship-reference').fill('GUIA-PRUEBA')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(OUT/f'dispatch-{width}.png'),full_page=True)
  page.locator('#save-shipment').click()
  b=page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'PRUEBA-ENVIO')")
  assert b['total']==420 and b['transit']==60
  assert '10 cajas (60 botellas)' in page.locator('#shipment-list').inner_text()
  page.locator('[data-receive]').click();page.locator('dialog [data-ok]').click()
  b=page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'PRUEBA-ENVIO')")
  assert b['total']==480 and b['atThirdParties']==60
  page.locator('#new-shipment').click();page.locator('#ship-kind').select_option('client');page.locator('#new-destination').click()
  page.locator('#destination-name').fill('Cliente Demo · CDMX');page.locator('dialog [data-ok]').click()
  page.locator('#ship-purpose').select_option('sale');page.locator('#ship-tag').select_option('Nacional');page.locator('#ship-amount').fill('5');page.locator('#ship-status').select_option('received');page.locator('#save-shipment').click()
  b=page.evaluate("EBLedger.balance(JSON.parse(localStorage.getItem('eb-v1')),'PRUEBA-ENVIO')")
  assert b['total']==450 and b['deliveredSales']==30
  assert 'entregado al comprador' in page.locator('#shipment-list').inner_text().lower()
  assert 'Entrega por venta' in page.locator('#shipment-list').inner_text()
  page.locator('#new-shipment').click();page.locator('#ship-tag').select_option('Nacional');page.locator('#ship-amount').fill('66');page.locator('#save-shipment').click()
  assert 'Solo hay 390' in page.locator('#inventory-errors').inner_text()
  assert page.evaluate("JSON.parse(localStorage.getItem('eb-v1')).lotShipments.length")==2
  page.evaluate('window.print=()=>{}');page.locator('#stock-print').click()
  report=page.locator('#print-view').inner_text()
  assert '10 cajas (60 botellas)' in report and 'Entrega por venta' in report and 'Distribuidor' in report
  page.reload();page.locator('#lot-id').wait_for()
  data=page.evaluate("JSON.parse(localStorage.getItem('eb-v1'))")
  assert len(data['lotShipments'])==2 and data['lots'][0]['unitCost']==144 and data['documents']==[{'preserve':'yes'}]
  assert data['lotShipments'][0]['destination']['contact']=='Contacto de prueba'
  assert not errors,errors
  print('PASS DISPATCH BROWSER',width,': create destination, box route, contact, freight, consignment, sale, report and reload')
  ctx.close()
 browser.close()
