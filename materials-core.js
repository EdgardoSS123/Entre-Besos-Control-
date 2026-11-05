/* Separate, manual inventories. Reading never creates stock or changes lot costs. */
(function (root) {
  'use strict';
  const DEFAULTS = ['Botellas vacías','Tapones','Etiquetas','Marbetes','Precintos','Marbetes y precintos','Hologramas CRM','Cintillos','Corrugados','Pallets'];
  const key = kind => { if (kind === 'marketing') return 'materials'; if (kind === 'supplies') return 'supplies'; throw Error('Inventario no reconocido.'); };
  const copy = value => JSON.parse(JSON.stringify(value));
  function records(data, kind) {
    const value = data[key(kind)];
    if (value === undefined) return [];
    if (!Array.isArray(value) || value.some(x => !x || typeof x !== 'object' || Array.isArray(x))) throw Error('No se pudo leer este inventario. No se modificaron los datos.');
    return value;
  }
  function amount(value, label) {
    if (value === '' || value === null || value === undefined || typeof value === 'boolean' || !['string','number'].includes(typeof value) || (typeof value === 'string' && !value.trim())) throw Error('Captura '+label+'.');
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0 || n > 1e12) throw Error('Revisa '+label+': debe ser un número no negativo.');
    return n;
  }
  function cost(record) {
    if (record.totalCost === undefined || record.totalCost === null || record.totalCost === '') return null;
    const n = Number(record.totalCost);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }
  function catalog(data) {
    const names = [...DEFAULTS];
    if (Array.isArray(data.supplyCatalog)) data.supplyCatalog.forEach(x => names.push(typeof x === 'string' ? x : x?.name));
    records(data, 'supplies').forEach(x => names.push(x.name));
    (Array.isArray(data.lots) ? data.lots : []).forEach(lot => (Array.isArray(lot.materialsPlan) ? lot.materialsPlan : []).forEach(x => names.push(x.name)));
    const seen = new Set();
    return names.filter(x => typeof x === 'string' && x.trim()).map(x => x.trim()).filter(x => { const id=x.toLocaleLowerCase('es'); if(seen.has(id))return false; seen.add(id); return true; });
  }
  function validate(input, kind, data) {
    const name = String(input.name ?? '').trim(), loc = String(input.loc ?? '').trim(), presentation = String(input.presentation ?? '').trim();
    if (!name || name.length > 160) throw Error('Escribe un concepto de hasta 160 caracteres.');
    if (!loc || loc.length > 160) throw Error('Selecciona la bodega.');
    if (presentation.length > 120) throw Error('La presentación no debe exceder 120 caracteres.');
    if (kind === 'supplies' && !input.custom && !catalog(data).includes(name)) throw Error('Selecciona un insumo del catálogo o usa + Otro insumo.');
    const qty = amount(input.qty, 'la cantidad'), totalCost = amount(input.totalCost, 'el costo total');
    if (!Number.isSafeInteger(qty)) throw Error('La cantidad debe ser un número entero de unidades.');
    if (Math.abs(totalCost*100 - Math.round(totalCost*100)) > .0001) throw Error('El costo total admite hasta dos decimales.');
    if (qty === 0 && totalCost !== 0) throw Error('Con cero existencias, el costo de esas existencias debe ser cero.');
    return {name,loc,presentation,qty,totalCost:Math.round(totalCost*100)/100,currency:'MXN',unit:String(input.unit || 'unidades').slice(0,30)};
  }
  function change(data, kind, input, options) {
    const rows = records(data, kind), opts = options || {}, index = opts.index;
    if (!opts.id || !opts.stamp) throw Error('Falta la referencia del cambio.');
    const editing = index !== undefined && index !== null;
    if (editing && (!Number.isInteger(index) || index < 0 || index >= rows.length || JSON.stringify(rows[index]) !== opts.expected)) throw Error('El registro cambió en otra pestaña. Vuelve a abrirlo antes de guardar.');
    const before = editing ? rows[index] : null;
    if (opts.remove && !editing) throw Error('Selecciona el registro que deseas eliminar.');
    const after = opts.remove ? null : {...(before || {}),...validate(input,kind,data),id:before?.id || opts.id,createdAt:before?.createdAt || opts.stamp,updatedAt:opts.stamp};
    const normalize = s => String(s || '').trim().toLocaleLowerCase('es');
    if (after && rows.some((r,i) => i !== index && normalize(r.name) === normalize(after.name) && normalize(r.loc) === normalize(after.loc) && normalize(r.presentation) === normalize(after.presentation))) throw Error('Este concepto ya está registrado en esa bodega y presentación. Usa Editar para corregir su cantidad y costo.');
    const result = copy(data), field = key(kind);
    result[field] = copy(rows);
    if (opts.remove) result[field].splice(index,1);
    else if (editing) result[field][index] = after;
    else result[field].push(after);
    if (result.materialInventoryHistory !== undefined && !Array.isArray(result.materialInventoryHistory)) throw Error('El historial no tiene un formato válido. No se guardó el cambio.');
    result.materialInventoryHistory = [...(result.materialInventoryHistory || []),{id:opts.id,kind,action:opts.remove?'delete':editing?'update':'create',at:opts.stamp,before:copy(before),after:copy(after)}];
    return result;
  }
  const api = {records,catalog,cost,change,validate,defaults:DEFAULTS.slice()};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  else root.EBMaterials=api;
})(typeof window === 'undefined' ? globalThis : window);
