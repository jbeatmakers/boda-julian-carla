"""Real-browser access/RSVP regression suite. Production mode is read-only."""
from __future__ import annotations
import argparse, contextlib, importlib.util, json, os, pathlib, re, sqlite3, tempfile, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--browser',choices=['chromium','firefox','webkit'],default='chromium')
 parser.add_argument('--executable')
 parser.add_argument('--base',help='Published URL. Only non-mutating cases are run.')
 parser.add_argument('--output',default='browser-results.json')
 args=parser.parse_args()
 services=[];report=[]
 with tempfile.TemporaryDirectory(prefix='wedding-browser-') as tmp:
  if args.base:
   base=args.base.rstrip('/')
   database=None
  else:
   spec=importlib.util.spec_from_file_location('browser_wedding',ROOT/'server/app.py')
   app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
   app.DB_PATH=pathlib.Path(tmp)/'wedding.sqlite3';app.ADMIN_ROOT=ROOT
   app.Handler.log_message=lambda *a:None
   app.init_db()
   with app.db() as c:
    conf=app.read_settings(c)['celebration'];conf['time']='19:00'
    c.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(conf),'celebration'))
   backend=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
   api='http://127.0.0.1:'+str(backend.server_port)
   class Public(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
    def log_message(self,*a):pass
    def do_GET(self):
     if self.path.split('?')[0] in ('/','/index.html'):
      html=(ROOT/'index.html').read_text(encoding='utf-8')
      html=re.sub(r'(<meta name="wedding-(?:public-)?api" content=")[^"]*',lambda m:m[1]+api,html)
      body=html.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
     else:super().do_GET()
   public=ThreadingHTTPServer(('127.0.0.1',0),Public)
   base='http://127.0.0.1:'+str(public.server_port)
   app.ALLOWED_ORIGINS={base,"https://bodajulianycarla.bpm.red"}
   services=[backend,public]
   for service in services:threading.Thread(target=service.serve_forever,daemon=True).start()
   database=app.DB_PATH
  with sync_playwright() as pw:
   options={'headless':True}
   if args.executable:options['executable_path']=args.executable
   browser=getattr(pw,args.browser).launch(**options)
   def run(label,code='BODA',deny_storage=False,block_config=False,rsvp=None,mobile=False):
    opts={'viewport':{'width':390,'height':844} if mobile else {'width':1280,'height':900}}
    if mobile and args.browser!='firefox':opts.update(is_mobile=True,has_touch=True)
    ctx=browser.new_context(**opts)
    try:
     if deny_storage:ctx.add_init_script("for(const key of ['sessionStorage','localStorage']) Object.defineProperty(window,key,{get(){throw new DOMException('denied','SecurityError')}})")
     if not args.base:
      ctx.route(re.compile(r'https://[^/]+/api/'),lambda route:route.abort('blockedbyclient'))
      ctx.route('https://fonts.googleapis.com/**',lambda route:route.abort())
      ctx.route('https://www.google.com/maps**',lambda route:route.abort())
     if block_config:ctx.route('**/api/public/config',lambda route:route.abort('connectionfailed'))
     page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
     page.goto(base+'/',wait_until='domcontentloaded',timeout=30000)
     page.locator('#gateCode').fill(code)
     t=time.monotonic();page.locator('#gateForm button[type=submit]').click()
     if code=='18dic':
      assert page.locator('#site').evaluate("e=>e.classList.contains('hidden')")
      assert 'no coincide' in page.locator('#gateError').inner_text()
     else:
      page.wait_for_function("!document.getElementById('site').classList.contains('hidden')",timeout=1500)
      opened=time.monotonic()-t
      assert opened<3.0,('gate blocked',opened)
      if block_config:
       page.wait_for_function("!document.getElementById('configRetryInline').classList.contains('hidden')",timeout=8000)
       assert not page.locator('#ticketCard').is_visible(),'Never present a default or stale price'
       assert 'Actualizando' in page.locator('#celebrationTime').inner_text()
       ctx.unroute('**/api/public/config')
       page.locator('#configRetryInline').click()
      page.wait_for_function("document.getElementById('configStatus').classList.contains('hidden')",timeout=20000)
      assert page.locator('#ticketPrice').inner_text().strip()
      if rsvp:
       hits=[]
       if rsvp=='network':
        def fail(route):hits.append(1);route.abort('connectionfailed')
        ctx.route('**/api/public/rsvp',fail)
       elif rsvp=='invalid_receipt':
        ctx.route('**/api/public/rsvp',lambda route:route.fulfill(status=200,content_type='application/json',body='{}'))
       elif rsvp=='rejected':
        def reject(route):hits.append(1);route.fulfill(status=400,content_type='application/json',body='{"error":"invalid_email"}')
        ctx.route('**/api/public/rsvp',reject)
       page.locator('#fullName').fill('Browser QA '+label)
       page.locator('#seats').fill('2')
       page.locator('#rsvpSubmit').click()
       page.wait_for_function("!document.getElementById('rsvpSubmit').disabled",timeout=10000)
       text=page.locator('#rsvpStatus').inner_text()
       if rsvp=='network':
        assert 'no permite guardar' in text,text
        assert page.locator('#fullName').input_value()=='Browser QA '+label
        ctx.unroute('**/api/public/rsvp')
        page.evaluate("window.dispatchEvent(new Event('online'))")
        page.wait_for_function("document.getElementById('rsvpStatus').classList.contains('ok')",timeout=10000)
        assert 'servidor guardó' in page.locator('#rsvpStatus').inner_text()
       elif rsvp=='invalid_receipt':
        assert 'Todavía no recibimos' in text,text
        assert not page.locator('#rsvpStatus').evaluate("e=>e.classList.contains('ok')")
       elif rsvp=='rejected':
        assert len(hits)==1,'Do not retry validation errors'
        assert 'no aceptó' in text,text
       elif rsvp=='real':
        assert 'Quedó confirmada' in text,text
       if rsvp in ('network','real'):
        with contextlib.closing(sqlite3.connect(database)) as c:count=c.execute('SELECT COUNT(*) FROM rsvp_submissions WHERE reported_name=?',('Browser QA '+label,)).fetchone()[0]
        assert count==1,('database receipt count',count)
     assert not errors,errors
     row={'case':label,'browser':args.browser,'ok':True,'url':base,'release':page.locator('meta[name="wedding-release"]').get_attribute('content')}
     report.append(row);print(json.dumps(row),flush=True)
    finally:ctx.close()
   def recovery_case():
    ctx=browser.new_context()
    try:
     page=ctx.new_page()
     if args.base:
      page.goto(base+'/actualizar.html#rsvp',wait_until='domcontentloaded',timeout=30000)
      page.wait_for_url(re.compile(r'.*[?&]_v=.*#rsvp$'),timeout=15000)
     else:
      used=[False]
      def local_canonical(route):
       url=urlsplit(route.request.url)
       if url.path=='/' and not url.query and not used[0]:
        used[0]=True
        route.fulfill(status=200,content_type='text/html',body='<!doctype html><html><body><div id="lockScreen">Demo retirada</div><script src="/js/public-pista.js" defer></script></body></html>')
       else:
        target=base+url.path+('?' +url.query if url.query else '')
        route.fulfill(response=route.fetch(url=target))
      ctx.route(re.compile(r'^https://bodajulianycarla\.bpm\.red/'),local_canonical)
      page.goto('https://bodajulianycarla.bpm.red/#rsvp',wait_until='domcontentloaded',timeout=30000)
      page.wait_for_url(re.compile(r'.*[?&]_v=.*#rsvp$'),timeout=15000)
      assert used[0],'Legacy HTML fixture was not exercised'
     page.locator('#gateCode').fill('BODA')
     page.locator('#gateForm button[type=submit]').click()
     page.wait_for_function("!document.getElementById('site').classList.contains('hidden')",timeout=1500)
     row={'case':'recovery-link' if args.base else 'cached-demo-shell-recovers','browser':args.browser,'ok':True,'url':page.url,'release':page.locator('meta[name="wedding-release"]').get_attribute('content')}
     report.append(row);print(json.dumps(row),flush=True)
    finally:ctx.close()
   try:
    run('normal')
    run('lowercase','boda',mobile=True)
    run('pasted-spaces',' \u200b bO dA \u00a0',mobile=True)
    run('retired-code-rejected','18dic')
    run('storage-denied',deny_storage=True,mobile=True)
    run('api-failure-and-recovery',block_config=True)
    run('mobile-api-and-storage-failure',deny_storage=True,block_config=True,mobile=True)
    recovery_case()
    if not args.base:
     run('real-rsvp',rsvp='real',mobile=True)
     run('unsaved-rsvp-reconnect',deny_storage=True,rsvp='network')
     run('invalid-receipt-is-not-success',rsvp='invalid_receipt')
     run('validation-error-no-retry',rsvp='rejected')
   finally:
    browser.close()
    for service in services:service.shutdown();service.server_close()
    pathlib.Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  print('BROWSER_PASS',len(report),args.browser,flush=True)
if __name__=='__main__':main()
