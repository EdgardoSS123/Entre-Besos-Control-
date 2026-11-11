from pathlib import Path
p=Path('suppliers-ui.js');s=p.read_text()
if 'async function persist(result,raw)' not in s:
 assert s.count('function persist(result,raw)')==1
 s=s.replace('function persist(result,raw)','async function persist(result,raw)',1)
s=s.replace('  persist(result,before.raw);locallySaved=true;','  await persist(result,before.raw);locallySaved=true;')
s=s.replace('});persist(result,before.raw);window.EBShared.cancelDraft();','});await persist(result,before.raw);window.EBShared.cancelDraft();')
p.write_text(s)
print('Supplier create/update/delete await quota-safe persistence. No records modified.')
