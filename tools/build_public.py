"""Build the public Pages artifact from an explicit allowlist and validate versions."""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, re, shutil, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
PUBLIC=['index.html','actualizar.html','404.html','robots.txt','CNAME','assets/app.js','assets/updates.js','assets/styles.css','assets/botanical-frame.webp','assets/botanical-vine.webp','js/public-pista.js']
def build(destination:pathlib.Path)->dict:
 html=(ROOT/'index.html').read_text(encoding='utf-8')
 release=re.search(r'<meta name="wedding-release" content="([^"]+)"',html).group(1)
 assert (ROOT/'CNAME').read_text().strip()=='bodajulianycarla.bpm.red','Canonical domain must include y'
 for path in ['assets/app.js','assets/updates.js','assets/styles.css']:
  assert path+'?v='+release in html,('Unversioned asset',path)
 assert '_v='+release in (ROOT/'actualizar.html').read_text(encoding='utf-8'),'Recovery version mismatch'
 assert 'const ACCESS_CODE = "BODA"' in (ROOT/'assets/app.js').read_text(encoding='utf-8')
 destination=destination.resolve()
 assert destination != ROOT and destination.name == '_site','Output must be a dedicated _site directory'
 destination.mkdir(parents=True,exist_ok=True)
 hashes={}
 for name in PUBLIC:
  source=ROOT/name;target=destination/name
  target.parent.mkdir(parents=True,exist_ok=True)
  data=source.read_bytes()
  if source.suffix not in ('.webp','.png','.jpg'):data=data.replace(b'\r\n',b'\n')
  target.write_bytes(data);hashes[name]=hashlib.sha256(data).hexdigest()
 (destination/'.nojekyll').write_text('')
 sha=os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 manifest={'release':release,'source_sha':sha,'sha256':hashes}
 (destination/'release.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='utf-8')
 expected=set(PUBLIC)|{'.nojekyll','release.json'}
 actual={str(p.relative_to(destination)).replace('\\','/') for p in destination.rglob('*') if p.is_file()}
 assert actual==expected,('Unexpected public files',sorted(actual-expected))
 return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',default='_site');a=p.parse_args()
 result=build(pathlib.Path(a.output));print(json.dumps({'release':result['release'],'source_sha':result['source_sha'],'files':len(result['sha256'])}))
