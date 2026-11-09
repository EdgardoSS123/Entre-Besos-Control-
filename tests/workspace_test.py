"""Real authenticated SQLite workspace for browser regressions; localhost only.

The fixture database and credentials are disposable. No production URL, cookie,
account, or business record is read or written. The application's auth and
optimistic-concurrency checks remain enabled throughout every test.
"""
import atexit
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from urllib.parse import urlparse

EMPTY = dict(lots=[], moves=[], contacts=[], materials=[], supplies=[], expenses=[], documents=[], costs={})

class Workspace:
    def __init__(self, initialized=True):
        self.initialized=initialized
        self.root = Path(__file__).resolve().parents[1]
        self.temp = tempfile.TemporaryDirectory(prefix='eb-authenticated-regression-')
        self.public = Path(self.temp.name)/'public'
        self.public.mkdir()
        for source in self.root.iterdir():
            if source.is_file() and source.suffix in ['.js','.css','.html','.jpg','.png','.webmanifest']:
                shutil.copyfile(source, self.public/source.name)
        shutil.copyfile(self.root/'control.html', self.public/'index.html')
        shutil.copyfile(self.root/'index.html', self.public/'legacy.html')
        for folder in ['vendor','icons']:
            if (self.root/folder).exists(): shutil.copytree(self.root/folder, self.public/folder)
        script = r"""
const crypto=require('node:crypto');
const {createApp}=require('./server.cjs');
const salt='42'.repeat(16),password='isolated-browser-fixture-only';
const hash=crypto.scryptSync(password,Buffer.from(salt,'hex'),64,{N:32768,r:8,p:1,maxmem:67108864}).toString('hex');
const origins=[];
const app=createApp({folder:process.env.EB_TEST_DATA,root:process.env.EB_TEST_PUBLIC,users:[{username:'test-editor',role:'editor',salt,hash}],origins,secure:false});
if(process.env.EB_TEST_INITIALIZED==='1')app.db.prepare('UPDATE workspace SET revision=1,payload=?,updated=?,actor=? WHERE id=1').run(process.env.EB_TEST_EMPTY,new Date().toISOString(),'isolated-fixture');
app.server.listen(0,'127.0.0.1',()=>{const url='http://127.0.0.1:'+app.server.address().port;origins.push(url);console.log(url);});
process.on('SIGTERM',()=>app.server.close(()=>{app.db.close();process.exit(0);}));
"""
        self.server = subprocess.Popen(['node','--experimental-sqlite','-e',script],cwd=self.root,stdout=subprocess.PIPE,text=True,env={**os.environ,'EB_TEST_DATA':str(Path(self.temp.name)/'data'),'EB_TEST_PUBLIC':str(self.public),'EB_TEST_INITIALIZED':'1' if initialized else '0','EB_TEST_EMPTY':json.dumps(EMPTY)})
        self.base = self.server.stdout.readline().strip()+'/'
        if not self.base.startswith('http://127.0.0.1:'):
            self.close()
            raise RuntimeError('Isolated authenticated server did not start')
        atexit.register(self.close)

    def context(self, browser, **kwargs):
        ctx = browser.new_context(**kwargs)
        response = ctx.request.post(self.base+'api/login',data={'username':'test-editor','password':'isolated-browser-fixture-only'},headers={'Origin':self.base[:-1]})
        assert response.ok, response.text()
        if self.initialized:self.seed(ctx, EMPTY)
        return ctx

    def seed(self, ctx, data):
        session=ctx.request.get(self.base+'api/session').json()
        current=ctx.request.get(self.base+'api/state').json()
        result=ctx.request.put(self.base+'api/state',data={'data':data,'revision':current['revision'],'operation':str(uuid.uuid4())},headers={'Origin':self.base[:-1],'X-EB-CSRF':session['csrf']})
        assert result.ok,result.text()

    def ready(self, page):
        page.wait_for_function("()=>window.EBShared && document.querySelector('#eb-cloud-state')?.textContent.startsWith('Actualizado') && !window.EBShared.pending",timeout=20000)

    def flush(self, page):
        if page.url.startswith(self.base) and page.evaluate('!!window.EBShared'):
            self.ready(page)

    def goto(self, page, url, **kwargs):
        assert url.startswith(self.base), 'Tests may navigate only their disposable local workspace'
        self.flush(page)
        response=page.goto(url,**kwargs)
        if urlparse(url).path not in ['/instalar.html']:
            self.ready(page)
        return response

    def reload(self, page, **kwargs):
        self.flush(page)
        response=page.reload(**kwargs)
        if urlparse(page.url).path not in ['/instalar.html']:
            self.ready(page)
        return response

    def close(self):
        if getattr(self,'server',None) and self.server.poll() is None:
            self.server.terminate()
            try:self.server.wait(timeout=5)
            except subprocess.TimeoutExpired:self.server.kill();self.server.wait()
        if getattr(self,'temp',None):self.temp.cleanup()
