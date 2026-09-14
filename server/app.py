#!/usr/bin/env python3
"""Small persistent wedding backend: stdlib + SQLite, no runtime dependency on GitHub."""
from __future__ import annotations
import argparse, base64, getpass, hashlib, hmac, json, os, re, secrets, sqlite3, threading, time, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DB_PATH = Path(os.environ.get("WEDDING_DB_PATH", "/var/lib/boda-julian-carla/wedding.sqlite3"))
ADMIN_USER = os.environ.get("WEDDING_ADMIN_USER", "admin")
ADMIN_HASH = os.environ.get("WEDDING_ADMIN_PASSWORD_HASH", "")
HOST = os.environ.get("WEDDING_HOST", "127.0.0.1")
PORT = int(os.environ.get("WEDDING_PORT", "8787"))
ALLOWED_ORIGINS = {x.strip().rstrip("/") for x in os.environ.get(
    "WEDDING_ALLOWED_ORIGINS",
    "https://boda-julian-carla.bpm.red"
).split(",") if x.strip()}
SESSION_TTL = 8 * 3600
MAX_BODY = 16_384
_lock = threading.RLock()
_sessions: dict[str, dict] = {}
_rate: dict[str, list[float]] = {}

DEFAULT_SETTINGS = {
    "event_at":"2026-12-18T17:00:00-03:00",
    "location_display":"San Pablo de Reyes · Jujuy",
    "rsvp_deadline_display":"1 de diciembre",
    "ceremony":{"time":"17:00","title":"Santa Misa de Casamiento","place":"Iglesia San Pedro y San Pablo","address":"Carlos Figueroa · San Pablo de Reyes · Jujuy","lat":-24.14581,"lng":-65.39445},
    "celebration":{"time":"18:30","title":"Recepción, cena & fiesta","place":"Quincho · San Pablo de Reyes","address":"A unos 300 metros de la ceremonia.","lat":-24.14816,"lng":-65.39326},
    "dress":{"title":"Estética Edén","concept":"Una gala fresca, sofisticada y luminosa, inspirada en la naturaleza al atardecer.","details":"Formal elegante. No hace falta comprar de nuevo: un buen accesorio puede terminar de llevar el conjunto al tono de la noche."},
    "ticket":{"enabled":True,"price":35000,"currency":"ARS","text":"Ese es el valor por persona para la cena y la fiesta. Si en tu invitación acordamos otra cosa, naturalmente vale eso."},
    "bank":{"holder":"","alias":"","cbu":"","mp_url":""},
    "fallback_whatsapp":""
}
TABLE_FIELDS = {
    "expenses":{"category","description","vendor","budget","actual","paid","due_date","status","notes"},
    "shopping":{"category","item","unit","needed","bought","unit_cost","done","notes"},
    "tasks":{"title","category","due_date","priority","owner","status","notes"},
    "vendors":{"category","name","contact","total","paid","due_date","status","notes"},
    "songs":{"title","source","active"}
}
GUEST_FIELDS = {
    "name","phone","email","status","attendance","seats","diet","song","notes",
    "ticket_override","ticket_exempt","ticket_paid","gift_amount","gift_note","table_no"
}

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=8)
    try:
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=5000")
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def init_db() -> None:
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS settings(
          key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS guests(
          id TEXT PRIMARY KEY, request_id TEXT UNIQUE, name TEXT NOT NULL,
          phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'pending', attendance TEXT NOT NULL DEFAULT '',
          seats INTEGER NOT NULL DEFAULT 1, diet TEXT NOT NULL DEFAULT '',
          song TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
          ticket_override INTEGER, ticket_exempt INTEGER NOT NULL DEFAULT 0,
          ticket_paid INTEGER NOT NULL DEFAULT 0, gift_amount INTEGER NOT NULL DEFAULT 0,
          gift_note TEXT NOT NULL DEFAULT '', table_no TEXT NOT NULL DEFAULT '',
          invited_at TEXT NOT NULL, responded_at TEXT, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_guests_phone ON guests(phone);
        CREATE INDEX IF NOT EXISTS idx_guests_email ON guests(email);
        CREATE TABLE IF NOT EXISTS expenses(
          id TEXT PRIMARY KEY, category TEXT DEFAULT '', description TEXT NOT NULL,
          vendor TEXT DEFAULT '', budget REAL NOT NULL DEFAULT 0, actual REAL NOT NULL DEFAULT 0,
          paid REAL NOT NULL DEFAULT 0, due_date TEXT DEFAULT '', status TEXT DEFAULT 'pending',
          notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS shopping(
          id TEXT PRIMARY KEY, category TEXT DEFAULT '', item TEXT NOT NULL, unit TEXT DEFAULT '',
          needed REAL NOT NULL DEFAULT 0, bought REAL NOT NULL DEFAULT 0, unit_cost REAL NOT NULL DEFAULT 0,
          done INTEGER NOT NULL DEFAULT 0, notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks(
          id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT DEFAULT '', due_date TEXT DEFAULT '',
          priority TEXT DEFAULT 'normal', owner TEXT DEFAULT '', status TEXT DEFAULT 'pending',
          notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vendors(
          id TEXT PRIMARY KEY, category TEXT DEFAULT '', name TEXT NOT NULL, contact TEXT DEFAULT '',
          total REAL NOT NULL DEFAULT 0, paid REAL NOT NULL DEFAULT 0, due_date TEXT DEFAULT '',
          status TEXT DEFAULT 'pending', notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS songs(
          id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT DEFAULT 'manual',
          active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """)
        for k,v in DEFAULT_SETTINGS.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                      (k,json.dumps(v,ensure_ascii=False),now_iso()))

def read_settings(c: sqlite3.Connection) -> dict:
    out={}
    for r in c.execute("SELECT key,value FROM settings"):
        try: out[r["key"]]=json.loads(r["value"])
        except json.JSONDecodeError: out[r["key"]]=r["value"]
    return out

def hash_password(password: str, iterations: int = 310_000) -> str:
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,iterations)
    return f"pbkdf2_sha256${iterations}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        algo,it,salt,digest=encoded.split("$",3)
        if algo!="pbkdf2_sha256": return False
        calc=hashlib.pbkdf2_hmac("sha256",password.encode(),base64.urlsafe_b64decode(salt),int(it))
        return hmac.compare_digest(calc,base64.urlsafe_b64decode(digest))
    except Exception:
        return False

def clean_text(v, n=500) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]","",str(v or "")).strip()[:n]

def valid_email(v: str) -> bool:
    return not v or bool(re.fullmatch(r"[^@\s]{1,80}@[^@\s]{1,120}\.[^@\s]{2,30}",v))

def rate_ok(ip: str, limit=18, window=60) -> bool:
    now=time.time()
    with _lock:
        arr=[t for t in _rate.get(ip,[]) if now-t<window]
        if len(arr)>=limit:
            _rate[ip]=arr
            return False
        arr.append(now); _rate[ip]=arr
    return True

def purge_sessions():
    now=time.time()
    with _lock:
        for k in list(_sessions):
            if _sessions[k]["expires"]<now: _sessions.pop(k,None)

class Handler(BaseHTTPRequestHandler):
    server_version="WeddingAPI/2.0"

    def log_message(self, fmt, *args):
        print(f'{self.address_string()} - {fmt % args}')

    def _origin(self):
        return (self.headers.get("Origin") or "").rstrip("/")

    def _cors(self):
        origin=self._origin()
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin",origin)
            self.send_header("Vary","Origin")

    def _json(self, status, payload, cors=False, extra=None):
        body=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        if cors: self._cors()
        for k,v in (extra or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)

    def _body(self):
        try: n=int(self.headers.get("Content-Length","0"))
        except ValueError: n=0
        if n<0 or n>MAX_BODY: raise ValueError("body_too_large")
        raw=self.rfile.read(n) if n else b"{}"
        try: return json.loads(raw.decode("utf-8"))
        except Exception: raise ValueError("invalid_json")

    def _session(self, require_csrf=False):
        purge_sessions()
        cookie=self.headers.get("Cookie","")
        token=""
        for part in cookie.split(";"):
            k,_,v=part.strip().partition("=")
            if k=="wedding_session": token=v
        with _lock: sess=_sessions.get(token)
        if not sess: return None
        if require_csrf and not hmac.compare_digest(self.headers.get("X-CSRF-Token",""),sess["csrf"]):
            return None
        sess["expires"]=time.time()+SESSION_TTL
        return sess

    def _admin_or_401(self, csrf=False):
        sess=self._session(require_csrf=csrf)
        if not sess:
            self._json(HTTPStatus.UNAUTHORIZED,{"error":"unauthorized"})
            return None
        return sess

    def do_OPTIONS(self):
        if not self.path.startswith("/api/public/"):
            self.send_response(HTTPStatus.NO_CONTENT); self.end_headers(); return
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.send_header("Access-Control-Max-Age","600")
        self.end_headers()

    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/healthz":
            return self._json(200,{"ok":True})
        if p=="/api/public/config":
            with db() as c: settings=read_settings(c)
            return self._json(200,settings,cors=True)
        if p=="/api/public/songs":
            with db() as c:
                rows=[dict(r) for r in c.execute("SELECT id,title FROM songs WHERE active=1 ORDER BY created_at")]
            return self._json(200,{"songs":rows},cors=True)
        if p=="/api/admin/state":
            if not self._admin_or_401(): return
            with db() as c:
                payload={"settings":read_settings(c)}
                for t in ("guests","expenses","shopping","tasks","vendors","songs"):
                    payload[t]=[dict(r) for r in c.execute(f"SELECT * FROM {t} ORDER BY updated_at DESC")]
                payload["dashboard"]=dashboard(c,payload["settings"])
            return self._json(200,payload)
        if p=="/api/admin/session":
            sess=self._session()
            return self._json(200,{"authenticated":bool(sess),"csrf":sess["csrf"] if sess else ""})
        self._json(404,{"error":"not_found"})

    def do_POST(self):
        p=urlparse(self.path).path
        if p=="/api/public/rsvp":
            if self._origin() and self._origin() not in ALLOWED_ORIGINS:
                return self._json(403,{"error":"origin_not_allowed"},cors=True)
            if not rate_ok(self.client_address[0],18,60):
                return self._json(429,{"error":"too_many_requests"},cors=True)
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)},cors=True)
            return self._public_rsvp(data)
        if p=="/api/admin/login":
            if not rate_ok("login:"+self.client_address[0],8,300):
                return self._json(429,{"error":"too_many_attempts"})
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)})
            user=clean_text(data.get("user"),100)
            password=str(data.get("password") or "")
            if not ADMIN_HASH or not hmac.compare_digest(user,ADMIN_USER) or not verify_password(password,ADMIN_HASH):
                time.sleep(.25); return self._json(401,{"error":"invalid_credentials"})
            token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24)
            with _lock: _sessions[token]={"csrf":csrf,"expires":time.time()+SESSION_TTL}
            return self._json(200,{"ok":True,"csrf":csrf},extra={"Set-Cookie":f"wedding_session={token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={SESSION_TTL}"})
        if p=="/api/admin/logout":
            sess=self._session(require_csrf=True)
            if sess:
                cookie=self.headers.get("Cookie","")
                for part in cookie.split(";"):
                    k,_,v=part.strip().partition("=")
                    if k=="wedding_session":
                        with _lock: _sessions.pop(v,None)
            return self._json(200,{"ok":True},extra={"Set-Cookie":"wedding_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0"})
        if p=="/api/admin/guests":
            if not self._admin_or_401(csrf=True): return
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)})
            try:
                row=admin_create_guest(data)
            except ValueError as e:
                return self._json(400,{"error":str(e)})
            return self._json(201,row)
        m=re.fullmatch(r"/api/admin/(expenses|shopping|tasks|vendors|songs)",p)
        if m:
            if not self._admin_or_401(csrf=True): return
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)})
            try:
                row=create_generic(m.group(1),data)
            except ValueError as e:
                return self._json(400,{"error":str(e)})
            return self._json(201,row)
        self._json(404,{"error":"not_found"})

    def do_PUT(self):
        p=urlparse(self.path).path
        if p=="/api/admin/settings":
            if not self._admin_or_401(csrf=True): return
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)})
            if not isinstance(data,dict): return self._json(400,{"error":"invalid_payload"})
            allowed=set(DEFAULT_SETTINGS)
            with db() as c:
                for k,v in data.items():
                    if k not in allowed: continue
                    c.execute("""INSERT INTO settings(key,value,updated_at) VALUES(?,?,?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                    (k,json.dumps(v,ensure_ascii=False),now_iso()))
            return self._json(200,{"ok":True})
        self._json(404,{"error":"not_found"})

    def do_PATCH(self):
        p=urlparse(self.path).path
        m=re.fullmatch(r"/api/admin/(guests|expenses|shopping|tasks|vendors|songs)/([A-Za-z0-9_-]+)",p)
        if not m: return self._json(404,{"error":"not_found"})
        if not self._admin_or_401(csrf=True): return
        try: data=self._body()
        except ValueError as e: return self._json(400,{"error":str(e)})
        table,item_id=m.groups()
        try:
            row=update_row(table,item_id,data)
        except KeyError:
            return self._json(404,{"error":"not_found"})
        except ValueError as e:
            return self._json(400,{"error":str(e)})
        return self._json(200,row)

    def do_DELETE(self):
        p=urlparse(self.path).path
        m=re.fullmatch(r"/api/admin/(guests|expenses|shopping|tasks|vendors|songs)/([A-Za-z0-9_-]+)",p)
        if not m: return self._json(404,{"error":"not_found"})
        if not self._admin_or_401(csrf=True): return
        table,item_id=m.groups()
        with db() as c:
            cur=c.execute(f"DELETE FROM {table} WHERE id=?",(item_id,))
        return self._json(200,{"ok":cur.rowcount>0})

    def _public_rsvp(self, data):
        name=clean_text(data.get("name"),120)
        phone=re.sub(r"[^\d+]","",clean_text(data.get("phone"),40))
        email=clean_text(data.get("email"),160).lower()
        attendance="yes" if data.get("attendance")=="yes" else "no"
        seats=max(0,min(12,int(data.get("seats") or 0))) if attendance=="yes" else 0
        if len(name)<2: return self._json(400,{"error":"name_required"},cors=True)
        if not valid_email(email): return self._json(400,{"error":"invalid_email"},cors=True)
        request_id=clean_text(data.get("request_id"),80) or str(uuid.uuid4())
        diet=clean_text(data.get("diet"),240); song=clean_text(data.get("song"),240); notes=clean_text(data.get("message"),1200)
        now=now_iso(); status="confirmed" if attendance=="yes" else "declined"
        with db() as c:
            existing=c.execute("SELECT id FROM guests WHERE request_id=?",(request_id,)).fetchone()
            if existing: return self._json(200,{"ok":True,"id":existing["id"],"duplicate":True},cors=True)
            match=None
            if email: match=c.execute("SELECT id FROM guests WHERE lower(email)=? ORDER BY updated_at DESC LIMIT 1",(email,)).fetchone()
            if not match and phone: match=c.execute("SELECT id FROM guests WHERE phone=? ORDER BY updated_at DESC LIMIT 1",(phone,)).fetchone()
            if match:
                gid=match["id"]
                c.execute("""UPDATE guests SET request_id=?,name=?,phone=?,email=?,status=?,attendance=?,seats=?,diet=?,song=?,notes=?,responded_at=?,updated_at=? WHERE id=?""",
                          (request_id,name,phone,email,status,attendance,seats,diet,song,notes,now,now,gid))
            else:
                gid=str(uuid.uuid4())
                c.execute("""INSERT INTO guests(id,request_id,name,phone,email,status,attendance,seats,diet,song,notes,invited_at,responded_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (gid,request_id,name,phone,email,status,attendance,seats,diet,song,notes,now,now,now))
            if song:
                found=c.execute("SELECT id FROM songs WHERE lower(title)=lower(?)",(song,)).fetchone()
                if not found:
                    c.execute("INSERT INTO songs(id,title,source,active,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                              (str(uuid.uuid4()),song,"rsvp",1,now,now))
        return self._json(201,{"ok":True,"id":gid},cors=True)

def clean_for_table(table: str, data: dict) -> dict:
    allowed=GUEST_FIELDS if table=="guests" else TABLE_FIELDS[table]
    out={}
    for k in allowed:
        if k not in data: continue
        v=data[k]
        if k in {"seats","ticket_override","ticket_exempt","ticket_paid","gift_amount","done","active"}:
            if v in ("",None) and k=="ticket_override": out[k]=None
            else: out[k]=int(v or 0)
        elif k in {"budget","actual","paid","needed","bought","unit_cost","total"}:
            out[k]=float(v or 0)
        else: out[k]=clean_text(v,1200 if k=="notes" else 240)
    return out

def admin_create_guest(data: dict) -> dict:
    d=clean_for_table("guests",data)
    name=d.get("name","")
    if len(name)<2: raise ValueError("name_required")
    now=now_iso(); gid=str(uuid.uuid4())
    base={"phone":"","email":"","status":"pending","attendance":"","seats":1,"diet":"","song":"","notes":"",
          "ticket_override":None,"ticket_exempt":0,"ticket_paid":0,"gift_amount":0,"gift_note":"","table_no":""}
    base.update(d)
    cols=["id","name","phone","email","status","attendance","seats","diet","song","notes","ticket_override","ticket_exempt","ticket_paid","gift_amount","gift_note","table_no","invited_at","updated_at"]
    vals=[gid]+[base[k] for k in cols[1:-2]]+[now,now]
    with db() as c:
        c.execute(f"INSERT INTO guests({','.join(cols)}) VALUES({','.join('?' for _ in cols)})",vals)
        return dict(c.execute("SELECT * FROM guests WHERE id=?",(gid,)).fetchone())

def create_generic(table: str, data: dict) -> dict:
    d=clean_for_table(table,data)
    required={"expenses":"description","shopping":"item","tasks":"title","vendors":"name","songs":"title"}[table]
    if not d.get(required): raise ValueError(f"{required}_required")
    now=now_iso(); item_id=str(uuid.uuid4())
    d.update({"id":item_id,"created_at":now,"updated_at":now})
    cols=list(d)
    with db() as c:
        c.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({','.join('?' for _ in cols)})",[d[x] for x in cols])
        return dict(c.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone())

def update_row(table: str, item_id: str, data: dict) -> dict:
    d=clean_for_table(table,data)
    if not d:
        with db() as c:
            r=c.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone()
            if not r: raise KeyError
            return dict(r)
    d["updated_at"]=now_iso()
    sets=",".join(f"{k}=?" for k in d)
    with db() as c:
        cur=c.execute(f"UPDATE {table} SET {sets} WHERE id=?",[d[k] for k in d]+[item_id])
        if not cur.rowcount: raise KeyError
        return dict(c.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone())

def dashboard(c: sqlite3.Connection, settings: dict) -> dict:
    guests=[dict(r) for r in c.execute("SELECT * FROM guests")]
    ticket_price=int((settings.get("ticket") or {}).get("price") or 0)
    confirmed=[g for g in guests if g["status"]=="confirmed"]
    expected=0; paid=0; gifts=0; seats=0
    for g in confirmed:
        seats += max(0,int(g["seats"] or 0))
        unit=0 if g["ticket_exempt"] else (g["ticket_override"] if g["ticket_override"] is not None else ticket_price)
        expected += int(unit or 0)*max(1,int(g["seats"] or 1))
        paid += int(g["ticket_paid"] or 0); gifts += int(g["gift_amount"] or 0)
    ex=c.execute("SELECT COALESCE(SUM(actual),0) actual,COALESCE(SUM(paid),0) paid FROM expenses").fetchone()
    return {
        "guests_total":len(guests),"confirmed":len(confirmed),
        "declined":sum(g["status"]=="declined" for g in guests),
        "pending":sum(g["status"] in ("pending","invited","possible") for g in guests),
        "seats":seats,"ticket_expected":expected,"ticket_paid":paid,"ticket_pending":max(0,expected-paid),
        "gifts":gifts,"expenses_actual":float(ex["actual"] or 0),"expenses_paid":float(ex["paid"] or 0)
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--hash-password",action="store_true")
    args=parser.parse_args()
    if args.hash_password:
        pw=getpass.getpass("Nueva contraseña: ")
        pw2=getpass.getpass("Repetir: ")
        if pw!=pw2 or len(pw)<12: raise SystemExit("Las contraseñas no coinciden o tienen menos de 12 caracteres.")
        print(hash_password(pw)); return
    if not ADMIN_HASH:
        raise SystemExit("Falta WEDDING_ADMIN_PASSWORD_HASH. No se inicia un admin sin contraseña segura.")
    init_db()
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"Wedding API escuchando en http://{HOST}:{PORT} · DB {DB_PATH}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__":
    main()
