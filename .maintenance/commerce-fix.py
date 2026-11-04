from pathlib import Path
p=Path('tests/browser-commerce.py');s=p.read_text();s=s.replace("assert 'Pago parcial' in page.locator('.sale-record').first.inner_text()", "assert 'pago parcial' in page.locator('.sale-record').first.inner_text().lower()\n  assert page.evaluate(\"EBLedger.saleStatus(JSON.parse(localStorage.getItem('eb-v1')).lotSales[0],new Date().toISOString().slice(0,10)).status\")==\"Pago parcial\"")
s=s.replace("assert 'Pagada' in page.locator('.sale-record').first.inner_text()", "assert 'pagada' in page.locator('.sale-record').first.inner_text().lower()\n  assert page.evaluate(\"EBLedger.saleStatus(JSON.parse(localStorage.getItem('eb-v1')).lotSales[0],new Date().toISOString().slice(0,10)).status\")==\"Pagada\"")
p.write_text(s)
