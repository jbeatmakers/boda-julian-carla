#!/usr/bin/env python3
"""Small persistent wedding backend: stdlib + SQLite, no runtime dependency on GitHub."""
from __future__ import annotations
import argparse, base64, getpass, hashlib, hmac, json, math, os, re, secrets, sqlite3, threading, time, unicodedata, uuid
from contextlib import contextmanager
from difflib import SequenceMatcher
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

DB_PATH = Path(os.environ.get("WEDDING_DB_PATH", "/var/lib/boda-julian-carla/wedding.sqlite3"))
ADMIN_USER = os.environ.get("WEDDING_ADMIN_USER", "admin")
ADMIN_HASH = os.environ.get("WEDDING_ADMIN_PASSWORD_HASH", "")
ADMIN_ENTRY_HASH = os.environ.get("WEDDING_ADMIN_ENTRY_HASH", "")
ADMIN_ENTRY_HASH_FILE = Path(os.environ.get("WEDDING_ADMIN_ENTRY_HASH_FILE", "/var/lib/boda-julian-carla/admin-entry.hash"))
HOST = os.environ.get("WEDDING_HOST", "127.0.0.1")
PORT = int(os.environ.get("WEDDING_PORT", "8787"))
ADMIN_ROOT = Path(os.environ.get("WEDDING_ADMIN_ROOT", "/opt/boda-admin"))
ALLOWED_ORIGINS = {x.strip().rstrip("/") for x in os.environ.get(
    "WEDDING_ALLOWED_ORIGINS",
    "https://bodajulianycarla.bpm.red"
).split(",") if x.strip()}
INSTAGRAM_USER_ID = os.environ.get("WEDDING_INSTAGRAM_USER_ID", "").strip()
INSTAGRAM_ACCESS_TOKEN = os.environ.get("WEDDING_INSTAGRAM_ACCESS_TOKEN", "").strip()
INSTAGRAM_GRAPH_VERSION = os.environ.get("WEDDING_META_GRAPH_VERSION", "").strip()
INSTAGRAM_PROFILE_URL = os.environ.get("WEDDING_INSTAGRAM_PROFILE_URL", "").strip()
INSTAGRAM_FEED_PATH = Path(os.environ.get("WEDDING_INSTAGRAM_FEED_PATH", "/var/lib/boda-julian-carla/instagram-feed.json"))
INSTAGRAM_AUTH_PATH = Path(os.environ.get("WEDDING_INSTAGRAM_AUTH_PATH", "/var/lib/boda-julian-carla/instagram-auth.json"))
INSTAGRAM_TARGET_USERNAME = os.environ.get("WEDDING_INSTAGRAM_TARGET_USERNAME", "juli.y.carli").strip().lstrip("@")
META_APP_ID = os.environ.get("WEDDING_META_APP_ID", "4388236648154471").strip()
META_APP_SECRET = os.environ.get("WEDDING_META_APP_SECRET", "").strip()
META_GRAPH_VERSION = os.environ.get("WEDDING_META_GRAPH_VERSION", "v26.0").strip() or "v26.0"
META_REDIRECT_URI = os.environ.get("WEDDING_META_REDIRECT_URI", "https://boda-api.13-140-183-198.sslip.io/api/admin/instagram/callback").strip()
INSTAGRAM_HEADING = os.environ.get("WEDDING_INSTAGRAM_HEADING", "Momentos de la boda").strip()
INSTAGRAM_INTRO = os.environ.get("WEDDING_INSTAGRAM_INTRO", "Fotos y videos compartidos desde nuestro Instagram.").strip()
_instagram_cache = {"at":0.0,"payload":{"enabled":False,"items":[]}}
SESSION_TTL = 8 * 3600
MAX_BODY = 16_384
_lock = threading.RLock()
_sessions: dict[str, dict] = {}
_entry_tokens: dict[str, float] = {}
_oauth_states: dict[str, float] = {}
_rate: dict[str, list[float]] = {}

DEFAULT_SETTINGS = {
    "event_at":"2026-12-18T17:00:00-03:00",
    "location_display":"San Pablo de Reyes · Jujuy",
    "rsvp_deadline_display":"1 de diciembre",
    "ceremony":{"time":"17:00","title":"Santa Misa de Casamiento","place":"Iglesia San Pedro y San Pablo","address":"Carlos Figueroa · San Pablo de Reyes · Jujuy","lat":-24.14581,"lng":-65.39445},
    "celebration":{"time":"18:30","title":"Recepción, cena & fiesta","place":"Quincho · San Pablo de Reyes","address":"A unos 300 metros de la ceremonia.","lat":-24.14816,"lng":-65.39326},
    "dress":{"title":"Estética Edén","concept":"Una gala fresca, sofisticada y luminosa, inspirada en la naturaleza al atardecer.","details":"Formal elegante. No hace falta comprar de nuevo: un buen accesorio puede terminar de llevar el conjunto al tono de la noche."},
    "ticket":{"enabled":True,"price":80000,"currency":"ARS","text":"Ese es el valor por persona para la cena y la fiesta. Si en tu invitación acordamos otra cosa, naturalmente vale eso."},
    "bank":{"holder":"","alias":"","cbu":"","mp_url":""},
    "fallback_whatsapp":"",
    "copy":{"gate_intro":"Tenemos algo para compartir con vos.","gate_help":"Ingresá el código de tu invitación.","gate_label":"Código de acceso","gate_submit":"Abrir invitación","hero_intro":"Queremos compartir este día con vos.","hero_confirm_btn":"Confirmar asistencia","hero_maps_btn":"Horarios y mapas","countdown_days":"Días","countdown_hours":"Hs","countdown_minutes":"Min","countdown_seconds":"Seg","places_eyebrow":"Ceremonia & celebración","places_title":"El casamiento","places_intro":"Los dos lugares quedan muy cerca entre sí.","ceremony_eyebrow":"I · Ceremonia","celebration_eyebrow":"II · Celebración","maps_directions":"Cómo llegar ↗","dress_eyebrow":"Dress code","rsvp_eyebrow":"R.S.V.P.","rsvp_title":"¿Nos acompañás?","rsvp_deadline_intro":"Nos ayuda mucho que respondas antes del","attendance_yes":"Sí","attendance_yes_label":"Voy","attendance_no":"No","attendance_no_label":"No podré ir","name_label":"Nombre y apellido *","phone_label":"WhatsApp / teléfono","email_label":"Email","seats_label":"Lugares a reservar","seats_hint":"La cantidad disponible se ajusta a tu invitación.","diet_label":"Restricción alimentaria","diet_placeholder":"Solo si hace falta","song_label":"Una canción que no puede faltar","song_placeholder":"Tema — artista (opcional)","decline_body":"Gracias por avisarnos. Nos alegra que hayas pasado por acá y esperamos compartir muchas otras cosas con vos.","decline_gift_note":"Al marcar que no venís, no se genera ningún importe de tarjeta. La parte de regalos queda simplemente como una opción, por si en algún momento querés tener un gesto con nosotros.","message_label":"Dedicatoria / nota","message_placeholder":"Unas palabras, si querés","submit_rsvp":"Enviar confirmación","gift_eyebrow":"Tarjeta & regalos","gift_title":"Celebrar con ustedes ya es mucho","gift_intro":"Acá dejamos todo claro y simple para que cada uno elija con tranquilidad.","ticket_eyebrow":"Si venís","ticket_title":"Tarjeta de la celebración","present_eyebrow":"Si querés tener un gesto","present_title":"Regalos","present_body":"Nos va a alegrar cualquier regalo que nazca de vos: algo elegido, algo hecho por vos o simplemente unas palabras.","present_transfer":"Y si preferís ayudarnos con dinero para esta nueva etapa, también podés hacerlo por transferencia, con el monto que te resulte bien.","transfer_eyebrow":"Datos para transferencia","transfer_holder":"Titular","transfer_alias":"Alias","transfer_cbu":"CBU/CVU","copy_button":"Copiar","mercadopago_button":"Mercado Pago ↗","instagram_eyebrow":"Instagram","instagram_title":"Momentos de la boda","instagram_intro":"Fotos y videos compartidos desde nuestro Instagram.","instagram_button":"Ver Instagram ↗","footer_date":"18 de diciembre de 2026 · Jujuy"},
    "layout":{"sections":[{"id":"lugares","label":"Horarios y mapas","visible":True},{"id":"dress","label":"Dress code","visible":True},{"id":"rsvp","label":"Confirmación de asistencia","visible":True},{"id":"regalos","label":"Tarjeta y regalos","visible":True},{"id":"instagramSection","label":"Instagram","visible":True}]},
    "planning":{"guest_buffer_pct":5,"planned_guests_override":0,"table_capacity":10,"drinkers_pct":70,"water_l_pp":1.0,"soft_l_pp":0.8,"beer_l_drinker":1.0,"wine_l_drinker":0.45,"sparkling_l_pp":0.125,"spirits_l_drinker":0.12,"ice_kg_pp":1.0,"appetizer_pieces_pp":6,"main_portions_pp":1.05,"dessert_portions_pp":1.05,"cake_g_pp":100}
}
TABLE_FIELDS = {
    "expenses":{"category","description","vendor","budget","actual","paid","due_date","status","notes"},
    "shopping":{"category","item","unit","needed","bought","unit_cost","done","notes","barcode","planning_key","source","source_url","reference_price","reference_updated_at","planning_factor"},
    "tasks":{"title","category","due_date","priority","owner","status","notes"},
    "vendors":{"category","name","contact","total","paid","due_date","status","notes","role","payment_mode","contribution_note"},
    "songs":{"title","source","active"},
    "menu":{"item","course","unit","per_person","fixed_qty","stock","unit_cost","contributor","notes"},
    "contributions":{"guest_id","contributor","category","planning_key","planning_factor","item","quantity","unit","estimated_value","status","notes"}
}
GUEST_FIELDS = {
    "name","group_name","phone","email","status","attendance","seats","seats_allowed","diet","song","notes",
    "ticket_override","ticket_exempt","ticket_paid","ticket_credit","gift_amount","gift_note","contribution_note","table_no"
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
          group_name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'pending', attendance TEXT NOT NULL DEFAULT '',
          seats INTEGER NOT NULL DEFAULT 1, seats_allowed INTEGER NOT NULL DEFAULT 1, diet TEXT NOT NULL DEFAULT '',
          song TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
          ticket_override INTEGER, ticket_exempt INTEGER NOT NULL DEFAULT 0,
          ticket_paid INTEGER NOT NULL DEFAULT 0, gift_amount INTEGER NOT NULL DEFAULT 0,
          gift_note TEXT NOT NULL DEFAULT '', table_no TEXT NOT NULL DEFAULT '',
          invited_at TEXT NOT NULL, responded_at TEXT, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_guests_phone ON guests(phone);
        CREATE INDEX IF NOT EXISTS idx_guests_email ON guests(email);
        CREATE TABLE IF NOT EXISTS rsvp_submissions(
          id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
          reported_name TEXT NOT NULL, reported_phone TEXT NOT NULL DEFAULT '', reported_email TEXT NOT NULL DEFAULT '',
          attendance TEXT NOT NULL, seats INTEGER NOT NULL DEFAULT 0,
          diet TEXT NOT NULL DEFAULT '', song TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'pending', matched_guest_id TEXT NOT NULL DEFAULT '',
          submitted_at TEXT NOT NULL, resolved_at TEXT, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rsvp_submissions_status ON rsvp_submissions(status,submitted_at);
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
        CREATE TABLE IF NOT EXISTS menu(
          id TEXT PRIMARY KEY, item TEXT NOT NULL, course TEXT DEFAULT 'other', unit TEXT DEFAULT 'porciones',
          per_person REAL NOT NULL DEFAULT 0, fixed_qty REAL NOT NULL DEFAULT 0, stock REAL NOT NULL DEFAULT 0,
          unit_cost REAL NOT NULL DEFAULT 0, contributor TEXT DEFAULT '', notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS contributions(
          id TEXT PRIMARY KEY, guest_id TEXT DEFAULT '', contributor TEXT NOT NULL, category TEXT DEFAULT '', planning_key TEXT DEFAULT '', planning_factor REAL NOT NULL DEFAULT 1,
          item TEXT NOT NULL, quantity REAL NOT NULL DEFAULT 0, unit TEXT DEFAULT '', estimated_value REAL NOT NULL DEFAULT 0,
          status TEXT DEFAULT 'promised', notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """)
        guest_columns={r["name"] for r in c.execute("PRAGMA table_info(guests)")}
        if "seats_allowed" not in guest_columns:
            c.execute("ALTER TABLE guests ADD COLUMN seats_allowed INTEGER NOT NULL DEFAULT 1")
            c.execute("UPDATE guests SET seats_allowed=CASE WHEN seats>0 THEN seats ELSE 1 END")
        migrations={
          "guests":{"ticket_credit":"INTEGER NOT NULL DEFAULT 0","contribution_note":"TEXT NOT NULL DEFAULT ''","group_name":"TEXT NOT NULL DEFAULT ''"},
          "shopping":{"barcode":"TEXT DEFAULT ''","planning_key":"TEXT DEFAULT ''","source":"TEXT DEFAULT ''","source_url":"TEXT DEFAULT ''","reference_price":"REAL NOT NULL DEFAULT 0","reference_updated_at":"TEXT DEFAULT ''","planning_factor":"REAL NOT NULL DEFAULT 1"},
          "vendors":{"role":"TEXT DEFAULT ''","payment_mode":"TEXT DEFAULT 'cash'","contribution_note":"TEXT DEFAULT ''"},
          "contributions":{"planning_key":"TEXT DEFAULT ''","planning_factor":"REAL NOT NULL DEFAULT 1"}
        }
        for table,cols in migrations.items():
            existing={r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            for col,decl in cols.items():
                if col not in existing: c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        for k,v in DEFAULT_SETTINGS.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                      (k,json.dumps(v,ensure_ascii=False),now_iso()))
        for k in ("copy","layout"):
            row=c.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone()
            if not row: continue
            try: current=json.loads(row["value"])
            except (TypeError, json.JSONDecodeError): current={}
            default=DEFAULT_SETTINGS[k]
            if k=="copy" and isinstance(current,dict):
                merged={**default,**current}
            elif k=="layout" and isinstance(current,dict):
                wanted=default.get("sections",[]); configured=current.get("sections",[])
                by_id={x.get("id"):x for x in configured if isinstance(x,dict) and x.get("id")}
                merged={"sections":[by_id.get(x["id"],x) for x in wanted]}
                wanted_ids={y["id"] for y in wanted}
                merged["sections"] += [x for x in configured if isinstance(x,dict) and x.get("id") not in wanted_ids]
            else:
                continue
            if merged!=current:
                c.execute("UPDATE settings SET value=?,updated_at=? WHERE key=?",
                          (json.dumps(merged,ensure_ascii=False),now_iso(),k))

def read_settings(c: sqlite3.Connection) -> dict:
    out=json.loads(json.dumps(DEFAULT_SETTINGS,ensure_ascii=False))
    for r in c.execute("SELECT key,value FROM settings"):
        try: value=json.loads(r["value"])
        except json.JSONDecodeError: value=r["value"]
        if isinstance(out.get(r["key"]),dict) and isinstance(value,dict):
            out[r["key"]].update(value)
        else:
            out[r["key"]]=value
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

def admin_entry_hash() -> str:
    if ADMIN_ENTRY_HASH: return ADMIN_ENTRY_HASH
    try: return ADMIN_ENTRY_HASH_FILE.read_text(encoding="utf-8").strip()
    except OSError: return ""

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

def normalize_person_name(value: str) -> str:
    text=unicodedata.normalize("NFKD",clean_text(value,160).lower())
    text="".join(ch for ch in text if not unicodedata.combining(ch))
    text=re.sub(r"[^a-z0-9]+"," ",text)
    return " ".join(text.split())

def person_name_similarity(left: str, right: str) -> float:
    a,b=normalize_person_name(left),normalize_person_name(right)
    if not a or not b: return 0.0
    if a==b: return 1.0
    direct=SequenceMatcher(None,a,b).ratio()
    sorted_a,sorted_b=" ".join(sorted(a.split()))," ".join(sorted(b.split()))
    sorted_score=SequenceMatcher(None,sorted_a,sorted_b).ratio()
    ta,tb=set(a.split()),set(b.split())
    overlap=len(ta&tb)/max(1,min(len(ta),len(tb)))
    return max(direct,sorted_score,overlap*.92)

def rsvp_match_candidates(c: sqlite3.Connection, submission, limit=4) -> list[dict]:
    name=submission["reported_name"]; phone=re.sub(r"\D","",submission["reported_phone"] or "")
    email=(submission["reported_email"] or "").strip().lower()
    ranked=[]
    for row in c.execute("SELECT * FROM guests ORDER BY name COLLATE NOCASE"):
        g=dict(row); gphone=re.sub(r"\D","",g.get("phone") or ""); gemail=(g.get("email") or "").strip().lower()
        score=person_name_similarity(name,g.get("name") or "")
        reason="Nombre parecido"
        if email and gemail and email==gemail:
            score=max(score,.995); reason="Mismo email"
        if phone and gphone and phone==gphone:
            score=max(score,.99); reason="Mismo teléfono" if reason=="Nombre parecido" else "Mismo email y teléfono"
        ranked.append((score,g,reason))
    ranked.sort(key=lambda x:(-x[0],normalize_person_name(x[1].get("name") or "")))
    return [{
        "guest_id":g["id"],"name":g["name"],"group_name":g.get("group_name") or "",
        "status":g.get("status") or "pending","score":round(score*100),"reason":reason
    } for score,g,reason in ranked[:max(1,int(limit))] if score>=.30]

def rsvp_submission_for_admin(c: sqlite3.Connection, row) -> dict:
    out=dict(row)
    out["candidates"]=rsvp_match_candidates(c,row) if row["status"]=="pending" else []
    if row["matched_guest_id"]:
        guest=c.execute("SELECT name,group_name FROM guests WHERE id=?",(row["matched_guest_id"],)).fetchone()
        if guest:
            out["matched_guest_name"]=guest["name"]; out["matched_guest_group"]=guest["group_name"]
    return out

def resolve_rsvp_submission(c: sqlite3.Connection, submission_id: str, action: str, guest_id: str="") -> dict:
    row=c.execute("SELECT * FROM rsvp_submissions WHERE id=?",(submission_id,)).fetchone()
    if not row: raise KeyError("rsvp_not_found")
    if row["status"]!="pending": raise ValueError("rsvp_already_resolved")
    now=now_iso(); attendance=row["attendance"]; status="confirmed" if attendance=="yes" else "declined"
    if action=="match":
        guest=c.execute("SELECT * FROM guests WHERE id=?",(guest_id,)).fetchone()
        if not guest: raise KeyError("guest_not_found")
        allowed=max(1,min(12,int(guest["seats_allowed"] or 1)))
        seats=min(max(1,int(row["seats"] or 1)),allowed) if attendance=="yes" else 0
        phone=guest["phone"] or row["reported_phone"]; email=guest["email"] or row["reported_email"]
        c.execute("""UPDATE guests SET request_id=?,phone=?,email=?,status=?,attendance=?,seats=?,diet=?,song=?,notes=?,responded_at=?,updated_at=? WHERE id=?""",
                  (row["request_id"],phone,email,status,attendance,seats,row["diet"],row["song"],row["notes"],now,now,guest_id))
        resolved_status="matched"; resolved_guest_id=guest_id
    elif action=="new":
        resolved_guest_id=str(uuid.uuid4())
        seats=max(1,int(row["seats"] or 1)) if attendance=="yes" else 0
        allowed=max(1,seats)
        c.execute("""INSERT INTO guests(id,request_id,name,phone,email,status,attendance,seats,seats_allowed,diet,song,notes,invited_at,responded_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (resolved_guest_id,row["request_id"],row["reported_name"],row["reported_phone"],row["reported_email"],
                   status,attendance,seats,allowed,row["diet"],row["song"],row["notes"],row["submitted_at"],now,now))
        resolved_status="new"
    else:
        raise ValueError("invalid_rsvp_resolution")
    c.execute("UPDATE rsvp_submissions SET status=?,matched_guest_id=?,resolved_at=?,updated_at=? WHERE id=?",
              (resolved_status,resolved_guest_id,now,now,submission_id))
    guest=c.execute("SELECT * FROM guests WHERE id=?",(resolved_guest_id,)).fetchone()
    return {"submission":rsvp_submission_for_admin(c,c.execute("SELECT * FROM rsvp_submissions WHERE id=?",(submission_id,)).fetchone()),"guest":dict(guest)}

def find_invited_guest(c: sqlite3.Connection, name: str, phone: str, email: str):
    if email:
        row=c.execute("SELECT * FROM guests WHERE lower(email)=? ORDER BY updated_at DESC LIMIT 1",(email,)).fetchone()
        if row: return row
    if phone:
        row=c.execute("SELECT * FROM guests WHERE phone=? ORDER BY updated_at DESC LIMIT 1",(phone,)).fetchone()
        if row: return row
    if name:
        rows=c.execute("SELECT * FROM guests WHERE lower(trim(name))=lower(trim(?)) ORDER BY updated_at DESC LIMIT 2",(name,)).fetchall()
        if len(rows)==1: return rows[0]
    return None

def purge_sessions():
    now=time.time()
    with _lock:
        for k in list(_sessions):
            if _sessions[k]["expires"]<now: _sessions.pop(k,None)
        for k in list(_entry_tokens):
            if _entry_tokens[k] < now: _entry_tokens.pop(k,None)
        for k in list(_oauth_states):
            if _oauth_states[k] < now: _oauth_states.pop(k,None)

def _graph_json(path, params):
    url=f"https://graph.facebook.com/{META_GRAPH_VERSION}/{path.lstrip('/')}?{urlencode(params)}"
    req=Request(url,headers={"User-Agent":"WeddingPlanner/1.0"})
    with urlopen(req,timeout=10) as r:
        return json.loads(r.read().decode("utf-8","replace"))

def _save_private_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    try: os.chmod(tmp,0o600)
    except OSError: pass
    os.replace(tmp,path)

def refresh_instagram_feed(force=False):
    try:
        if not force and INSTAGRAM_FEED_PATH.exists() and time.time()-INSTAGRAM_FEED_PATH.stat().st_mtime<900:
            return True
        auth=json.loads(INSTAGRAM_AUTH_PATH.read_text(encoding="utf-8"))
        token=clean_text(auth.get("access_token"),4096); ig_id=clean_text(auth.get("ig_user_id"),80)
        if not token or not ig_id: return False
        data=_graph_json(f"{ig_id}/media",{"fields":"id,caption,media_type,media_url,thumbnail_url,permalink,timestamp","limit":12,"access_token":token})
        items=[]
        for row in (data.get("data") or []):
            item={k:clean_text(row.get(k),2000) for k in ("caption","media_type","media_url","thumbnail_url","permalink","timestamp")}
            if item.get("permalink") and (item.get("media_url") or item.get("thumbnail_url")): items.append(item)
        feed={"profile_url":INSTAGRAM_PROFILE_URL or f"https://www.instagram.com/{INSTAGRAM_TARGET_USERNAME}/","updated_at":now_iso(),"items":items[:6]}
        _save_private_json(INSTAGRAM_FEED_PATH,feed)
        return bool(items)
    except Exception:
        return False

def instagram_status_payload():
    out={"app_created":bool(META_APP_ID),"configured":bool(META_APP_ID and META_APP_SECRET),"target_username":INSTAGRAM_TARGET_USERNAME,"profile_url":INSTAGRAM_PROFILE_URL or f"https://www.instagram.com/{INSTAGRAM_TARGET_USERNAME}/","connected":False,"username":"","page_name":""}
    try:
        auth=json.loads(INSTAGRAM_AUTH_PATH.read_text(encoding="utf-8"))
        out.update({"connected":bool(auth.get("access_token") and auth.get("ig_user_id")),"username":clean_text(auth.get("username"),120),"page_name":clean_text(auth.get("page_name"),160)})
    except (OSError,ValueError,TypeError): pass
    return out

def instagram_oauth_url():
    if not META_APP_ID or not META_APP_SECRET: raise ValueError("meta_not_configured")
    purge_sessions(); state=secrets.token_urlsafe(24)
    with _lock: _oauth_states[state]=time.time()+600
    params={"client_id":META_APP_ID,"redirect_uri":META_REDIRECT_URI,"state":state,"response_type":"code","scope":"pages_show_list,instagram_basic,pages_read_engagement"}
    return f"https://www.facebook.com/{META_GRAPH_VERSION}/dialog/oauth?{urlencode(params)}"

def instagram_complete_oauth(code, state):
    purge_sessions()
    with _lock: expires=_oauth_states.pop(state,None)
    if not expires or expires<time.time(): raise ValueError("oauth_state_invalid")
    token_data=_graph_json("oauth/access_token",{"client_id":META_APP_ID,"redirect_uri":META_REDIRECT_URI,"client_secret":META_APP_SECRET,"code":code})
    user_token=clean_text(token_data.get("access_token"),4096)
    if not user_token: raise ValueError("oauth_token_missing")
    try:
        long_data=_graph_json("oauth/access_token",{"grant_type":"fb_exchange_token","client_id":META_APP_ID,"client_secret":META_APP_SECRET,"fb_exchange_token":user_token})
        user_token=clean_text(long_data.get("access_token"),4096) or user_token
    except Exception: pass
    pages=_graph_json("me/accounts",{"fields":"id,name,access_token,instagram_business_account{id,username}","limit":100,"access_token":user_token}).get("data") or []
    target=None
    for row in pages:
        ig=row.get("instagram_business_account") or {}
        if str(ig.get("username") or "").lower()==INSTAGRAM_TARGET_USERNAME.lower(): target=(row,ig); break
    if not target: raise ValueError("instagram_target_not_found")
    page,ig=target; page_token=clean_text(page.get("access_token"),4096)
    if not page_token: raise ValueError("page_token_missing")
    auth={"ig_user_id":clean_text(ig.get("id"),80),"username":clean_text(ig.get("username"),120),"page_id":clean_text(page.get("id"),80),"page_name":clean_text(page.get("name"),160),"access_token":page_token,"connected_at":now_iso()}
    _save_private_json(INSTAGRAM_AUTH_PATH,auth); refresh_instagram_feed(True)
    return auth

def instagram_public_payload():
    if INSTAGRAM_AUTH_PATH.exists(): refresh_instagram_feed(False)
    payload={"enabled":False,"heading":INSTAGRAM_HEADING,"intro":INSTAGRAM_INTRO,"username":INSTAGRAM_TARGET_USERNAME,"profile_url":INSTAGRAM_PROFILE_URL or f"https://www.instagram.com/{INSTAGRAM_TARGET_USERNAME}/","items":[]}
    try:
        raw=json.loads(INSTAGRAM_FEED_PATH.read_text(encoding="utf-8"))
        items=[]
        for row in (raw.get("items") or [])[:6]:
            item={k:clean_text(row.get(k),1000) for k in ("caption","media_type","media_url","thumbnail_url","permalink","timestamp")}
            if item.get("permalink") and (item.get("media_url") or item.get("thumbnail_url")): items.append(item)
        payload["items"]=items; payload["enabled"]=bool(items)
        if raw.get("profile_url"): payload["profile_url"]=clean_text(raw.get("profile_url"),500)
    except (OSError,ValueError,TypeError): pass
    return payload

def sanitize_settings_payload(data: dict) -> dict:
    if not isinstance(data,dict): raise ValueError("invalid_payload")
    out={}
    for key,value in data.items():
        if key not in DEFAULT_SETTINGS: continue
        if key=="planning":
            if not isinstance(value,dict): raise ValueError("invalid_planning")
            clean={}
            for k,v in value.items():
                if k not in DEFAULT_SETTINGS["planning"]: continue
                try: n=float(v)
                except (TypeError,ValueError): raise ValueError("invalid_number")
                if n<0: raise ValueError("negative_value")
                if k in {"guest_buffer_pct","drinkers_pct"} and n>100: raise ValueError("invalid_percentage")
                if k=="table_capacity" and not 1<=n<=50: raise ValueError("invalid_table_capacity")
                if k=="planned_guests_override" and n>5000: raise ValueError("invalid_guest_count")
                if n>10000: raise ValueError("invalid_number")
                clean[k]=n
            out[key]=clean
        elif key=="ticket":
            if not isinstance(value,dict): raise ValueError("invalid_ticket")
            price=value.get("price",DEFAULT_SETTINGS["ticket"]["price"])
            try: price=int(price or 0)
            except (TypeError,ValueError): raise ValueError("invalid_number")
            if price<0: raise ValueError("negative_value")
            out[key]={"enabled":bool(value.get("enabled",True)),"price":price,"currency":"ARS","text":clean_text(value.get("text"),1200)}
        elif key=="bank":
            if not isinstance(value,dict): raise ValueError("invalid_bank")
            url=clean_text(value.get("mp_url"),1000)
            if url and not re.match(r"^https://",url,re.I): raise ValueError("invalid_url")
            out[key]={"holder":clean_text(value.get("holder"),200),"alias":clean_text(value.get("alias"),120),"cbu":clean_text(value.get("cbu"),80),"mp_url":url}
        elif key in {"ceremony","celebration"}:
            if not isinstance(value,dict): raise ValueError("invalid_location")
            base=DEFAULT_SETTINGS[key]; loc={k:clean_text(value.get(k,base.get(k)),500) for k in ("time","title","place","address")}
            try: lat=float(value.get("lat",base["lat"])); lng=float(value.get("lng",base["lng"]))
            except (TypeError,ValueError): raise ValueError("invalid_coordinates")
            if not -90<=lat<=90 or not -180<=lng<=180: raise ValueError("invalid_coordinates")
            loc.update({"lat":lat,"lng":lng}); out[key]=loc
        elif key=="copy":
            if not isinstance(value,dict): raise ValueError("invalid_copy")
            out[key]={k:clean_text(v,1200) for k,v in value.items() if k in DEFAULT_SETTINGS["copy"]}
        elif key=="dress":
            if not isinstance(value,dict): raise ValueError("invalid_dress")
            out[key]={k:clean_text(value.get(k),1200) for k in ("title","concept","details")}
        else:
            out[key]=clean_text(value,500)
    return out

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
        self.send_header("X-Robots-Tag","noindex, nofollow, noarchive, nosnippet, noimageindex")
        if cors: self._cors()
        for k,v in (extra or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)

    def _static(self, rel, content_type):
        path=(ADMIN_ROOT/rel).resolve()
        root=ADMIN_ROOT.resolve()
        if root not in path.parents and path!=root: return self._json(404,{"error":"not_found"})
        try: body=path.read_bytes()
        except OSError: return self._json(404,{"error":"not_found"})
        self.send_response(200); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("X-Robots-Tag","noindex, nofollow, noarchive, nosnippet, noimageindex"); self.end_headers(); self.wfile.write(body)

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
        p=urlparse(self.path).path
        cors_ok=p.startswith("/api/public/") or p=="/api/admin/entry"
        if not cors_ok:
            self.send_response(HTTPStatus.NO_CONTENT); self.end_headers(); return
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.send_header("Access-Control-Max-Age","600")
        self.end_headers()

    def do_GET(self):
        parsed=urlparse(self.path); p=parsed.path
        if p=="/api/admin/instagram/callback":
            q=parse_qs(parsed.query); code=(q.get("code") or [""])[0]; state=(q.get("state") or [""])[0]
            ok=False
            if code and state:
                try: instagram_complete_oauth(code,state); ok=True
                except Exception: ok=False
            self.send_response(303); self.send_header("Location","/?instagram="+("connected" if ok else "error")); self.send_header("Cache-Control","no-store"); self.end_headers(); return
        if p=="/" and parsed.query.startswith("entry="):
            token=parsed.query.partition("=")[2]
            purge_sessions()
            with _lock:
                expires=_entry_tokens.pop(token,None)
            if expires and expires>=time.time():
                session=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24)
                with _lock: _sessions[session]={"csrf":csrf,"expires":time.time()+SESSION_TTL}
                self.send_response(303)
                self.send_header("Location","/")
                self.send_header("Cache-Control","no-store")
                self.send_header("Set-Cookie",f"wedding_session={session}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={SESSION_TTL}")
                self.end_headers(); return
            self.send_response(303); self.send_header("Location","/"); self.send_header("Cache-Control","no-store"); self.end_headers(); return
        if p in ("/","/admin.html"):
            return self._static("admin.html","text/html; charset=utf-8")
        if p=="/assets/admin.css":
            return self._static("assets/admin.css","text/css; charset=utf-8")
        if p=="/assets/admin.js":
            return self._static("assets/admin.js","text/javascript; charset=utf-8")
        if p=="/healthz":
            return self._json(200,{"ok":True})
        if p=="/api/public/config":
            with db() as c: settings=read_settings(c)
            return self._json(200,settings,cors=True)
        if p=="/api/public/instagram":
            return self._json(200,instagram_public_payload(),cors=True)
        if p=="/api/admin/instagram/status":
            if not self._admin_or_401(): return
            return self._json(200,instagram_status_payload())
        if p=="/api/admin/instagram/connect":
            if not self._admin_or_401(): return
            try: return self._json(200,{"url":instagram_oauth_url(),**instagram_status_payload()})
            except ValueError as e: return self._json(503,{"error":str(e),**instagram_status_payload()})
        if p=="/api/public/songs":
            with db() as c:
                rows=[dict(r) for r in c.execute("SELECT id,title FROM songs WHERE active=1 ORDER BY created_at")]
            return self._json(200,{"songs":rows},cors=True)
        if p=="/api/admin/state":
            if not self._admin_or_401(): return
            with db() as c:
                payload={"settings":read_settings(c)}
                for t in ("guests","expenses","shopping","tasks","vendors","songs","menu","contributions"):
                    payload[t]=[dict(r) for r in c.execute(f"SELECT * FROM {t} ORDER BY updated_at DESC")]
                payload["rsvp_submissions"]=[rsvp_submission_for_admin(c,r) for r in c.execute("SELECT * FROM rsvp_submissions ORDER BY submitted_at DESC")]
                payload["dashboard"]=dashboard(c,payload["settings"])
                payload["planner"]=planner(c,payload["settings"])
            return self._json(200,payload)
        if p=="/api/admin/session":
            sess=self._session()
            return self._json(200,{"authenticated":bool(sess),"csrf":sess["csrf"] if sess else ""})
        if p=="/api/admin/price-lookup":
            if not self._admin_or_401(): return
            query=urlparse(self.path).query
            params={k:v for k,_,v in (x.partition("=") for x in query.split("&") if x)}
            return self._json(200,price_lookup(params.get("barcode","")))
        self._json(404,{"error":"not_found"})

    def do_POST(self):
        p=urlparse(self.path).path
        if p=="/api/public/invite":
            if self._origin() and self._origin() not in ALLOWED_ORIGINS:
                return self._json(403,{"error":"origin_not_allowed"},cors=True)
            if not rate_ok("invite:"+self.client_address[0],30,60):
                return self._json(429,{"error":"too_many_requests"},cors=True)
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)},cors=True)
            name=clean_text(data.get("name"),120)
            phone=re.sub(r"[^\d+]","",clean_text(data.get("phone"),40))
            email=clean_text(data.get("email"),160).lower()
            with db() as c: match=find_invited_guest(c,name,phone,email)
            allowed=max(1,min(12,int(match["seats_allowed"] or 1))) if match else 1
            return self._json(200,{"found":bool(match),"max_seats":allowed},cors=True)
        if p=="/api/public/rsvp":
            if self._origin() and self._origin() not in ALLOWED_ORIGINS:
                return self._json(403,{"error":"origin_not_allowed"},cors=True)
            if not rate_ok(self.client_address[0],18,60):
                return self._json(429,{"error":"too_many_requests"},cors=True)
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)},cors=True)
            return self._public_rsvp(data)
        if p=="/api/admin/entry":
            origin=self._origin()
            if origin not in ALLOWED_ORIGINS:
                return self._json(403,{"error":"origin_not_allowed"},cors=True)
            if not rate_ok("entry:"+self.client_address[0],8,300):
                return self._json(429,{"error":"too_many_attempts"},cors=True)
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)},cors=True)
            code=str(data.get("code") or "").strip().upper()
            entry_hash=admin_entry_hash()
            if not entry_hash or not verify_password(code,entry_hash):
                time.sleep(.25); return self._json(401,{"error":"invalid_entry"},cors=True)
            token=secrets.token_urlsafe(32)
            with _lock: _entry_tokens[token]=time.time()+60
            return self._json(200,{"ok":True,"entry_token":token},cors=True)
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
        m=re.fullmatch(r"/api/admin/rsvp-submissions/([A-Za-z0-9_-]+)/resolve",p)
        if m:
            if not self._admin_or_401(csrf=True): return
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)})
            action=clean_text(data.get("action"),20)
            guest_id=clean_text(data.get("guest_id"),100)
            try:
                with db() as c:
                    out=resolve_rsvp_submission(c,m.group(1),action,guest_id)
            except KeyError as e:
                return self._json(404,{"error":str(e.args[0] if e.args else "not_found")})
            except (ValueError,sqlite3.IntegrityError) as e:
                return self._json(400,{"error":str(e)})
            return self._json(200,out)
        if p=="/api/admin/guests":
            if not self._admin_or_401(csrf=True): return
            try: data=self._body()
            except ValueError as e: return self._json(400,{"error":str(e)})
            try:
                row=admin_create_guest(data)
            except ValueError as e:
                return self._json(400,{"error":str(e)})
            return self._json(201,row)
        m=re.fullmatch(r"/api/admin/(expenses|shopping|tasks|vendors|songs|menu|contributions)",p)
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
            try:
                with db() as c:
                    current=read_settings(c)
                merged={}
                for k,v in data.items():
                    if k not in DEFAULT_SETTINGS: continue
                    if isinstance(v,dict) and isinstance(current.get(k),dict):
                        merged[k]={**current[k],**v}
                    else:
                        merged[k]=v
                data=sanitize_settings_payload(merged)
            except ValueError as e:
                return self._json(400,{"error":str(e)})
            with db() as c:
                for k,v in data.items():
                    c.execute("""INSERT INTO settings(key,value,updated_at) VALUES(?,?,?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                    (k,json.dumps(v,ensure_ascii=False),now_iso()))
            return self._json(200,{"ok":True})
        self._json(404,{"error":"not_found"})

    def do_PATCH(self):
        p=urlparse(self.path).path
        m=re.fullmatch(r"/api/admin/(guests|expenses|shopping|tasks|vendors|songs|menu|contributions)/([A-Za-z0-9_-]+)",p)
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
        m=re.fullmatch(r"/api/admin/(guests|expenses|shopping|tasks|vendors|songs|menu|contributions)/([A-Za-z0-9_-]+)",p)
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
        requested_seats=max(1,min(12,int(data.get("seats") or 1))) if attendance=="yes" else 0
        if len(name)<2: return self._json(400,{"error":"name_required"},cors=True)
        if not valid_email(email): return self._json(400,{"error":"invalid_email"},cors=True)
        request_id=clean_text(data.get("request_id"),80) or str(uuid.uuid4())
        diet=clean_text(data.get("diet"),240); song=clean_text(data.get("song"),240); notes=clean_text(data.get("message"),1200)
        now=now_iso()
        with db() as c:
            existing=c.execute("SELECT id,status,matched_guest_id FROM rsvp_submissions WHERE request_id=?",(request_id,)).fetchone()
            if existing:
                return self._json(200,{"ok":True,"id":existing["id"],"duplicate":True,"review_pending":existing["status"]=="pending"},cors=True)
            legacy=c.execute("SELECT id FROM guests WHERE request_id=?",(request_id,)).fetchone()
            if legacy:
                return self._json(200,{"ok":True,"id":legacy["id"],"duplicate":True,"review_pending":False},cors=True)
            match=find_invited_guest(c,name,phone,email)
            allowed=max(1,min(12,int(match["seats_allowed"] or 1))) if match else max(1,requested_seats or 1)
            seats=min(requested_seats,allowed) if attendance=="yes" else 0
            submission_id=str(uuid.uuid4())
            c.execute("""INSERT INTO rsvp_submissions(
                id,request_id,reported_name,reported_phone,reported_email,attendance,seats,diet,song,notes,status,matched_guest_id,submitted_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,'',?,?)""",
            (submission_id,request_id,name,phone,email,attendance,seats,diet,song,notes,"pending",now,now))
            if song:
                found=c.execute("SELECT id FROM songs WHERE lower(title)=lower(?)",(song,)).fetchone()
                if not found:
                    c.execute("INSERT INTO songs(id,title,source,active,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                              (str(uuid.uuid4()),song,"rsvp",1,now,now))
        return self._json(201,{"ok":True,"id":submission_id,"review_pending":True},cors=True)

def clean_for_table(table: str, data: dict) -> dict:
    allowed=GUEST_FIELDS if table=="guests" else TABLE_FIELDS[table]
    out={}
    for k in allowed:
        if k not in data: continue
        v=data[k]
        if k in {"seats","seats_allowed","ticket_override","ticket_exempt","ticket_paid","ticket_credit","gift_amount","done","active"}:
            if v in ("",None) and k=="ticket_override":
                out[k]=None
            else:
                try: n=int(v or 0)
                except (TypeError,ValueError): raise ValueError("invalid_number")
                if k in {"ticket_exempt","done","active"}: out[k]=1 if n else 0
                elif k in {"seats","seats_allowed"}: out[k]=n
                elif n<0: raise ValueError("negative_value")
                else: out[k]=n
        elif k in {"budget","actual","paid","needed","bought","unit_cost","total","reference_price","planning_factor","per_person","fixed_qty","stock","quantity","estimated_value"}:
            try: n=float(v or 0)
            except (TypeError,ValueError): raise ValueError("invalid_number")
            if n<0: raise ValueError("negative_value")
            out[k]=n
        else: out[k]=clean_text(v,1200 if k=="notes" else 240)
    return out

def normalize_guest_values(base: dict) -> dict:
    status=base.get("status") or "pending"
    attendance=base.get("attendance") or ""
    if status not in {"possible","invited","pending","confirmed","declined"}: raise ValueError("invalid_status")
    if attendance not in {"","yes","no"}: raise ValueError("invalid_attendance")
    email=str(base.get("email") or "").lower()
    if email and not valid_email(email): raise ValueError("invalid_email")
    allowed=int(base.get("seats_allowed") or 1)
    seats=int(base.get("seats") or 0)
    if not 1<=allowed<=12: raise ValueError("invalid_seats_allowed")
    if attendance=="no" or status=="declined":
        status,attendance,seats="declined","no",0
    elif attendance=="yes" or status=="confirmed":
        status,attendance="confirmed","yes"
        seats=max(1,seats)
    if not 0<=seats<=allowed: raise ValueError("invalid_seats")
    base.update({"status":status,"attendance":attendance,"seats_allowed":allowed,"seats":seats,"email":email})
    return base

def admin_create_guest(data: dict) -> dict:
    d=clean_for_table("guests",data)
    name=d.get("name","")
    if len(name)<2: raise ValueError("name_required")
    now=now_iso(); gid=str(uuid.uuid4())
    base={"group_name":"","phone":"","email":"","status":"pending","attendance":"","seats":1,"seats_allowed":1,"diet":"","song":"","notes":"",
          "ticket_override":None,"ticket_exempt":0,"ticket_paid":0,"ticket_credit":0,"gift_amount":0,"gift_note":"","contribution_note":"","table_no":""}
    base.update(d)
    if "seats_allowed" not in d and "seats" in d:
        base["seats_allowed"]=max(int(base.get("seats_allowed") or 1),int(base.get("seats") or 0))
    base=normalize_guest_values(base)
    cols=["id","name","group_name","phone","email","status","attendance","seats","seats_allowed","diet","song","notes","ticket_override","ticket_exempt","ticket_paid","ticket_credit","gift_amount","gift_note","contribution_note","table_no","invited_at","updated_at"]
    vals=[gid]+[base[k] for k in cols[1:-2]]+[now,now]
    with db() as c:
        c.execute(f"INSERT INTO guests({','.join(cols)}) VALUES({','.join('?' for _ in cols)})",vals)
        return dict(c.execute("SELECT * FROM guests WHERE id=?",(gid,)).fetchone())

def create_generic(table: str, data: dict) -> dict:
    d=clean_for_table(table,data)
    required={"expenses":"description","shopping":"item","tasks":"title","vendors":"name","songs":"title","menu":"item","contributions":"item"}[table]
    if table=="contributions":
        if not d.get("contributor"): d["contributor"]="Sin asignar"
        if d.get("status") and d["status"] not in {"promised","received"}: raise ValueError("invalid_status")
    if table=="vendors" and d.get("payment_mode") and d["payment_mode"] not in {"cash","contribution","mixed","free"}:
        raise ValueError("invalid_payment_mode")
    if not d.get(required): raise ValueError(f"{required}_required")
    now=now_iso(); item_id=str(uuid.uuid4())
    d.update({"id":item_id,"created_at":now,"updated_at":now})
    cols=list(d)
    with db() as c:
        c.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({','.join('?' for _ in cols)})",[d[x] for x in cols])
        return dict(c.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone())

def update_row(table: str, item_id: str, data: dict) -> dict:
    d=clean_for_table(table,data)
    with db() as c:
        current=c.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone()
        if not current: raise KeyError
        if not d: return dict(current)
        if table=="guests":
            merged=dict(current); merged.update(d); merged=normalize_guest_values(merged)
            for k in ("status","attendance","seats","seats_allowed","email"): d[k]=merged[k]
        elif table=="contributions" and "status" in d and d["status"] not in {"promised","received"}:
            raise ValueError("invalid_status")
        elif table=="vendors" and "payment_mode" in d and d["payment_mode"] not in {"cash","contribution","mixed","free"}:
            raise ValueError("invalid_payment_mode")
        d["updated_at"]=now_iso()
        sets=",".join(f"{k}=?" for k in d)
        c.execute(f"UPDATE {table} SET {sets} WHERE id=?",[d[k] for k in d]+[item_id])
        return dict(c.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone())

def dashboard(c: sqlite3.Connection, settings: dict) -> dict:
    guests=[dict(r) for r in c.execute("SELECT * FROM guests")]
    ticket_price=int((settings.get("ticket") or {}).get("price") or 0)
    confirmed=[g for g in guests if g["status"]=="confirmed"]
    expected=0; paid=0; gifts=0; seats=0
    for g in confirmed:
        seats += max(0,int(g["seats"] or 0))
        unit=0 if g["ticket_exempt"] else (g["ticket_override"] if g["ticket_override"] is not None else ticket_price)
        gross=int(unit or 0)*max(1,int(g["seats"] or 1))
        expected += max(0,gross-int(g.get("ticket_credit",0) or 0))
        paid += int(g["ticket_paid"] or 0); gifts += int(g["gift_amount"] or 0)
    ex=c.execute("SELECT COALESCE(SUM(actual),0) actual,COALESCE(SUM(paid),0) paid FROM expenses").fetchone()
    review_pending=int(c.execute("SELECT COUNT(*) FROM rsvp_submissions WHERE status='pending'").fetchone()[0])
    return {
        "guests_total":len(guests),"confirmed":len(confirmed),
        "declined":sum(g["status"]=="declined" for g in guests),
        "pending":sum(g["status"] in ("pending","invited","possible") for g in guests),
        "rsvp_review_pending":review_pending,
        "seats":seats,"ticket_expected":expected,"ticket_paid":paid,"ticket_pending":max(0,expected-paid),
        "gifts":gifts,"expenses_actual":float(ex["actual"] or 0),"expenses_paid":float(ex["paid"] or 0)
    }

def _num(v, default=0.0):
    try: return float(v)
    except (TypeError,ValueError): return default

def planner(c: sqlite3.Connection, settings: dict) -> dict:
    p={**DEFAULT_SETTINGS["planning"],**(settings.get("planning") or {})}
    guests=[dict(r) for r in c.execute("SELECT * FROM guests")]
    confirmed=sum(max(0,int(g["seats"] or 0)) for g in guests if g["status"]=="confirmed")
    invited_capacity=sum(max(1,int(g["seats_allowed"] or 1)) for g in guests if g["status"] in ("pending","invited"))
    possible_capacity=sum(max(1,int(g["seats_allowed"] or 1)) for g in guests if g["status"]=="possible")
    pending=invited_capacity+possible_capacity
    override=int(_num(p.get("planned_guests_override"),0))
    forecast_base=confirmed+invited_capacity
    planned=override if override>0 else int(math.ceil(forecast_base*(1+_num(p.get("guest_buffer_pct"),5)/100)))
    planned=max(planned,confirmed)
    drinkers=int(math.ceil(planned*_num(p.get("drinkers_pct"),70)/100))
    cap=max(1,int(_num(p.get("table_capacity"),10)))
    suggestions=[
      {"key":"water","label":"Agua","unit":"L","target":round(planned*_num(p.get("water_l_pp"),1),1)},
      {"key":"soft","label":"Gaseosas / mixers","unit":"L","target":round(planned*_num(p.get("soft_l_pp"),.8),1)},
      {"key":"beer","label":"Cerveza","unit":"L","target":round(drinkers*_num(p.get("beer_l_drinker"),1),1)},
      {"key":"wine","label":"Vino","unit":"L","target":round(drinkers*_num(p.get("wine_l_drinker"),.45),1)},
      {"key":"sparkling","label":"Espumante / brindis","unit":"L","target":round(planned*_num(p.get("sparkling_l_pp"),.125),1)},
      {"key":"spirits","label":"Destilados","unit":"L","target":round(drinkers*_num(p.get("spirits_l_drinker"),.12),1)},
      {"key":"ice","label":"Hielo","unit":"kg","target":round(planned*_num(p.get("ice_kg_pp"),1),1)}]
    stock={r["planning_key"]:float(r["qty"] or 0) for r in c.execute("SELECT planning_key,COALESCE(SUM(bought*CASE WHEN planning_factor>0 THEN planning_factor ELSE 1 END),0) qty FROM shopping WHERE planning_key<>'' GROUP BY planning_key")}
    for r in c.execute("SELECT planning_key,COALESCE(SUM(quantity*CASE WHEN planning_factor>0 THEN planning_factor ELSE 1 END),0) qty FROM contributions WHERE status='received' AND planning_key<>'' GROUP BY planning_key"):
        stock[r["planning_key"]]=stock.get(r["planning_key"],0)+float(r["qty"] or 0)
    for x in suggestions:
        x["stock"]=round(stock.get(x["key"],0),2); x["missing"]=round(max(0,x["target"]-x["stock"]),2)
    menu=[]
    for r in c.execute("SELECT * FROM menu ORDER BY course,item"):
        x=dict(r); target=_num(x["fixed_qty"]) or (_num(x["per_person"])*planned)
        x["target"]=round(target,2); x["missing"]=round(max(0,target-_num(x["stock"])),2); menu.append(x)
    if not menu and planned:
        menu=[
          {"item":"Bocados / recepción","course":"appetizer","unit":"unidades","target":round(planned*_num(p.get("appetizer_pieces_pp"),6),0),"stock":0,"missing":round(planned*_num(p.get("appetizer_pieces_pp"),6),0)},
          {"item":"Plato principal","course":"main","unit":"porciones","target":round(planned*_num(p.get("main_portions_pp"),1.05),0),"stock":0,"missing":round(planned*_num(p.get("main_portions_pp"),1.05),0)},
          {"item":"Postre","course":"dessert","unit":"porciones","target":round(planned*_num(p.get("dessert_portions_pp"),1.05),0),"stock":0,"missing":round(planned*_num(p.get("dessert_portions_pp"),1.05),0)},
          {"item":"Torta","course":"cake","unit":"kg","target":round(planned*_num(p.get("cake_g_pp"),100)/1000,1),"stock":0,"missing":round(planned*_num(p.get("cake_g_pp"),100)/1000,1)}]
    contributions=[dict(r) for r in c.execute("SELECT * FROM contributions")]
    return {"confirmed":confirmed,"pending_capacity":pending,"invited_capacity":invited_capacity,"possible_capacity":possible_capacity,"forecast_base":forecast_base,"planned":planned,"tables":int(math.ceil(planned/cap)) if planned else 0,"table_capacity":cap,"drinkers":drinkers,"suggestions":suggestions,"menu":menu,"contributions_promised":sum(x["status"]=="promised" for x in contributions),"contributions_received":sum(x["status"]=="received" for x in contributions)}

def price_lookup(barcode: str) -> dict:
    barcode=re.sub(r"\D","",barcode or "")
    if len(barcode)<8: return {"found":False,"error":"barcode_invalid","offers":[]}
    base="https://d3e6htiiul5ek9.cloudfront.net/prod"
    headers={"User-Agent":"Mozilla/5.0 WeddingPlanner/1.0","Referer":"https://www.preciosclaros.gob.ar/","Origin":"https://www.preciosclaros.gob.ar"}
    try:
        def get(path,params):
            req=Request(base+path+"?"+urlencode(params),headers=headers)
            with urlopen(req,timeout=6) as r: return json.loads(r.read().decode("utf-8","replace"))
        branches=get("/sucursales",{"lat":-24.14816,"lng":-65.39326,"limit":20}).get("sucursales",[])
        ids=",".join(str(x.get("id","")) for x in branches if x.get("id"))
        detail=get("/producto",{"limit":30,"id_producto":barcode,"array_sucursales":ids})
        product=detail.get("producto") or {}
        if not product: return {"found":False,"barcode":barcode,"offers":[],"source":"Precios Claros","source_url":"https://www.preciosclaros.gob.ar/"}
        name=clean_text(product.get("nombre") or "",160); offers=[]
        for branch in detail.get("sucursales") or []:
            if not isinstance(branch,dict): continue
            price=_num((branch.get("preciosProducto") or {}).get("precioLista"))
            if price<=0: continue
            store=clean_text(branch.get("banderaDescripcion") or branch.get("sucursalNombre") or branch.get("comercioRazonSocial") or "",120)
            address=clean_text(branch.get("direccion") or "",120)
            offers.append({"price":price,"store":store,"address":address,"updated_today":bool(branch.get("actualizadoHoy"))})
        if not offers:
            low=_num(product.get("precioMin")); high=_num(product.get("precioMax"))
            if low>0: offers.append({"price":low,"store":"mínimo relevado","address":"","updated_today":False})
            if high>0 and high!=low: offers.append({"price":high,"store":"máximo relevado","address":"","updated_today":False})
        offers=sorted(offers,key=lambda x:x["price"])[:12]
        return {"found":True,"barcode":barcode,"name":name,"offers":offers,"source":"Precios Claros","source_url":"https://www.preciosclaros.gob.ar/"}
    except Exception:
        return {"found":False,"barcode":barcode,"offers":[],"source":"Precios Claros","source_url":"https://www.preciosclaros.gob.ar/","error":"price_source_unavailable"}

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
