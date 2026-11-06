from pathlib import Path
p=Path('office.html');s=p.read_text()
if '/contacts-import.js' not in s:
    marker='<script type="application/x-eb-shared" src="/office-nav.js'
    assert s.count(marker)==1
    extra='<script type="application/x-eb-shared" src="/vendor/fflate.js?v=contact-import1"></script><script type="application/x-eb-shared" src="/contacts-import.js?v=contact-import1"></script>'
    s=s.replace(marker,extra+marker,1)
    p.write_text(s)
p=Path('office-ui.js');s=p.read_text()
if 'contactCountryParam' not in s:
    old="let editing=null,dirty=false,selected='México',query='';"
    assert s.count(old)==1
    s=s.replace(old,"const contactCountryParam=new URLSearchParams(location.search).get('country');\nlet editing=null,dirty=false,selected=C.COUNTRIES.includes(contactCountryParam)?contactCountryParam:'México',query='';",1)
    p.write_text(s)
p=Path('.github/scripts/build-pdf.sh');s=p.read_text()
if 'vendor/fflate.js' not in s:
    s+='\n# Reuse the exact compression dependency already pinned by the PDF lockfile.\ncp pdf-deps/node_modules/fflate/umd/index.js vendor/fflate.js\ncp pdf-deps/node_modules/fflate/LICENSE vendor/fflate-LICENSE.txt\nnode --check vendor/fflate.js\n'
    p.write_text(s)
p=Path('Dockerfile');s=p.read_text()
if 'COPY contacts-import.js ./' not in s:
    marker='FROM nginx:alpine AS static'
    assert s.count(marker)==1
    s=s.replace(marker,'COPY contacts-import.js ./\nCOPY tests/contact-import.cjs ./tests/\nRUN node --check contacts-import.js && node tests/contact-import.cjs\n\n'+marker,1)
    s=s.replace('COPY nginx.conf','COPY contacts-import.js /usr/share/nginx/html/\nCOPY nginx.conf',1)
    s=s.replace('for asset in ','for asset in contacts-import.js vendor/fflate.js ',1)
    p.write_text(s)
print('Excel importer integrated. No contacts, credentials or business records touched.')
