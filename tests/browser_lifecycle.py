"""Hermetic end-to-end admin and guest lifecycle tests; never uses production data."""
from __future__ import annotations
import argparse, importlib.util, json, pathlib, re, tempfile, threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect
ROOT=pathlib.Path(__file__).resolve().parents[1]
PUBLIC='https://bodajulianycarla.bpm.red'
ADMIN='https://wedding-admin.test'

@contextmanager
def environment(browser):
 with tempfile.TemporaryDirectory(prefix='wedding-lifecycle-') as tmp:
  spec=importlib.util.spec_from_file_location('lifecycle_backend',ROOT/'server/app.py')
  app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
  app.DB_PATH=pathlib.Path(tmp)/'qa.sqlite3';app.ADMIN_ROOT=ROOT
  app.ADMIN_USER='qa';app.ADMIN_HASH=app.hash_password('sandbox-test-password-only');app.ADMIN_ENTRY_HASH=''
  app.ALLOWED_ORIGINS={PUBLIC,ADMIN};app.Handler.log_message=lambda *args:None;app.init_db()
  server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
  threading.Thread(target=server.serve_forever,daemon=True).start()
  api='http://127.0.0.1:'+str(server.server_port)
  ctx=browser.new_context(viewport={'width':1280,'height':900})
  html=(ROOT/'index.html').read_text(encoding='utf-8')
  html=re.sub(r'(<meta name="wedding-(?:public-)?api" content=")[^"]*',lambda m:m[1]+ADMIN,html)
  def intercept(route):
   u=urlsplit(route.request.url)
   if u.netloc=='wedding-admin.test':
    route.fulfill(response=route.fetch(url=api+u.path+('?' +u.query if u.query else '')))
   elif u.netloc=='bodajulianycarla.bpm.red':
    if u.path in ('/','/index.html'):
     route.fulfill(status=200,content_type='text/html',body=html)
    else:
     relative=u.path.lstrip('/');path=(ROOT/relative).resolve()
     if ROOT in path.parents and path.is_file() and not relative.startswith(('server/','deploy/','.git')):
      mime={'js':'text/javascript','css':'text/css','html':'text/html','webp':'image/webp'}.get(path.suffix[1:],'text/plain')
      route.fulfill(status=200,content_type=mime,body=path.read_bytes())
     else:route.fulfill(status=404,body='Not found')
   else:route.fulfill(status=200,content_type='text/plain',body='')
  ctx.route('**/*',intercept)
  errors=[];ctx.on('page',lambda page:page.on('pageerror',lambda e:errors.append(str(e))))
  try:yield ctx,app,api,html,errors
  finally:
   ctx.unroute_all(behavior='ignoreErrors')
   ctx.close();server.shutdown();server.server_close()

def enter(ctx):
 page=ctx.new_page();page.goto(PUBLIC+'/',wait_until='domcontentloaded')
 page.locator('#gateCode').fill('BODA');page.locator('#gateForm button[type=submit]').click()
 expect(page.locator('#site')).to_be_visible()
 page.wait_for_function("document.getElementById('configStatus').classList.contains('hidden')")
 return page

def refresh_preserves_typing(env):
 ctx,app,api,html,errors=env;page=enter(ctx)
 page.locator('#fullName').fill('Typing must stay focused')
 with page.expect_response(lambda r:r.url.endswith('/api/public/config')):
  page.evaluate("window.dispatchEvent(new Event('online'))")
 page.wait_for_timeout(100)
 assert page.locator('#fullName').input_value()=='Typing must stay focused'
 assert page.evaluate('document.activeElement.id')=='fullName','Background refresh removed keyboard focus'

def hidden_instagram_stays_hidden(env):
 ctx,app,api,html,errors=env
 with app.db() as c:
  layout=app.read_settings(c)['layout']
  for section in layout['sections']:
   if section['id']=='instagramSection':section['visible']=False
  c.execute("UPDATE settings SET value=? WHERE key='layout'",(json.dumps(layout),))
 delayed=[];ctx.route('**/api/public/instagram',lambda route:delayed.append(route))
 page=enter(ctx)
 page.wait_for_timeout(80);assert delayed
 for route in delayed:route.fulfill(status=200,content_type='application/json',headers={'Access-Control-Allow-Origin':PUBLIC},body=json.dumps({'username':'juli.y.carli','profile_url':'https://www.instagram.com/juli.y.carli/','items':[]}))
 page.wait_for_timeout(100)
 assert not page.locator('#instagramSection').is_visible(),'Late Instagram response ignored the admin visibility setting'

def success_does_not_erase_new_draft(env):
 ctx,app,api,html,errors=env;page=enter(ctx);delayed=[]
 ctx.route('**/api/public/rsvp',lambda route:delayed.append(route))
 page.locator('#fullName').fill('Submitted Person');page.locator('#rsvpSubmit').click()
 page.wait_for_timeout(80);assert delayed
 page.locator('#fullName').fill('New unsent draft')
 route=delayed.pop();route.fulfill(response=route.fetch(url=api+'/api/public/rsvp'))
 expect(page.locator('#rsvpSubmit')).to_be_enabled()
 assert page.locator('#fullName').input_value()=='New unsent draft','Receipt erased edits typed while saving'
 with app.db() as c:assert c.execute('select reported_name from rsvp_submissions').fetchone()[0]=='Submitted Person'

def reconnect_clears_only_saved_form(env):
 ctx,app,api,html,errors=env;page=enter(ctx)
 ctx.route('**/api/public/rsvp',lambda route:route.abort('connectionfailed'))
 page.locator('#fullName').fill('Offline Person');page.locator('#rsvpSubmit').click()
 expect(page.locator('#rsvpSubmit')).to_be_enabled(timeout=10000)
 assert 'pendiente' in page.locator('#rsvpStatus').inner_text()
 ctx.unroute('**/api/public/rsvp')
 page.evaluate("window.dispatchEvent(new Event('online'))")
 page.wait_for_function("document.getElementById('rsvpStatus').classList.contains('ok')")
 assert page.locator('#fullName').input_value()=='','Saved outbox form remained ready to submit a duplicate'
 assert page.evaluate("JSON.parse(localStorage.getItem('boda_rsvp_outbox_v2')).length")==0
 with app.db() as c:assert c.execute('select count(*) from rsvp_submissions').fetchone()[0]==1

def persisted_request_id_reused(env):
 ctx,app,api,html,errors=env;page=enter(ctx)
 original={'request_id':'persisted-before-reload','name':'Persisted Person','phone':'','email':'','attendance':'yes','seats':1,'diet':'','song':'','message':'','submitted_at':'2026-09-27T00:00:00Z'}
 page.evaluate("p=>localStorage.setItem('boda_rsvp_outbox_v2',JSON.stringify([p]))",original)
 page.locator('#fullName').fill(original['name'])
 sent=[]
 def record(route):sent.append(route.request.post_data_json);route.fallback()
 ctx.route('**/api/public/rsvp',record)
 page.locator('#rsvpSubmit').click();expect(page.locator('#rsvpSubmit')).to_be_enabled()
 assert sent and sent[0]['request_id']==original['request_id'],'Retry invented a second submission after page reload'
 assert page.evaluate("JSON.parse(localStorage.getItem('boda_rsvp_outbox_v2')).length")==0

def release_keeps_draft(env):
 ctx,app,api,html,errors=env;page=enter(ctx)
 page.locator('#fullName').fill('Preserved Draft');page.locator('#message').fill('Keep my message');page.locator('#seats').fill('3')
 current=page.locator('meta[name="wedding-release"]').get_attribute('content');next_release=current+'-qa'
 def update(route):
  if urlsplit(route.request.url).path in ('/','/index.html'):route.fulfill(status=200,content_type='text/html',body=html.replace(current,next_release))
  else:route.fallback()
 ctx.route(PUBLIC+'/**',update)
 page.evaluate("window.dispatchEvent(new Event('online'))")
 page.wait_for_url(re.compile(r'.*[?&]_v='+re.escape(next_release)))
 expect(page.locator('#fullName')).to_have_value('Preserved Draft')
 expect(page.locator('#message')).to_have_value('Keep my message')
 expect(page.locator('#seats')).to_have_value('3')

def admin_full_roundtrip(env):
 ctx,app,api,html,errors=env;page=ctx.new_page();page.goto(ADMIN+'/',wait_until='domcontentloaded')
 page.locator('#loginUser').fill('qa');page.locator('#loginPassword').fill('sandbox-test-password-only');page.locator('#loginForm button[type=submit]').click();expect(page.locator('#appView')).to_be_visible()
 for tab in page.locator('#tabs [data-tab]').all():tab.click()
 page.locator('#tabs [data-tab="guests"]').click();page.locator('#addGuestBtn').click()
 page.locator('#gName').fill('Lifecycle Guest');page.locator('#gGroup').fill('QA group');page.locator('#gStatus').select_option('invited');page.locator('#gSeatsAllowed').fill('2')
 page.locator('#guestForm button[type=submit]').click();expect(page.locator('#guestModal')).to_be_hidden()
 with app.db() as c:guest=dict(c.execute("select * from guests where name='Lifecycle Guest'").fetchone());assert guest['group_name']=='QA group'
 # Public response is sent to this sandbox backend, then reconciled through admin controls.
 public=enter(ctx);public.locator('#fullName').fill('Lifecycle Guest');public.locator('#seats').fill('2');public.locator('#rsvpSubmit').click();expect(public.locator('#rsvpSubmit')).to_be_enabled()
 with page.expect_response(lambda res:res.request.method=='GET' and res.url.endswith('/api/admin/state')) as refreshed:
  page.locator('#refreshBtn').click(no_wait_after=True)
 assert refreshed.value.status==200
 page.wait_for_function("document.body.innerText.includes('Lifecycle Guest')")
 with app.db() as c:assert c.execute('select count(*) from rsvp_submissions').fetchone()[0]==1
 with page.expect_response(lambda res:res.request.method=='POST' and '/rsvp-submissions/' in res.url and res.url.endswith('/resolve')) as response:
  page.locator('[data-action="rsvp-match"]').first.click()
 assert response.value.status==200
 with app.db() as c:
  saved=c.execute('select status,attendance,seats,group_name from guests where id=?',(guest['id'],)).fetchone()
  assert tuple(saved)==('confirmed','yes',2,'QA group')
  assert c.execute('select status from rsvp_submissions').fetchone()[0]=='matched'
 for tab,form,fields,table in [
  ('shopping','shoppingForm',{'item':'QA water','needed':'10','bought':'2','unit_cost':'100'},'shopping'),
  ('vendors','vendorForm',{'name':'QA photographer','total':'1000','paid':'200'},'vendors'),
  ('expenses','expenseForm',{'description':'QA expense','actual':'1000','paid':'200'},'expenses'),
  ('tasks','taskForm',{'title':'QA task'},'tasks'),
  ('planner','menuForm',{'item':'QA menu','per_person':'1'},'menu'),
  ('planner','contributionForm',{'contributor':'QA contributor','item':'QA contribution','quantity':'2'},'contributions')]:
  page.locator('#tabs [data-tab="'+tab+'"]').click()
  for name,value in fields.items():page.locator('#'+form+' [name="'+name+'"]').fill(value)
  with page.expect_response(lambda res:res.request.method=='POST' and res.url.endswith('/api/admin/'+table)) as response:page.locator('#'+form+' button[type=submit]').click()
  assert response.value.status==201,(table,response.value.status)
  page.wait_for_timeout(50)
  with app.db() as c:assert c.execute('select count(*) from '+table).fetchone()[0]>=1
 page.locator('#tabs [data-tab="site"]').click();page.locator('[data-copy-key="hero_intro"]').fill('Sandbox updated invitation')
 with page.expect_response(lambda res:res.request.method=='PUT' and res.url.endswith('/api/admin/settings')) as response:page.locator('#saveSettingsBtn').click()
 assert response.value.status==200
 with app.db() as c:assert app.read_settings(c)['copy']['hero_intro']=='Sandbox updated invitation'
 page.locator('#viewCardBtn').click()
 frame=page.frame_locator('#fullCardPreview');expect(frame.locator('#site')).to_be_visible(timeout=15000)
 page.locator('#viewAdminBtn').click();page.locator('#logoutBtn').click();expect(page.locator('#loginView')).to_be_visible()
 page.reload(wait_until='domcontentloaded');expect(page.locator('#loginView')).to_be_visible()
 assert not errors,errors

def responsive_navigation(env):
 ctx,app,api,html,errors=env;page=enter(ctx)
 for width in [320,390,768,1280]:
  page.set_viewport_size({'width':width,'height':844})
  for target in ['#lugares','#dress','#rsvp','#regalos']:
   page.locator(target).scroll_into_view_if_needed()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),('Page overflow',width)
  assert not page.evaluate("Array.from(document.querySelectorAll('[id]')).map(e=>e.id).some((v,i,a)=>a.indexOf(v)!==i)"),'Duplicate IDs'
  assert not page.evaluate("Array.from(document.querySelectorAll('a[href^=\"#\"]')).map(e=>e.getAttribute('href')).some(h=>h.length>1&&!document.getElementById(h.slice(1)))"),'Broken in-page navigation'
 page.locator('label:has(input[name="attendance"][value="no"])').click()
 expect(page.locator('#attendingFields')).to_be_hidden()
 expect(page.locator('#declineMessage')).to_be_visible()
 expect(page.locator('#ticketCard')).to_be_hidden()
 page.locator('#fullName').fill('Declining Guest')
 page.locator('#rsvpSubmit').click();expect(page.locator('#rsvpSubmit')).to_be_enabled()
 with app.db() as c:
  row=c.execute("SELECT attendance,seats FROM rsvp_submissions WHERE reported_name='Declining Guest'").fetchone()
  assert tuple(row)==('no',0)

def main():
 p=argparse.ArgumentParser();p.add_argument('--browser',default='chromium');p.add_argument('--executable');p.add_argument('--output',default='browser-results-lifecycle.json');args=p.parse_args()
 tests=[refresh_preserves_typing,hidden_instagram_stays_hidden,success_does_not_erase_new_draft,reconnect_clears_only_saved_form,persisted_request_id_reused,release_keeps_draft,admin_full_roundtrip,responsive_navigation]
 results=[]
 with sync_playwright() as pw:
  options={'headless':True}
  if args.executable:options['executable_path']=args.executable
  browser=getattr(pw,args.browser).launch(**options)
  for test in tests:
   row={'case':test.__name__,'browser':args.browser}
   try:
    with environment(browser) as env:test(env);assert not env[-1],env[-1]
    row['ok']=True
   except Exception as exc:row.update(ok=False,error=str(exc))
   results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
  browser.close()
 pathlib.Path(args.output).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 raise SystemExit(int(any(not x['ok'] for x in results)))
if __name__=='__main__':main()
