(function(){
  'use strict';
  const $=id=>document.getElementById(id),shareURL=new URL('/instalar.html',location.origin).href;
  const standalone=()=>window.matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
  const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  let installPrompt=null,shareBusy=false,pending=null,dialog=null,restoreBusy=false;
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function status(text,error=false){const e=$('eb-app-status');if(e){e.textContent=text;e.dataset.error=String(error);e.hidden=false;}}
  function markInstalled(){const installed=standalone(),b=$('eb-install-action');if(!b)return;b.hidden=installed;$('eb-install-state').textContent=installed?'Ya estás usando Entre Besos como app.':'Tu logo en la pantalla de inicio.';b.textContent=installPrompt?'Instalar app':ios?'Cómo instalar en iPhone':'Instalar en mi dispositivo';if(installed)$('eb-install-guide').hidden=true;}
  function panel(){return '<div class="eb-app-heading"><img src="/icons/eb-192.png" width="88" height="88" alt="Logo original de Entre Besos"><div><p class="eb-app-eyebrow">CONTROL INTERNO</p><h1 id="eb-app-title">Entre Besos</h1><p id="eb-install-state">Tu logo en la pantalla de inicio.</p></div></div>'+
    '<div class="eb-app-actions"><button type="button" id="eb-install-action" class="eb-app-primary">Instalar en mi dispositivo</button><button type="button" id="eb-share-action" class="eb-app-secondary">Compartir app</button></div>'+
    '<div id="eb-install-guide" class="eb-install-guide" hidden><h2>En iPhone o iPad</h2><ol><li>Abre esta página en <strong>Safari</strong>.</li><li>Toca <strong>Compartir</strong> (cuadro con flecha hacia arriba). Puede estar dentro de Más.</li><li>Elige <strong>Agregar a pantalla de inicio</strong>.</li><li>Activa <strong>Abrir como app web</strong>, si aparece, y toca <strong>Agregar</strong>.</li></ol><p>El nombre será <strong>Entre Besos</strong>. Abre el ícono para usarla sin la barra de direcciones.</p><p class="eb-app-note">En Android o PC, usa Instalar app en el menú del navegador cuando esté disponible. No es una descarga del App Store.</p></div>'+
    '<div class="eb-share-link"><label for="eb-app-link">Enlace para compartir</label><div><input id="eb-app-link" type="url" readonly value="'+esc(shareURL)+'"><button type="button" id="eb-copy-action" class="eb-app-secondary">Copiar</button></div><small>Solo comparte el acceso a la app; no envía tus registros ni contraseñas.</small></div>'+
    '<div class="eb-app-data-note"><strong>Protege tus datos antes de instalar.</strong><p>Los registros se guardan en este navegador. El acceso instalado puede tener almacenamiento separado; todavía no hay sincronización entre dispositivos. Guarda un respaldo antes de instalar o cambiar de acceso.</p><button type="button" id="eb-app-backup" class="eb-app-secondary">Guardar respaldo</button></div>'+
    '<details class="eb-app-recovery"><summary>¿La app instalada aparece vacía?</summary><p>Recupera el archivo JSON generado con Respaldo. Solo se permite en un dispositivo vacío: nunca reemplaza registros existentes ni combina bases.</p><label class="eb-file-label" for="eb-backup-file">Seleccionar respaldo</label><input id="eb-backup-file" type="file" accept=".json,application/json"><div id="eb-restore-preview" hidden><p id="eb-restore-summary"></p><button type="button" class="eb-app-primary" id="eb-restore-confirm">Importar en este dispositivo vacío</button><button type="button" class="eb-app-secondary" id="eb-restore-cancel">Cancelar</button></div></details>'+
    '<p id="eb-app-status" class="eb-app-status" role="status" aria-live="polite" hidden></p>';}
  function capturePending(){return ['material-name','material-custom-name','material-qty','material-cost'].some(id=>$(id)&&$(id).value!=='');}
  function makePanel(){
    const landing=$('eb-install-content');if(landing){landing.innerHTML=panel()+'<a class="eb-open-app" href="/">Abrir Entre Besos →</a>';bind();return;}
    dialog=document.createElement('dialog');dialog.className='eb-install-sheet';dialog.id='eb-install-sheet';dialog.setAttribute('aria-labelledby','eb-app-title');dialog.innerHTML='<button type="button" class="eb-app-close" aria-label="Cerrar instalación">×</button>'+panel();document.body.append(dialog);
    dialog.querySelector('.eb-app-close').onclick=()=>dialog.close();
    dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});bind();
    const host=document.querySelector('.topbar .controls-row');if(host&&!$('eb-app-menu')){const b=document.createElement('button');b.type='button';b.id='eb-app-menu';b.className='secondary';b.textContent='App';b.setAttribute('aria-label','Instalar o compartir Entre Besos');b.onclick=()=>{markInstalled();dialog.showModal();};host.append(b);}
  }
  async function install(){
    if(installPrompt){const prompt=installPrompt;installPrompt=null;try{await prompt.prompt();const result=await prompt.userChoice;status(result.outcome==='accepted'?'Solicitud aceptada. Busca Entre Besos en tus aplicaciones.':'Puedes instalarla después desde el menú del navegador.');}catch(e){$('eb-install-guide').hidden=false;status('Usa las instrucciones de instalación.');}markInstalled();return;}
    $('eb-install-guide').hidden=false;$('eb-install-guide').scrollIntoView({block:'nearest',behavior:'smooth'});
  }
  async function copyLink(){
    try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(shareURL);status('Enlace copiado. Pégalo en WhatsApp, Mensajes o correo.');return;}}catch(e){}
    const input=$('eb-app-link');input.focus();input.select();input.setSelectionRange(0,input.value.length);
    try{if(document.execCommand('copy')){status('Enlace copiado.');return;}}catch(e){}
    status('Mantén presionado el enlace seleccionado y elige Copiar.');
  }
  async function share(){
    if(shareBusy)return;shareBusy=true;$('eb-share-action').disabled=true;
    try{if(typeof navigator.share==='function'){await navigator.share({title:'Entre Besos Control',text:'Instala Entre Besos Control con su logo en la pantalla de inicio.',url:shareURL});status('Enlace preparado para compartir.');}else await copyLink();}
    catch(e){status(e.name==='AbortError'?'No se compartió el enlace.':'No se pudo abrir Compartir. Usa Copiar para enviar el enlace.',e.name!=='AbortError');}
    finally{shareBusy=false;$('eb-share-action').disabled=false;}
  }
  function backup(){
    try{const raw=localStorage.getItem('eb-v1');if(!raw){status('Este acceso todavía no tiene registros. Genera el respaldo desde el navegador donde están tus datos.');return;}
      const url=URL.createObjectURL(new Blob([raw],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='Entre-Besos-respaldo-'+new Date().toISOString().slice(0,10)+'.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),120000);status('Respaldo generado. Conserva ese archivo antes de cambiar de acceso.');
    }catch(e){status('No se pudo generar el respaldo. No borres los datos del sitio.',true);}
  }
  async function chooseFile(){
    pending=null;$('eb-restore-preview').hidden=true;
    const file=$('eb-backup-file').files[0];if(!file)return;
    try{if(file.size>10*1024*1024)throw Error('El archivo supera 10 MB.');if(capturePending())throw Error('Primero guarda o cancela tu captura de materiales.');
      const B=window.EBDeviceBackup,expected=B.inspect(localStorage);if(expected.occupied)throw Error('Este acceso ya tiene datos o una captura pendiente. No se reemplazará nada.');
      const raw=await file.text(),d=B.parse(raw);pending={raw,expected};
      $('eb-restore-summary').textContent='El archivo contiene '+d.lots.length+' lotes, '+(d.materials||[]).length+' registros de marketing y '+(d.supplies||[]).length+' de insumos. Se recuperará únicamente en este dispositivo.';$('eb-restore-preview').hidden=false;status('Archivo revisado. Confirma la importación para recuperar los datos.');
    }catch(e){status(e.message,true);}
  }
  function restore(){if(restoreBusy||!pending)return;restoreBusy=true;
    try{if(capturePending())throw Error('Primero guarda o cancela tu captura.');window.EBDeviceBackup.restore(localStorage,pending.raw,pending.expected);pending=null;location.assign('/');}
    catch(e){status('No se importó. '+e.message,true);restoreBusy=false;}
  }
  function bind(){
    $('eb-install-action').onclick=install;$('eb-share-action').onclick=share;$('eb-copy-action').onclick=copyLink;$('eb-app-backup').onclick=backup;
    $('eb-backup-file').onchange=chooseFile;$('eb-restore-confirm').onclick=restore;$('eb-restore-cancel').onclick=()=>{pending=null;$('eb-backup-file').value='';$('eb-restore-preview').hidden=true;};markInstalled();
  }
  window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;markInstalled();});
  window.addEventListener('appinstalled',()=>{installPrompt=null;markInstalled();status('Entre Besos quedó instalada.');});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',makePanel,{once:true});else makePanel();
})();
