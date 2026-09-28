import importlib.util,json,tempfile,unittest
from pathlib import Path

class LayoutOrderTest(unittest.TestCase):
    def test_restart_preserves_saved_order_visibility_and_labels(self):
        path=Path(__file__).resolve().parents[1]/'server/app.py'
        spec=importlib.util.spec_from_file_location('layout_order_app',path)
        app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
        with tempfile.TemporaryDirectory() as directory:
            app.DB_PATH=Path(directory)/'isolated.sqlite3';app.init_db()
            sections=list(reversed(app.DEFAULT_SETTINGS['layout']['sections']))
            sections=[dict(item) for item in sections]
            sections[0].update(visible=False,label='Custom saved label')
            with app.db() as connection:
                connection.execute("UPDATE settings SET value=? WHERE key='layout'",(json.dumps({'sections':sections}),))
            app.init_db();app.init_db()
            with app.db() as connection:actual=app.read_settings(connection)['layout']['sections']
            self.assertEqual(actual,sections,'Startup must not reorder the admin layout')

if __name__=='__main__':unittest.main()
