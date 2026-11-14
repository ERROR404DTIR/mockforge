import json,tempfile,unittest
from pathlib import Path
import app
class Tests(unittest.TestCase):
 def test_path_params(self):
  route,params=app.match_route(app.DEFAULT["routes"],"GET","/api/users/42")
  self.assertIsNotNone(route); self.assertEqual(params,{"id":"42"})
 def test_method_mismatch(self):
  route,_=app.match_route(app.DEFAULT["routes"],"DELETE","/api/health"); self.assertIsNone(route)
 def test_template_render(self):
  self.assertEqual(app.render({"id":"{{id}}","body":"{{body}}"},{"id":"7"},{"ok":1}),{"id":"7","body":{"ok":1}})
 def test_reject_traversal(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/"bad.json"; f.write_text(json.dumps({"routes":[{"method":"GET","path":"/../secret"}]}))
   with self.assertRaises(ValueError): app.load_config(f)
if __name__=="__main__": unittest.main()
