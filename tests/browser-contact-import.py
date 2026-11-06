import copy,json,os,shutil,subprocess,tempfile,time,urllib.request,zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from playwright.sync_api import sync_playwright,expect
ROOT=Path.cwd();OUT=Path('/tmp/eb-import-review');OUT.mkdir(exist_ok=True)
PUB=Path(tempfile.mkdtemp(prefix='eb-import-public-'))
for f in ROOT.iterdir():
 if f.suffix in ['.html','.js','.css','.jpg','.webmanifest']:shutil.copy(f,PUB/f.name)
shutil.copy(ROOT/'control.html',PUB/'index.html')
for name in ['vendor','icons']:shutil.copytree(ROOT/name,PUB/name)
rows=[['Kissology-style sample: SYNTHETIC DATA'],['Contact Name','Company','City','Email','Phone'],['Jane Example','Example Store','Austin','jane@example.test','+1 512 555 0100'],['Jane Example','Example Store','Austin','jane@example.test','+1 512 555 0100'],['','Second Store','Dallas','',''],['Invalid','Bad Email','Houston','not-an-email','']]
def sheet_xml(rows):
 return '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join('<row r="'+str(ri)+'">'+''.join('<c r="'+chr(65+ci)+str(ri)+'" t="inlineStr"><is><t>'+escape(value)+'</t></is></c>' for ci,value in enumerate(row))+'</row>' for ri,row in enumerate(rows,1))+'</sheetData></worksheet>'
fixture=OUT/'synthetic-contacts.xlsx'
with zipfile.ZipFile(fixture,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="USA" sheetId="1" r:id="rId1"/></sheets></workbook>')
 z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>')
 z.writestr('xl/worksheets/sheet1.xml',sheet_xml(rows))
seed={'lots':[{'id':'KEEP','p':0,'bottles':60,'unitCost':200,'totalCost':12000,'ml':720}],'moves':[],'contacts':[],'materials':[{'name':'Keep','qty':1}],'supplies':[]}
server=subprocess.Popen(['python3','-m','http.server','8779','--bind','127.0.0.1'],cwd=PUB,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
base='http://127.0.0.1:8779/'
for _ in range(40):
 try:urllib.request.urlopen(base,timeout=1);break
 except Exception:time.sleep(.1)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
  for width in (1440,390):
   state={'data':copy.deepcopy(seed),'revision':1};errors=[]
   ctx=browser.new_context(viewport={'width':width,'height':900},accept_downloads=True)
   def handle(route):
    request=route.request;path=request.url.split('/api/')[1]
    if path=='session':reply={'authenticated':True,'user':{'username':'test','name':'Test','role':'editor'},'csrf':'only-local-test'}
    elif path.startswith('state'):
     if request.method=='PUT':
      payload=request.post_data_json;assert payload['revision']==state['revision'];state['revision']+=1;state['data']=payload['data'];reply={'ok':True,'revision':state['revision']}
     elif '?since='+str(state['revision']) in path:reply={'unchanged':True,'revision':state['revision']}
     else:reply=state
    else:raise AssertionError(path)
    route.fulfill(status=200,content_type='application/json',body=json.dumps(reply))
   ctx.route('**/api/**',handle);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base+'office.html?section=contacts&country=USA');expect(page.locator('#contact-import-button')).to_be_visible();expect(page.locator('[data-country="USA"]')).to_have_class('selected')
   page.locator('#contact-import-button').click();expect(page.locator('#ci-country')).to_have_value('USA');page.locator('#contact-import-file').set_input_files(str(fixture));expect(page.locator('#ci-count')).to_contain_text('2 nuevos');expect(page.locator('#ci-count')).to_contain_text('1 coincidencias');expect(page.locator('#ci-count')).to_contain_text('1 filas por corregir');expect(page.locator('#ci-preview')).to_contain_text('Example Store · Austin');expect(page.locator('#ci-preview')).to_contain_text('Second Store')
   page.screenshot(path=str(OUT/f'import-preview-{width}.png'),full_page=True)
   page.locator('#ci-save').click();expect(page.locator('#ci-content')).to_contain_text('2 contactos confirmados',timeout=20000);page.locator('#ci-close').click();expect(page.locator('.office-contact')).to_have_count(2)
   page.reload();expect(page.locator('.office-contact')).to_have_count(2);page.locator('#contact-import-button').click();page.locator('#contact-import-file').set_input_files(str(fixture));expect(page.locator('#ci-count')).to_contain_text('0 nuevos');expect(page.locator('#ci-save')).to_be_disabled();page.locator('#ci-close').click()
   for k in seed:
    if k!='contacts':assert state['data'][k]==seed[k],k
   assert len(state['data']['contacts'])==2
   assert state['data']['contacts'][1]['email']==''
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
   page.screenshot(path=str(OUT/f'import-saved-{width}.png'),full_page=True)
   assert not errors,errors
   ctx.close();print('PASS XLSX upload and contacts:',width,flush=True)
  # Shared strings are read without evaluation of formulas; also reject non-XLSX files.
  ctx=browser.new_context();page=ctx.new_page();page.goto(base+'office.html')
  page.add_script_tag(url=base+'vendor/fflate.js');page.add_script_tag(url=base+'contacts-core.js');page.add_script_tag(url=base+'contacts-import.js')
  assert page.evaluate("()=>{try{window.EBContactImport.xlsx(new Uint8Array([1,2,3]));return false}catch(e){return true}}")
  ctx.close();browser.close()
finally:
 server.terminate();server.wait(timeout=10)
print('PASS: local XLSX parsing, preview, country selection, invalid email excluded, no duplicates on retry, cloud acknowledgement and untouched other data.')
