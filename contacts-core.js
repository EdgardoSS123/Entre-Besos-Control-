/* Contact directory, including prior CRM records. No inventory changes. */
(function(root){
  'use strict';
  const COUNTRIES=['USA','México','Singapur'],copy=x=>JSON.parse(JSON.stringify(x));
  const text=x=>String(x??'').trim();
  function country(v){const k=text(v).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();return ({usa:'USA',us:'USA','united states':'USA','estados unidos':'USA',mexico:'México',mx:'México',singapur:'Singapur',singapore:'Singapur',sg:'Singapur'})[k]||'';}
  function rows(d){if(d.contacts===undefined)return[];if(!Array.isArray(d.contacts)||d.contacts.some(x=>!x||typeof x!=='object'))throw Error('No se pudo leer el directorio. No se modificaron tus datos.');return d.contacts;}
  function view(c){
    if(Array.isArray(c)){
      const contact=text(c[2]);return {country:country(c[3]),name:text(c[1])||text(c[0]),place:text(c[0]),email:/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)?contact:'',phone:/^[+\d().\s-]{5,60}$/.test(contact)?contact:'',legacyDetails:c.filter(Boolean).join(' · ')};
    }
    return {country:country(c.country||c.market||c.zone),name:text(c.name||c.contact||c.company),place:text(c.place||c.location||c.company),email:text(c.email),phone:text(c.phone||c.tel),legacyDetails:text(c.legacyDetails)};
  }
  function validate(input){
    const r={country:country(input.country),name:text(input.name),place:text(input.place),email:text(input.email),phone:text(input.phone)};
    if(!r.country)throw Error('Elige USA, México o Singapur.');
    if(!r.name||r.name.length>160)throw Error('Escribe un nombre de hasta 160 caracteres.');
    if(r.place.length>240||r.phone.length>60||r.email.length>254)throw Error('Revisa la longitud del lugar, correo o teléfono.');
    if(r.email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(r.email))throw Error('Revisa el correo electrónico.');
    return r;
  }
  function change(d,input,opt){
    const source=rows(d),editing=opt.index!==undefined;
    if(!opt.id||!opt.stamp)throw Error('Falta la referencia del cambio.');
    if(editing&&(!Number.isInteger(opt.index)||opt.index<0||opt.index>=source.length||JSON.stringify(source[opt.index])!==opt.expected))throw Error('Este contacto cambió. Ábrelo otra vez antes de guardar.');
    if(opt.remove&&!editing)throw Error('Selecciona el contacto.');
    const before=editing?source[opt.index]:null;
    const after=opt.remove?null:{...(before&&!Array.isArray(before)?before:{}),...validate(input),id:before?.id||opt.id,createdAt:before?.createdAt||opt.stamp,updatedAt:opt.stamp,...(Array.isArray(before)?{legacyRecord:copy(before),legacyDetails:view(before).legacyDetails}:{})};
    const out=copy(d);out.contacts=copy(source);
    if(opt.remove)out.contacts.splice(opt.index,1);else if(editing)out.contacts[opt.index]=after;else out.contacts.push(after);
    if(out.contactHistory!==undefined&&!Array.isArray(out.contactHistory))throw Error('Historial de contactos no válido. No se guardó.');
    out.contactHistory=[...(out.contactHistory||[]),{id:opt.id,at:opt.stamp,action:opt.remove?'delete':editing?'update':'create',before,after}];return out;
  }
  const api={COUNTRIES,rows,view,change,country,validate};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBContacts=api;
})(typeof window==='undefined'?globalThis:window);
