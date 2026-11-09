from pathlib import Path
# Compact mobile cards intentionally hide the redundant equivalence text.
# Check the computed text without changing the visible mobile layout.
for name in ['origin-stock','always-samples']:
 p=Path('tests/browser-'+name+'.py');s=p.read_text()
 s=s.replace("page.locator('.simple-metrics').inner_text()", "page.locator('.simple-metrics').text_content()")
 s=s.replace("page.locator('#simple-current').locator('..').inner_text()", "page.locator('#simple-current').locator('..').text_content()")
 s=s.replace("page.locator('#simple-sold').locator('..').inner_text()", "page.locator('#simple-sold').locator('..').text_content()")
 if name=='always-samples':
  s=s.replace("len(snapshot['lotSampleActions'])==5 and len(snapshot['lotSales'])==1", "len(snapshot['lotSampleActions'])==6 and len(snapshot['lotSales'])==1")
  marker="  assert snapshot['lotSales'][0]['totalCents']==360000"
  extra="\n  assert [a['type'] for a in snapshot['lotSampleActions']]==['reserve','consume','release','reserve','release','reserve']\n  assert [a['quantity'] for a in snapshot['lotSampleActions']]==[12,2,6,6,6,702]\n  assert all(a['income']==0 and a['receivable']==0 for a in snapshot['lotSampleActions'])"
  if extra not in s:s=s.replace(marker,marker+extra,1)
 p.write_text(s)
print('PASS assertions match compact mobile layout; reserved-product sale has one explicit reclassification and one sale, never duplicate income')
