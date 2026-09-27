"""Verify the published bytes and live backend; no RSVP writes or private data."""
from __future__ import annotations
import argparse,hashlib,json,os,pathlib,re,subprocess,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='https://bodajulianycarla.bpm.red'
def fetch(path):
 req=urllib.request.Request(path,headers={'Cache-Control':'no-cache','Origin':BASE})
 with urllib.request.urlopen(req,timeout=20) as r:return r.status,dict(r.headers),r.read()
def main():
 p=argparse.ArgumentParser();p.add_argument('--backend-only',action='store_true');p.add_argument('--wait',type=int,default=0);args=p.parse_args()
 html=(ROOT/'index.html').read_text(encoding='utf-8')
 api=re.search(r'<meta name="wedding-public-api" content="([^"]+)"',html) or re.search(r'<meta name="wedding-api" content="([^"]+)"',html)
 api=api.group(1).rstrip('/')
 _,_,data=fetch(api+'/healthz');health=json.loads(data)
 assert health.get('ok') and health.get('database')=='ready',('Unhealthy backend',health)
 expected=hashlib.sha256((ROOT/'server/app.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
 assert health.get('code_sha256')==expected,'Production backend differs from the tested source; deploy backend first'
 _,headers,data=fetch(api+'/api/public/config');config=json.loads(data)
 headers={k.lower():v for k,v in headers.items()}
 assert headers.get('access-control-allow-origin')==BASE,'Canonical CORS missing'
 assert isinstance(config.get('ticket',{}).get('enabled'),bool)
 assert isinstance(config.get('copy'),dict)
 print(json.dumps({'backend':'PASS','database':'ready','cors':'PASS','code_sha256':expected}),flush=True)
 if args.backend_only:return
 expected_source=os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 release=re.search(r'<meta name="wedding-release" content="([^"]+)"',html).group(1)
 deadline=time.monotonic()+args.wait
 while True:
  try:
   _,_,body=fetch(BASE+'/release.json?_check='+str(time.time_ns()))
   manifest=json.loads(body)
   assert manifest['source_sha']==expected_source,('Pending deployment',manifest['source_sha'],expected_source)
   assert manifest['release']==release
   break
  except Exception:
   if time.monotonic()>=deadline:raise
   time.sleep(5)
 for path,digest in manifest['sha256'].items():
  assert not path.startswith('/') and '..' not in path.split('/')
  _,_,body=fetch(BASE+'/'+path+'?_check='+str(time.time_ns()))
  assert hashlib.sha256(body).hexdigest()==digest,('Published bytes mismatch',path)
  expected_bytes=(ROOT/path).read_bytes()
  if pathlib.Path(path).suffix!='.webp':expected_bytes=expected_bytes.replace(b'\r\n',b'\n')
  assert hashlib.sha256(expected_bytes).hexdigest()==digest,('Artifact differs from tested source',path)
 print(json.dumps({'public':'PASS','canonical':BASE,'release':release,'source_sha':expected_source,'verified_files':len(manifest['sha256'])}),flush=True)
if __name__=='__main__':main()
