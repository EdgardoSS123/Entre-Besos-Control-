import os, json, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
URL=os.environ.get('EB_TEST_URL','http://127.0.0.1:8765/').rstrip('/')+'/'
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-materials-checks'));OUT.mkdir(exist_ok=True,parents=True)
seed={'lots':[{'id':'PRESERVE','unitCost':237.66,'bottles':438,'p':2,'date':'2024-11-03'}],'moves':[],'sales':[{'amount':9}],'contacts':[],'costs':{},'materials':[{'name':'Material histórico','qty':7,'loc':'Oaxaca','other':'keep'}]}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
 for width in (1440,390,375):
  ctx=browser.new_context(viewport={'width':width,'height':1000},accept_downloads=True)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(URL+'materials.html?kind=marketing');page.evaluate('(s)=>localStorage.setItem("eb-v1", JSON.stringify(s))',seed);page.reload()
  expect(page.locator('#material-name')).to_have_value('');expect(page.locator('#material-qty')).to_have_value('');expect(page.locator('#material-cost')).to_have_value('')
  expect(page.locator('[data-record="0"]')).to_contain_text('Sin capturar');assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1")).materials[0]')==seed['materials'][0]
  page.locator('#material-name').fill('Playeras');page.locator('#material-location').select_option('CDMX');page.locator('#material-presentation').fill('M');page.locator('#material-qty').fill('20');page.locator('#material-cost').fill('3500')
  expect(page.locator('#material-unit')).to_have_text('$175.00');page.locator('#material-save').click();expect(page.locator('[data-record="1"]')).to_contain_text('$3,500.00')
  page.reload();expect(page.locator('[data-record="1"]')).to_contain_text('Playeras');page.locator('[data-edit-material="1"]').click();page.locator('#material-qty').fill('30');page.locator('#material-cost').fill('4500');expect(page.locator('#material-unit')).to_have_text('$150.00');page.locator('#material-save').click()
  page.locator('#material-filter').select_option('CDMX');expect(page.locator('.material-record')).to_have_count(1);page.locator('#material-filter').select_option('');expect(page.locator('.material-record')).to_have_count(2)
  page.locator('#material-search').fill('histórico');expect(page.locator('.material-record')).to_have_count(1);page.locator('#material-search').fill('')
  page.screenshot(path=str(OUT/f'marketing-{width}.png'),full_page=True)
  page.locator('[data-kind="supplies"]:visible').first.click();expect(page.locator('#material-name')).to_have_value('');expect(page.locator('.material-record')).to_have_count(0)
  for name in ['Botellas vacías','Tapones','Etiquetas','Marbetes','Precintos','Hologramas CRM','Cintillos','Corrugados','Pallets']:assert name in page.locator('#material-name').inner_text()
  page.locator('#material-name').select_option('Botellas vacías');page.locator('#material-location').select_option('Oaxaca');page.locator('#material-presentation').fill('720 ml');page.locator('#material-qty').fill('100');page.locator('#material-cost').fill('2500');expect(page.locator('#material-unit')).to_have_text('$25.00');page.locator('#material-save').click()
  page.locator('#material-custom').click();page.locator('#material-custom-name').fill('Insumo especial');page.locator('#material-location').select_option('Oaxaca');page.locator('#material-qty').fill('2');page.locator('#material-cost').fill('0');page.locator('#material-save').click();assert 'Insumo especial' in page.locator('#material-name').inner_text()
  page.locator('[data-edit-material="0"]').click();page.locator('#material-qty').fill('120');page.locator('#material-cost').fill('3000');page.locator('#material-save').click()
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Horizontal overflow at {width}'
  page.screenshot(path=str(OUT/f'insumos-{width}.png'),full_page=True)
  stored=page.evaluate('JSON.parse(localStorage.getItem("eb-v1"))');assert stored['materials'][1]['qty']==30;assert stored['supplies'][0]['qty']==120
  for k in ['lots','moves','sales','contacts','costs']:assert stored[k]==seed[k]
  page.locator('[data-edit-material="0"]').click();page.locator('#material-qty').fill('121')
  page.evaluate('()=>{const d=JSON.parse(localStorage.getItem("eb-v1"));d.supplies[0].qty=130;localStorage.setItem("eb-v1",JSON.stringify(d));}')
  page.locator('#material-save').click();expect(page.locator('#material-error')).to_contain_text('cambió');assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1")).supplies[0].qty')==130
  page.on('dialog',lambda d:d.accept());page.locator('#material-cancel').click();page.locator('[data-delete-material="1"]').click();expect(page.locator('.material-record')).to_have_count(1)
  with page.expect_download() as event:page.locator('[data-backup]:visible').first.click()
  backup=Path(event.value.path());b=json.loads(backup.read_text());assert b['materials'][1]['qty']==30;assert len(b['supplies'])==1;assert b['lots']==seed['lots']
  page.locator('#material-name').select_option('Tapones');page.locator('#material-location').select_option('Oaxaca');page.locator('#material-qty').fill('5');page.locator('#material-cost').fill('10')
  page.evaluate('Storage.prototype.setItem = function(){throw new DOMException("Sin espacio","QuotaExceededError")};')
  page.locator('#material-save').click();expect(page.locator('#material-error')).to_contain_text('No se guardó');expect(page.locator('#material-qty')).to_have_value('5')
  assert not errors,errors;ctx.close();print('PASS MATERIALS UI',width)
 browser.close()
