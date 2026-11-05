/* Display-only conversions. A case contains 6 bottles, a pallet 80 cases. */
(function(root){
  'use strict';
  const CASE=6,PALLET=480,number=n=>new Intl.NumberFormat('es-MX').format(n);
  function parts(n){
    if(!Number.isSafeInteger(n))throw Error('La cantidad de botellas debe ser un entero seguro.');
    const a=Math.abs(n);return{bottles:n,sign:n<0?-1:1,pallets:Math.floor(a/PALLET),cases:Math.floor((a%PALLET)/CASE),loose:a%CASE,totalCases:Math.floor(a/CASE)};
  }
  function describe(n,compact=false){const p=parts(n),s=number(p.pallets)+' '+(p.pallets===1?'pallet':'pallets')+' + '+number(p.cases)+' '+(p.cases===1?'caja':'cajas')+' + '+number(p.loose)+(compact?' sueltas':' '+(p.loose===1?'botella suelta':'botellas sueltas'));return p.sign<0?'−('+s+')':s;}
  function cases(n){const p=parts(n),s=number(p.totalCases)+' '+(p.totalCases===1?'caja':'cajas')+' + '+number(p.loose)+' '+(p.loose===1?'botella suelta':'botellas sueltas');return p.sign<0?'−('+s+')':s;}
  const api={parts,describe,cases,CASE,PALLET};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EBPackages=api;
})(typeof window==='undefined'?globalThis:window);
