import re, unittest
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class Parser(HTMLParser):
    def __init__(self): super().__init__(); self.ids=set(); self.scripts=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if d.get('id'): self.ids.add(d['id'])
        if tag=='script' and d.get('src'): self.scripts.append(d['src'])

class StaticTest(unittest.TestCase):
    def test_public_contract(self):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'assets/app.js').read_text(encoding='utf-8')
        self.assertIn('BODA',js)
        self.assertIn('raw.startsWith("#")',js)
        special=''.join(('#','a','m','o','r')); self.assertNotIn(special,js.lower())
        self.assertIn('/api/admin/entry',js)
        self.assertNotIn('Colegio de Abogados',html)
        self.assertNotIn('Centro de Abogados',html)
        self.assertIn('-24.14581,-65.39445',html)
        self.assertIn('-24.14816,-65.39326',html)
        self.assertIn('celebrate-link',html)
        self.assertNotIn('Nos casamos.',html)
        self.assertNotRegex(html,r'<iframe[^>]+src=')
        self.assertIn('Si querés tener un gesto',html)
        self.assertIn('Celebrar con ustedes ya es mucho',html)
        self.assertIn('seatsHint',html)
        self.assertIn('data-site-copy="hero_intro"',html)
        self.assertIn('rel="icon"',html)
        self.assertIn('[data-site-copy]',js)
        self.assertIn('instagramSection',html)
        self.assertIn('instagramProfile',html)
        self.assertIn('/api/public/instagram',js)
        self.assertEqual(html.count('data-copy='),2)
        self.assertNotRegex(js,r'\\\\["\']')
        p=Parser(); p.feed(html)
        for needed in ('gate','gateCode','rsvpForm','ticketCard','ceremonyMap','celebrationMap'):
            self.assertIn(needed,p.ids)
        self.assertIn('assets/app.js',[src.split('?')[0] for src in p.scripts])

    def test_admin_has_no_embedded_password(self):
        html=(ROOT/'admin.html').read_text(encoding='utf-8')
        js=(ROOT/'assets/admin.js').read_text(encoding='utf-8')
        self.assertNotIn('AUTH_PASS',html+js)
        self.assertNotRegex(html+js,r'(?i)(?:password|contraseña)\s*[:=]\s*["\'][^"\']+["\']')
        self.assertIn('/api/admin/login',js)
        self.assertIn('ticket_override',js)
        self.assertIn('ticket_exempt',js)
        self.assertIn('ticket_credit',js)
        self.assertIn('Planificador de la fiesta',html)
        self.assertIn('Stock & compras',html)
        self.assertIn('data-copy-key',js)
        self.assertIn('BarcodeDetector',js)
        self.assertIn('Cargar checklist base',html)
        self.assertIn('rel="icon"',html)
        self.assertIn('ensureAccessibleNames',js)
        self.assertIn('numOr("ceremonyLatInput"',js)
        p=Parser(); p.feed(html)
        for needed in ('viewAdminBtn','viewCardBtn','cardView','fullCardPreview','guestGroupFilter','gGroup','guestGroups','rsvpReviewCard','rsvpReviewRows','rsvpReviewCount'):
            self.assertIn(needed,p.ids)
        self.assertIn('group_name',js)
        self.assertIn('/api/admin/rsvp-submissions/',js)
        self.assertIn('rsvp-match-selected',js)
        self.assertIn('rsvp-new',js)

    def test_admin_preview_bridge_is_restricted_to_api_origin(self):
        js=(ROOT/'assets/app.js').read_text(encoding='utf-8')
        self.assertIn('wedding-admin-preview',js)
        self.assertIn('e.origin===API_BASE',js)

if __name__=='__main__': unittest.main(verbosity=2)
