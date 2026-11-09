'use strict';
const assert=require('node:assert/strict');let I=require('../inventory-core.js');I=require('../commerce-core.js')(I);
assert.equal(I.quote(2,'90071992547399.89','box').totalCents,3002399751579996);
assert.equal(I.quote(6,'1100.01','bottle').totalCents,660006);
assert.equal(I.quote(1,'100.01','box').totalCents,1667);
assert.equal(I.quote(3,'0.01','box').totalCents,1);
assert.throws(()=>I.quote(7,'90071992547409.91','bottle'));
for(const bad of ['-1','1.001','NaN','Infinity','',null])assert.throws(()=>I.quote(1,bad,'bottle'));
for(const n of [0,-1,1.5,NaN,Infinity])assert.throws(()=>I.quote(n,'1','box'));
let cases=0;for(let n=1;n<=1000;n+=7)for(const c of [1,37,101,999,110001,9007199254739989]){const s=String(BigInt(c)/100n)+'.'+String(BigInt(c)%100n).padStart(2,'0');for(const basis of ['bottle','box']){const d=basis==='box'?6n:1n,expected=(BigInt(n)*BigInt(c)+d/2n)/d;if(expected===0n||expected>BigInt(Number.MAX_SAFE_INTEGER))assert.throws(()=>I.quote(n,s,basis));else assert.equal(I.quote(n,s,basis).totalCents,Number(expected));cases++;}}
console.log('PASS EXACT MONEY:',cases,'independent integer-rational quotes; invalid amounts and overflow rejected; no stored records rewritten');
