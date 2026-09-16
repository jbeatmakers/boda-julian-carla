import http.client, importlib.util, json, tempfile, threading, unittest
from pathlib import Path

APP_PATH=Path(__file__).resolve().parents[1]/"server"/"app.py"
spec=importlib.util.spec_from_file_location("wedding_app",APP_PATH)
app=importlib.util.module_from_spec(spec); spec.loader.exec_module(app)

class WeddingApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        app.DB_PATH=Path(cls.tmp.name)/"wedding.sqlite3"
        app.ADMIN_USER="admin"
        app.ADMIN_HASH=app.hash_password("very-secure-test-password")
        app.ADMIN_ENTRY_HASH=app.hash_password("[REDACTED-ADMIN-CODE]")
        app.ALLOWED_ORIGINS={"https://boda-julian-carla.bpm.red"}
        app._rate.clear(); app._sessions.clear()
        app.init_db()
        cls.server=app.ThreadingHTTPServer(("127.0.0.1",0),app.Handler)
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.tmp.cleanup()

    def setUp(self):
        app._rate.clear(); app._sessions.clear(); app._entry_tokens.clear()
        with app.db() as c:
            for table in ("guests","expenses","shopping","tasks","vendors","songs","settings"):
                c.execute(f"DELETE FROM {table}")
        app.init_db()

    def req(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=4)
        h=dict(headers or {})
        raw=None
        if body is not None:
            raw=json.dumps(body).encode(); h.setdefault("Content-Type","application/json")
        conn.request(method,path,body=raw,headers=h)
        res=conn.getresponse(); data=res.read(); hdr=dict(res.getheaders()); conn.close()
        try: payload=json.loads(data or b"{}")
        except Exception: payload={}
        return res.status,payload,hdr

    def login(self):
        status,data,hdr=self.req("POST","/api/admin/login",{"user":"admin","password":"very-secure-test-password"})
        self.assertEqual(status,200)
        cookie=hdr["Set-Cookie"].split(";",1)[0]
        return cookie,data["csrf"]

    def test_health_and_public_config(self):
        s,d,_=self.req("GET","/healthz"); self.assertEqual((s,d["ok"]),(200,True))
        s,d,h=self.req("GET","/api/public/config",headers={"Origin":"https://boda-julian-carla.bpm.red"})
        self.assertEqual(s,200); self.assertEqual(d["ticket"]["price"],35000)
        self.assertEqual(h.get("Access-Control-Allow-Origin"),"https://boda-julian-carla.bpm.red")

    def test_rsvp_is_persistent_and_idempotent(self):
        cookie,csrf=self.login(); admin_headers={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,invited,_=self.req("POST","/api/admin/guests",{"name":"Invitado Prueba","email":"guest@example.com","status":"invited","seats_allowed":2},admin_headers); self.assertEqual(s,201)
        headers={"Origin":"https://boda-julian-carla.bpm.red"}
        s,limit,_=self.req("POST","/api/public/invite",{"name":"Invitado Prueba","email":"guest@example.com"},headers); self.assertEqual(s,200); self.assertEqual(limit["max_seats"],2)
        payload={"request_id":"test-rsvp-1","name":"Invitado Prueba","phone":"388 555 0101","email":"guest@example.com","attendance":"yes","seats":2,"diet":"sin TACC","song":"Tema — Artista","message":"Nos vemos"}
        s,d,_=self.req("POST","/api/public/rsvp",payload,headers); self.assertEqual(s,201); gid=d["id"]
        s,d,_=self.req("POST","/api/public/rsvp",payload,headers); self.assertEqual(s,200); self.assertTrue(d["duplicate"])
        cookie,csrf=self.login()
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        g=next(x for x in d["guests"] if x["id"]==gid)
        self.assertEqual(g["status"],"confirmed"); self.assertEqual(g["seats"],2)
        self.assertTrue(any(x["title"]=="Tema — Artista" for x in d["songs"]))

    def test_admin_guest_special_price_and_free_guest(self):
        cookie,csrf=self.login(); headers={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,g,_=self.req("POST","/api/admin/guests",{"name":"Tarjeta Especial","status":"confirmed","attendance":"yes","seats":2,"ticket_override":20000},headers)
        self.assertEqual(s,201)
        s,g,_=self.req("PATCH",f"/api/admin/guests/{g['id']}",{"ticket_paid":40000,"gift_amount":15000},headers); self.assertEqual(s,200)
        s,free,_=self.req("POST","/api/admin/guests",{"name":"Invitado Sin Cargo","status":"confirmed","attendance":"yes","seats":1,"ticket_exempt":1},headers); self.assertEqual(s,201)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        self.assertGreaterEqual(d["dashboard"]["ticket_paid"],40000)
        self.assertGreaterEqual(d["dashboard"]["gifts"],15000)
        self.assertEqual(next(x for x in d["guests"] if x["id"]==free["id"])["ticket_exempt"],1)

    def test_crud_and_settings(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        for table,payload in [
            ("expenses",{"description":"DJ","actual":120000,"paid":60000}),
            ("shopping",{"item":"Agua","unit":"botellas","needed":20,"bought":5}),
            ("tasks",{"title":"Confirmar menú","priority":"high"}),
            ("vendors",{"name":"Proveedor prueba","category":"Foto","total":200000,"paid":50000}),
        ]:
            s,row,_=self.req("POST",f"/api/admin/{table}",payload,h); self.assertEqual(s,201); self.assertTrue(row["id"])
        s,_,_=self.req("PUT","/api/admin/settings",{"ticket":{"enabled":True,"price":42000,"currency":"ARS","text":"Texto nuevo"}},h); self.assertEqual(s,200)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(d["settings"]["ticket"]["price"],42000)

    def test_bad_admin_payload_is_400_not_connection_drop(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,d,_=self.req("POST","/api/admin/guests",{"name":""},h); self.assertEqual(s,400); self.assertEqual(d["error"],"name_required")
        s,d,_=self.req("POST","/api/admin/expenses",{"description":""},h); self.assertEqual(s,400); self.assertEqual(d["error"],"description_required")

    def test_planner_tables_stock_and_received_contributions(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,_,_=self.req("POST","/api/admin/guests",{"name":"Familia Uno","status":"confirmed","attendance":"yes","seats_allowed":8,"seats":8},h); self.assertEqual(s,201)
        s,_,_=self.req("PUT","/api/admin/settings",{"planning":{"planned_guests_override":20,"table_capacity":8,"drinkers_pct":50,"water_l_pp":1,"soft_l_pp":.5,"beer_l_drinker":1,"wine_l_drinker":.5,"sparkling_l_pp":.1,"spirits_l_drinker":.1,"ice_kg_pp":1,"guest_buffer_pct":5,"appetizer_pieces_pp":6,"main_portions_pp":1.05,"dessert_portions_pp":1.05,"cake_g_pp":100}},h); self.assertEqual(s,200)
        s,_,_=self.req("POST","/api/admin/shopping",{"item":"Agua stock","planning_key":"water","unit":"botellas","planning_factor":1.5,"bought":10},h); self.assertEqual(s,201)
        s,c,_=self.req("POST","/api/admin/contributions",{"contributor":"Tía Ana","item":"Agua","planning_key":"water","planning_factor":.5,"quantity":5,"unit":"botellas","status":"promised"},h); self.assertEqual(s,201)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200); self.assertEqual(d["planner"]["planned"],20); self.assertEqual(d["planner"]["tables"],3)
        water=next(x for x in d["planner"]["suggestions"] if x["key"]=="water"); self.assertEqual(water["stock"],15); self.assertEqual(water["missing"],5)
        s,_,_=self.req("PATCH",f"/api/admin/contributions/{c['id']}",{"status":"received"},h); self.assertEqual(s,200)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); water=next(x for x in d["planner"]["suggestions"] if x["key"]=="water"); self.assertEqual(water["stock"],17.5); self.assertEqual(water["missing"],2.5)

    def test_ticket_credit_and_menu_planning(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,g,_=self.req("POST","/api/admin/guests",{"name":"Aporte Tarjeta","status":"confirmed","attendance":"yes","seats_allowed":2,"seats":2,"ticket_credit":20000},h); self.assertEqual(s,201)
        s,_,_=self.req("POST","/api/admin/menu",{"item":"Empanadas","course":"appetizer","unit":"unidades","per_person":2,"stock":30},h); self.assertEqual(s,201)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        self.assertEqual(d["dashboard"]["ticket_expected"],50000)
        m=next(x for x in d["planner"]["menu"] if x["item"]=="Empanadas"); self.assertEqual(m["target"],6); self.assertEqual(m["missing"],0)

    def test_price_lookup_rejects_bad_barcode_without_network(self):
        cookie,csrf=self.login()
        s,d,_=self.req("GET","/api/admin/price-lookup?barcode=123",headers={"Cookie":cookie}); self.assertEqual(s,200); self.assertFalse(d["found"]); self.assertEqual(d["error"],"barcode_invalid")

    def test_special_entry_creates_admin_session_without_login_form(self):
        origin={"Origin":"https://boda-julian-carla.bpm.red"}
        s,d,h=self.req("POST","/api/admin/entry",{"code":"[REDACTED-ADMIN-CODE]"},origin)
        self.assertEqual(s,200); self.assertTrue(d["entry_token"])
        s,d,h=self.req("GET",f"/?entry={d['entry_token']}")
        self.assertEqual(s,303); self.assertEqual(h.get("Location"),"/")
        self.assertIn("wedding_session=",h.get("Set-Cookie",""))
        cookie=h["Set-Cookie"].split(";",1)[0]
        s,d,_=self.req("GET","/api/admin/session",headers={"Cookie":cookie})
        self.assertEqual(s,200); self.assertTrue(d["authenticated"])
        s,d,_=self.req("POST","/api/admin/entry",{"code":"wrong"},origin)
        self.assertEqual(s,401)

    def test_security_boundaries(self):
        s,d,_=self.req("GET","/api/admin/state"); self.assertEqual(s,401)
        s,d,_=self.req("POST","/api/public/rsvp",{"name":"Origen Malo","attendance":"yes","seats":1},{"Origin":"https://evil.example"}); self.assertEqual(s,403)
        cookie,csrf=self.login()
        s,d,_=self.req("POST","/api/admin/tasks",{"title":"Sin csrf"},{"Cookie":cookie}); self.assertEqual(s,401)
        s,d,_=self.req("POST","/api/admin/tasks",{"title":"Con csrf"},{"Cookie":cookie,"X-CSRF-Token":csrf}); self.assertEqual(s,201)

if __name__=="__main__": unittest.main(verbosity=2)
