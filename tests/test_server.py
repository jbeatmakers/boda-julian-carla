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
        app.ADMIN_ENTRY_HASH=app.hash_password("#TEST-ENTRY-ONLY")
        app.ALLOWED_ORIGINS={"https://bodajulianycarla.bpm.red"}
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
            for table in ("rsvp_submissions","guests","expenses","shopping","tasks","vendors","songs","menu","contributions","settings"):
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
        s,d,h=self.req("GET","/api/public/config",headers={"Origin":"https://bodajulianycarla.bpm.red"})
        self.assertEqual(s,200); self.assertEqual(d["ticket"]["price"],80000)
        self.assertEqual(h.get("Access-Control-Allow-Origin"),"https://bodajulianycarla.bpm.red")
        s,ig,h=self.req("GET","/api/public/instagram",headers={"Origin":"https://bodajulianycarla.bpm.red"})
        self.assertEqual(s,200); self.assertEqual(ig["username"],"juli.y.carli")
        self.assertEqual(ig["profile_url"],"https://www.instagram.com/juli.y.carli/")
        self.assertEqual(h.get("Access-Control-Allow-Origin"),"https://bodajulianycarla.bpm.red")

    def test_rsvp_is_persistent_idempotent_and_requires_reconciliation(self):
        cookie,csrf=self.login(); admin_headers={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,invited,_=self.req("POST","/api/admin/guests",{"name":"Invitado Prueba","email":"guest@example.com","status":"invited","seats_allowed":2},admin_headers); self.assertEqual(s,201)
        headers={"Origin":"https://bodajulianycarla.bpm.red"}
        s,limit,_=self.req("POST","/api/public/invite",{"name":"Invitado Prueba","email":"guest@example.com"},headers); self.assertEqual(s,200); self.assertIsNone(limit["max_seats"]); self.assertTrue(limit["unlimited"])
        payload={"request_id":"test-rsvp-1","name":"Invitado Prueva","phone":"388 555 0101","email":"guest@example.com","attendance":"yes","seats":25,"diet":"sin TACC","song":"Tema — Artista","message":"Nos vemos"}
        s,d,_=self.req("POST","/api/public/rsvp",payload,headers); self.assertEqual(s,201); submission_id=d["id"]; self.assertTrue(d["review_pending"])
        s,d,_=self.req("POST","/api/public/rsvp",payload,headers); self.assertEqual(s,200); self.assertTrue(d["duplicate"])
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        canonical=next(x for x in d["guests"] if x["id"]==invited["id"])
        self.assertEqual(canonical["name"],"Invitado Prueba"); self.assertEqual(canonical["status"],"invited")
        pending=next(x for x in d["rsvp_submissions"] if x["id"]==submission_id)
        self.assertEqual(pending["reported_name"],"Invitado Prueva"); self.assertEqual(pending["status"],"pending")
        self.assertEqual(pending["candidates"][0]["guest_id"],invited["id"]); self.assertGreaterEqual(pending["candidates"][0]["score"],90)
        self.assertEqual(d["dashboard"]["rsvp_review_pending"],1)
        s,out,_=self.req("POST",f"/api/admin/rsvp-submissions/{submission_id}/resolve",{"action":"match","guest_id":invited["id"]},admin_headers); self.assertEqual(s,200)
        self.assertEqual(out["guest"]["name"],"Invitado Prueba")
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        g=next(x for x in d["guests"] if x["id"]==invited["id"])
        self.assertEqual(g["name"],"Invitado Prueba"); self.assertEqual(g["status"],"confirmed"); self.assertEqual(g["seats"],25)
        resolved=next(x for x in d["rsvp_submissions"] if x["id"]==submission_id); self.assertEqual(resolved["status"],"matched")
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

    def test_guest_group_roundtrip_and_rsvp_preserves_group(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,g,_=self.req("POST","/api/admin/guests",{"name":"Amigo Basket","group_name":"Basket amigos","status":"invited","email":"basket@example.com","seats_allowed":2},h); self.assertEqual(s,201)
        self.assertEqual(g["group_name"],"Basket amigos")
        s,submission,_=self.req("POST","/api/public/rsvp",{"request_id":"group-rsvp","name":"Amigo Basket","email":"basket@example.com","attendance":"yes","seats":2},{"Origin":"https://bodajulianycarla.bpm.red"}); self.assertEqual(s,201)
        s,_,_=self.req("POST",f"/api/admin/rsvp-submissions/{submission['id']}/resolve",{"action":"match","guest_id":g["id"]},h); self.assertEqual(s,200)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        saved=next(x for x in d["guests"] if x["id"]==g["id"])
        self.assertEqual(saved["group_name"],"Basket amigos"); self.assertEqual(saved["status"],"confirmed")

    def test_name_similarity_ignores_accents_and_word_order(self):
        self.assertGreaterEqual(app.person_name_similarity("José Luis Pérez","Perez Jose Luis"),.90)
        self.assertLess(app.person_name_similarity("José Luis Pérez","Carolina Gómez"),.45)

    def test_rsvp_can_choose_another_guest_or_create_new(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}; origin={"Origin":"https://bodajulianycarla.bpm.red"}
        s,first,_=self.req("POST","/api/admin/guests",{"name":"María López","group_name":"Familia","status":"invited","seats_allowed":1},h); self.assertEqual(s,201)
        s,second,_=self.req("POST","/api/admin/guests",{"name":"María Luisa López","group_name":"Amigos","status":"invited","seats_allowed":2},h); self.assertEqual(s,201)
        s,submission,_=self.req("POST","/api/public/rsvp",{"request_id":"choose-other","name":"Maria Lopez","attendance":"yes","seats":2},origin); self.assertEqual(s,201)
        s,_,_=self.req("POST",f"/api/admin/rsvp-submissions/{submission['id']}/resolve",{"action":"match","guest_id":second["id"]},h); self.assertEqual(s,200)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        one=next(x for x in d["guests"] if x["id"]==first["id"]); two=next(x for x in d["guests"] if x["id"]==second["id"])
        self.assertEqual(one["status"],"invited"); self.assertEqual(two["name"],"María Luisa López"); self.assertEqual(two["status"],"confirmed"); self.assertEqual(two["seats"],2)
        s,new_submission,_=self.req("POST","/api/public/rsvp",{"request_id":"brand-new","name":"Persona Nueva","attendance":"no","seats":1},origin); self.assertEqual(s,201)
        s,out,_=self.req("POST",f"/api/admin/rsvp-submissions/{new_submission['id']}/resolve",{"action":"new"},h); self.assertEqual(s,200)
        self.assertEqual(out["guest"]["name"],"Persona Nueva"); self.assertEqual(out["guest"]["status"],"declined"); self.assertEqual(out["submission"]["status"],"new")

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

    def test_planner_forecasts_confirmed_plus_invited_but_not_possible(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        self.req("POST","/api/admin/guests",{"name":"Confirmado","status":"confirmed","attendance":"yes","seats_allowed":2,"seats":2},h)
        self.req("POST","/api/admin/guests",{"name":"Invitado","status":"invited","seats_allowed":3,"seats":0},h)
        self.req("POST","/api/admin/guests",{"name":"Posible","status":"possible","seats_allowed":4,"seats":0},h)
        self.req("PUT","/api/admin/settings",{"planning":{"planned_guests_override":0,"guest_buffer_pct":10,"table_capacity":4}},h)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        p=d["planner"]; self.assertEqual(p["confirmed"],2); self.assertEqual(p["invited_capacity"],3); self.assertEqual(p["possible_capacity"],4)
        self.assertEqual(p["forecast_base"],5); self.assertEqual(p["planned"],6); self.assertEqual(p["tables"],2)

    def test_ticket_credit_and_menu_planning(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,g,_=self.req("POST","/api/admin/guests",{"name":"Aporte Tarjeta","status":"confirmed","attendance":"yes","seats_allowed":2,"seats":2,"ticket_credit":20000},h); self.assertEqual(s,201)
        s,_,_=self.req("POST","/api/admin/menu",{"item":"Empanadas","course":"appetizer","unit":"unidades","per_person":2,"stock":30},h); self.assertEqual(s,201)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(s,200)
        self.assertEqual(d["dashboard"]["ticket_expected"],140000)
        m=next(x for x in d["planner"]["menu"] if x["item"]=="Empanadas"); self.assertEqual(m["target"],6); self.assertEqual(m["missing"],0)

    def test_price_lookup_rejects_bad_barcode_without_network(self):
        cookie,csrf=self.login()
        s,d,_=self.req("GET","/api/admin/price-lookup?barcode=123",headers={"Cookie":cookie}); self.assertEqual(s,200); self.assertFalse(d["found"]); self.assertEqual(d["error"],"barcode_invalid")

    def test_rejects_negative_money_and_impossible_guest_limits(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,d,_=self.req("POST","/api/admin/shopping",{"item":"Vino","bought":-1},h); self.assertEqual(s,400); self.assertEqual(d["error"],"negative_value")
        s,d,_=self.req("POST","/api/admin/guests",{"name":"Cupo Malo","seats_allowed":9007199254740992},h); self.assertEqual(s,400); self.assertEqual(d["error"],"invalid_seats_allowed")
        s,g,_=self.req("POST","/api/admin/guests",{"name":"Cupo Bien","status":"confirmed","attendance":"yes","seats_allowed":3,"seats":3},h); self.assertEqual(s,201)
        s,d,_=self.req("PATCH",f"/api/admin/guests/{g['id']}",{"seats_allowed":2},h); self.assertEqual(s,400); self.assertEqual(d["error"],"invalid_seats")

    def test_guest_attendance_normalizes_status_and_seats(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,g,_=self.req("POST","/api/admin/guests",{"name":"No viene","status":"pending","attendance":"no","seats_allowed":4,"seats":3},h)
        self.assertEqual(s,201); self.assertEqual(g["status"],"declined"); self.assertEqual(g["attendance"],"no"); self.assertEqual(g["seats"],0)
        s,g,_=self.req("POST","/api/admin/guests",{"name":"Sí viene","status":"pending","attendance":"yes","seats_allowed":2,"seats":0},h)
        self.assertEqual(s,201); self.assertEqual(g["status"],"confirmed"); self.assertEqual(g["attendance"],"yes"); self.assertEqual(g["seats"],1)

    def test_settings_validation_and_partial_merge(self):
        cookie,csrf=self.login(); h={"Cookie":cookie,"X-CSRF-Token":csrf}
        s,d,_=self.req("PUT","/api/admin/settings",{"ticket":{"price":42000}},h); self.assertEqual(s,200)
        s,d,_=self.req("GET","/api/admin/state",headers={"Cookie":cookie}); self.assertEqual(d["settings"]["ticket"]["price"],42000); self.assertTrue(d["settings"]["ticket"]["enabled"]); self.assertTrue(d["settings"]["ticket"]["text"])
        s,d,_=self.req("PUT","/api/admin/settings",{"planning":{"drinkers_pct":150}},h); self.assertEqual(s,400); self.assertEqual(d["error"],"invalid_percentage")
        s,d,_=self.req("PUT","/api/admin/settings",{"planning":{"table_capacity":0}},h); self.assertEqual(s,400); self.assertEqual(d["error"],"invalid_table_capacity")
        s,d,_=self.req("PUT","/api/admin/settings",{"bank":{"mp_url":"javascript:alert(1)"}},h); self.assertEqual(s,400); self.assertEqual(d["error"],"invalid_url")

    def test_special_entry_creates_admin_session_without_login_form(self):
        origin={"Origin":"https://bodajulianycarla.bpm.red"}
        s,d,h=self.req("POST","/api/admin/entry",{"code":"#TEST-ENTRY-ONLY"},origin)
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
