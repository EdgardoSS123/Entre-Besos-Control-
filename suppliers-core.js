/* Supplier directory only. Never creates inventory, purchases, costs or customer contacts. */
(function(root){
'use strict';
const M=typeof module!=='undefined'&&module.exports?require('./materials-core.js'):root.EBMaterials;
const copy=x=>JSON.parse(JSON.stringify(x)),text=x=>String(x??'').trim();
const norm=x=>text(x).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es').replace(/\s+/g,' ');
function rows(d){
 if(d.suppliers===undefined)return[];
 if(!Array.isArray(d.suppliers)||d.suppliers.some(r=>!r||typeof r!=='object'||Array.isArray(r)))throw Error('No se pudo leer el registro de proveedores. No se modificó la base.');
 return d.suppliers;
}
function items(value){
 if(!Array.isArray(value))throw Error('Selecciona al menos un insumo.');
 if(value.length>100)throw Error('Un proveedor admite hasta 100 conceptos.');
 const found=new Set();return value.map(x=>{if(typeof x!=='string')throw Error('Revisa el nombre del insumo.');const v=text(x);if(!v||v.length>160)throw Error('El insumo debe tener entre 1 y 160 caracteres.');return v;}).filter(v=>{const k=norm(v);if(found.has(k))return false;found.add(k);return true;});
}
function view(r){return{name:text(r.name||r.company),items:Array.isArray(r.items)?r.items.filter(x=>typeof x==='string'):[],contact:text(r.contact),place:text(r.place||r.location),email:text(r.email),phone:text(r.phone||r.tel),notes:text(r.notes),deleted:!!r.deletedAt};}
function catalog(d){
 const names=[...M.catalog(d),'Mezcal a granel','Embotellado','Material de marketing','Transporte','Seguro','Bodega'];
 rows(d).forEach(r=>{if(!r.deletedAt)names.push(...view(r).items);});
 const seen=new Set();return names.filter(x=>typeof x==='string'&&text(x)&&norm(x)!=='otros').map(text).filter(v=>{const k=norm(v);if(seen.has(k))return false;seen.add(k);return true;});
}
function validate(input){
 if(!input||typeof input!=='object')throw Error('Revisa los datos del proveedor.');
 const v={name:text(input.name),items:items(input.items),contact:text(input.contact),place:text(input.place),email:text(input.email),phone:text(input.phone),notes:text(input.notes)};
 if(!v.name||v.name.length>160)throw Error('Escribe el nombre del proveedor (máximo 160 caracteres).');
 if(!v.items.length)throw Error('Selecciona al menos un insumo que ofrece este proveedor.');
 if(v.items.some(x=>norm(x)==='otros'))throw Error('En Otros escribe el concepto específico.');
 if(v.contact.length>160||v.place.length>240||v.phone.length>60||v.email.length>254||v.notes.length>1000)throw Error('Revisa la longitud de los datos de contacto o notas.');
 if(v.email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.email))throw Error('Revisa el correo electrónico.');
 return v;
}
function change(d,input,opt){
 const o=opt||{},source=rows(d),at=source.findIndex(r=>r.id===o.id),before=at<0?null:source[at],action=o.action||'save';
 if(!o.id||!o.operation||!o.stamp||!Number.isFinite(Date.parse(o.stamp)))throw Error('Falta la referencia del cambio.');
 if(!['save','delete','restore'].includes(action))throw Error('Acción no válida.');
 if(d.supplierHistory!==undefined&&!Array.isArray(d.supplierHistory))throw Error('Historial de proveedores no válido. No se guardó.');
 const request=JSON.stringify({id:o.id,action,input}),prior=(d.supplierHistory||[]).find(h=>h.id===o.operation);
 if(prior){if(prior.request!==request)throw Error('Referencia de guardado duplicada.');return{data:d,record:before,unchanged:true};}
 if(before&&o.expected!==JSON.stringify(before))throw Error('Este proveedor cambió en otro dispositivo. Cierra la captura y vuelve a abrirlo.');
 if(!before&&o.expected!==undefined)throw Error('Este proveedor ya no existe. Actualiza la pantalla.');
 if(!before&&action!=='save')throw Error('Proveedor no encontrado.');
 if(before?.deletedAt&&action==='save')throw Error('Restaura el proveedor desde Papelera antes de editarlo.');
 if(action==='restore'&&!before.deletedAt||action==='delete'&&before.deletedAt)return{data:d,record:before,unchanged:true};
 const value=action==='save'?validate(input):view(before);
 if(action!=='delete'&&source.some((r,i)=>i!==at&&!r.deletedAt&&norm(view(r).name)===norm(value.name)&&norm(view(r).place)===norm(value.place)))throw Error('Este proveedor ya está registrado en esa ubicación. Usa Editar para agregar más insumos.');
 if(before&&action==='save'&&JSON.stringify(validate(view(before)))===JSON.stringify(value))return{data:d,record:before,unchanged:true};
 const after=action==='save'?{...(before||{}),...value}:copy(before);
 after.id=o.id;after.createdAt=before?.createdAt||o.stamp;after.createdBy=before?.createdBy||o.actor||'';after.updatedAt=o.stamp;after.updatedBy=o.actor||'';after.version=(before?.version||0)+1;
 if(action==='delete')after.deletedAt=o.stamp;if(action==='restore')delete after.deletedAt;
 const next=copy(d);next.suppliers=copy(source);if(at<0)next.suppliers.push(after);else next.suppliers[at]=after;
 next.supplierHistory=[...(next.supplierHistory||[]),{id:o.operation,request,at:o.stamp,actor:o.actor||'',supplierId:o.id,action:action==='save'?(before?'update':'create'):action,before:copy(before),after:copy(after)}];
 return{data:next,record:after,unchanged:false};
}
const api={rows,view,catalog,validate,change,norm};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBSupplierCore=api;
})(typeof window==='undefined'?globalThis:window);
