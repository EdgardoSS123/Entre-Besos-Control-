'use strict';
/* Deliberate server projection: EB2 receives presentation data only, never workspace records. */
const path=require('node:path');
function buildPartnerReport(data,root,options={}){
 let I=require(path.join(root,'inventory-core.js'));
 for(const module of ['commerce-core.js','simple-core.js','corrections-core.js'])I=require(path.join(root,module))(I);
 const full=require(path.join(root,'executive-core.js')).build(data,I,options);
 const allowed=new Set(['Ventas','Lo que tenemos y lo que ha costado','Dónde está el producto','Cada lote: producción, salidas y saldo','Salidas por pedidos','Diferencias que requieren revisión','Producto en tránsito','Material de marketing · existencias y costo','Insumos · existencias y costo','Total registrado · material de marketing','Total registrado · insumos','Ventas antiguas sin vínculo a lote','Total de gastos por moneda','Fletes y costos de movimientos','Directorio y documentación']);
 const sections=full.sections.filter(s=>allowed.has(s.title)).map(s=>({title:s.title,head:s.head,body:s.body,right:s.right||[],...(s.note?{note:s.note}:{}),...(s.empty?{empty:s.empty}:{})}));
 return{title:full.title,subtitle:full.subtitle,file:full.file,scope:full.scope,metrics:full.metrics,sections,notes:full.notes};
}
module.exports={buildPartnerReport};
