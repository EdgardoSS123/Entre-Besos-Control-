from pathlib import Path

def replace(path,old,new):
    p=Path(path);s=p.read_text()
    if new in s:return
    assert s.count(old)==1,(path,old[:100],s.count(old))
    p.write_text(s.replace(old,new,1))

replace('materials-ui.js',"const KEY='eb-v1', C=window.EBMaterials", "const KEY='eb-v1', OTHER='__eb_other__', C=window.EBMaterials")
replace('materials-ui.js',"options(names,'Selecciona un insumo')+'</select>","options(names,'Selecciona un insumo')+'<option value=\"'+OTHER+'\">Otros</option></select>")
replace('materials-ui.js','<input class="hidden" id="material-custom-name" maxlength="160" aria-label="Nombre del nuevo insumo">','<label class="hidden" id="material-custom-label" for="material-custom-name">Especifica el concepto *</label><input class="hidden" id="material-custom-name" maxlength="160" aria-label="Nombre del nuevo insumo" placeholder="Escribe el nombre" disabled>')
old="    if(supplies)$('material-custom').onclick=()=>{custom=!custom;$('material-custom-name').classList.toggle('hidden',!custom);$('material-custom-name').required=custom;$('material-name').required=!custom;$('material-name').disabled=custom;$('material-custom').textContent=custom?'Elegir del catálogo':'+ Otro insumo';changed=true;(custom?$('material-custom-name'):$('material-name')).focus();};"
new="""    if(supplies){
      $('material-custom').onclick=()=>{setCustom(!custom,true);changed=true;};
      $('material-name').onchange=()=>{setCustom($('material-name').value===OTHER,true);changed=true;};
    }"""
replace('materials-ui.js',old,new)
old="    if($('material-custom-name')){$('material-custom-name').classList.add('hidden');$('material-custom-name').required=false;$('material-name').disabled=false;$('material-name').required=true;$('material-custom').textContent='+ Otro insumo';}"
replace('materials-ui.js',old,"    if($('material-custom-name'))setCustom(false);")
replace('materials-ui.js','  function render() {',"""  function setCustom(active,focus=false){
    custom=active;
    const input=$('material-custom-name'),select=$('material-name');
    input.classList.toggle('hidden',!active);input.required=active;input.disabled=!active;
    $('material-custom-label').classList.toggle('hidden',!active);
    select.disabled=false;select.required=true;
    if(active)select.value=OTHER;else if(select.value===OTHER)select.value='';
    $('material-custom').textContent=active?'Elegir del catálogo':'+ Otro insumo';
    if(focus)(active?input:select).focus();
  }
  function render() {""")

scripts='<script src="./vendor/jspdf.umd.min.js?v=4.2.1" defer></script><script src="./vendor/jspdf.plugin.autotable.min.js?v=5.0.9" defer></script><script src="./reports-data.js?v=pdf1" defer></script><script src="./reports-pdf.js?v=pdf1" defer></script>'
for name in ['control.html','materials.html']:
    p=Path(name);s=p.read_text()
    if './reports-pdf.js' not in s:
        assert s.count('</body>')==1
        s=s.replace('</body>',scripts+'</body>')
        s=s.replace('</head>','<style>#eb-report-pdf{min-width:44px;white-space:nowrap}.topbar .controls-row{flex-shrink:0}@media(max-width:540px){.topbar .controls-row{gap:6px}.topbar .chip{display:none}.topbar{gap:8px}}</style></head>')
        p.write_text(s)

replace('materials.html','./materials-ui.js?v=materials1','./materials-ui.js?v=others-pdf1')
# Avoid a MutationObserver loop when a print button is already labelled PDF.
replace('reports-pdf.js',"b.textContent='PDF';b.title='Descargar reporte PDF con logo';", "if(b.textContent!=='PDF')b.textContent='PDF';b.title='Descargar reporte PDF con logo';")

p=Path('Dockerfile');s=p.read_text()
if 'COPY pdf-deps/' not in s:
    marker='FROM nginx:alpine'
    assert s.count(marker)==1
    s=s.replace(marker,'COPY pdf-deps/ ./pdf-deps/\nCOPY .github/scripts/build-pdf.sh ./build-pdf.sh\nRUN sh ./build-pdf.sh\nCOPY reports-data.js reports-pdf.js ./\nRUN node --check reports-data.js && node --check reports-pdf.js\n\n'+marker)
    s=s.replace('COPY nginx.conf','COPY reports-data.js reports-pdf.js /usr/share/nginx/html/\nCOPY --from=verify /verify/vendor /usr/share/nginx/html/vendor\nCOPY nginx.conf',1)
    s=s.replace('for asset in ','for asset in reports-data.js reports-pdf.js vendor/jspdf.umd.min.js vendor/jspdf.plugin.autotable.min.js ',1)
    p.write_text(s)
print('Integrated Otros and PDF report actions. No business data migrations.')
