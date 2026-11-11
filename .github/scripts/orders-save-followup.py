from pathlib import Path
p=Path('orders-ui.js');s=p.read_text()
old='window.EBOrdersUI={render,get dirty(){return dirty;}};'
new='window.EBOrdersUI={render,get dirty(){return dirty;},get saving(){return busy;}};'
if new not in s:
    assert s.count(old)==1
    p.write_text(s.replace(old,new,1))
# A preflight GET now precedes the write. Waiting only for an empty shared
# outbox can return before the action begins, so also wait for the action.
# Preserve all existing balance, recipient, permission and privacy assertions.
for name in ['orders','orders-customer','orders-save','audit','save-return']:
    p=Path('tests/browser-'+name+'.py');s=p.read_text()
    for old in ['window.EBShared&&!window.EBShared.pending','window.EBShared&&!EBShared.pending']:
        new=old+'&&!window.EBOrdersUI?.saving'
        if new not in s:s=s.replace(old,new)
    p.write_text(s)
print('Waiting for the complete order action, including preparation, write and cloud acknowledgement; all substantive assertions retained.')
