"""Isolated browser storage, never the user's records."""
import os,shutil,subprocess,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from workspace_test import Workspace
workspace=Workspace()
BASE=workspace.base
OUT=Path(os.environ.get('EB_SCREENSHOTS','/tmp/eb-history-review'));OUT.mkdir(parents=True,exist_ok=True)
fixture=OUT/'fixture.json';subprocess.run(['node','tests/history-reconciliation.cjs'],check=True,env={**os.environ,'EB_FIXTURE':str(fixture)})
state=fixture.read_text()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
 for w in (1440,390):
  ctx=workspace.context(browser,viewport={'width':w,'height':960 if w>700 else 844},is_mobile=w<700,has_touch=w<700)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  workspace.goto(page,BASE,wait_until='networkidle')
  page.evaluate('(raw)=>localStorage.setItem("eb-v1",raw)',state);workspace.reload(page,wait_until='networkidle')
  page.locator('[data-simple-open="FILTER-TEST"]').click();page.locator('.simple-history').evaluate('(e)=>e.open=true')
  snapshot=page.evaluate('localStorage.getItem("eb-v1")');total=page.locator('#simple-current').inner_text()
  h=page.locator('#history-warehouse');expect(h).to_be_visible();h.select_option('USA')
  assert page.locator('[data-history-kind="sale"]:visible').count()==1
  assert page.locator('[data-history-kind="move"]:visible').count()==0
  assert '1 ventas' in page.locator('#history-counts').inner_text()
  h.select_option('CDMX');assert page.locator('[data-history-kind="sale"]:visible').count()==1
  assert page.locator('[data-history-kind="move"]:visible').count()==1
  assert page.locator('[data-history-kind="sample"]:visible').count()==1
  h.select_option('EB1-1 · Edgardo');assert page.locator('[data-history-kind="move"]:visible').count()==1
  assert page.locator('[data-history-kind="sale"]:visible').count()==0
  h.select_option('__unknown__');assert page.locator('[data-history-kind="sale"]:visible').count()==1
  h.select_option('Singapur');expect(page.locator('#history-empty')).to_be_visible()
  assert page.locator('#simple-current').inner_text()==total and page.evaluate('localStorage.getItem("eb-v1")')==snapshot
  h.select_option('USA');page.locator('[data-record-edit="sale-usa"]').click()
  expect(page.locator('#edit-price')).to_have_value('100');assert page.locator('#edit-basis').count()==0
  page.locator('dialog [data-save]').click();page.wait_for_function("()=>!document.querySelector('dialog[open]')||!!document.querySelector('dialog[open] [data-error]:not(.hidden)')");assert page.locator('dialog[open]').count()==0,page.locator('dialog[open]').inner_text()
  assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1")).lotSales.find(x=>x.id==="sale-usa").totalCents')==60000
  page.locator('.simple-history').evaluate('(e)=>e.open=true');h=page.locator('#history-warehouse');h.select_option('CDMX')
  page.locator('[data-record-edit="sale-mx"]').click();page.locator('#edit-amount').fill('100');page.locator('#edit-unit').select_option('bottle');page.locator('dialog [data-save]').click()
  page.wait_for_function("()=>!document.querySelector('dialog[open]')||!!document.querySelector('dialog[open] [data-error]:not(.hidden)')");assert page.locator('dialog[open]').count()==0,page.locator('dialog[open]').inner_text();expect(page.locator('.stock-warning')).to_be_visible()
  assert page.evaluate('EBLedger.available(JSON.parse(localStorage.getItem("eb-v1")),"FILTER-TEST","CDMX","Nacional")')==-54
  assert '-54' in page.locator('[data-place="CDMX"]').inner_text()
  page.locator('#simple-sale-tab').click();page.locator('#simple-source').select_option(json.dumps(['CDMX','Nacional'],separators=(',',':'),ensure_ascii=False));page.locator('#simple-amount').fill('1');page.locator('#simple-unit').select_option('bottle');page.locator('#simple-price').fill('1100');page.locator('#simple-save').click()
  assert page.evaluate('EBLedger.available(JSON.parse(localStorage.getItem("eb-v1")),"FILTER-TEST","CDMX","Nacional")')==-55
  assert page.evaluate('JSON.parse(localStorage.getItem("eb-v1")).lotSampleActions.length')==1
  page.locator('.simple-history').evaluate('(e)=>e.open=true');page.locator('#history-warehouse').select_option('CDMX');page.locator('.simple-history').scroll_into_view_if_needed()
  page.screenshot(path=str(OUT/f'history-{w}.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  saved=page.evaluate('localStorage.getItem("eb-v1")');workspace.reload(page,wait_until='networkidle');assert saved==page.evaluate('localStorage.getItem("eb-v1")')
  assert not errors,errors
  print('PASS HISTORY',w,'filter sales/moves both endpoints/samples/unknown, no stock mutation, bottle edit, negative save and reload')
  ctx.close()
 browser.close()
