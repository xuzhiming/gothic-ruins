import unittest
from pathlib import Path
class Pipeline(unittest.TestCase):
 def test_explicit_asset_only_web_skip(self):
  text=(Path(__file__).resolve().parents[1]/'run_all.sh').read_text()
  self.assertIn('SKIP_WEB_TEST',text)
  self.assertIn('web test NOT EXECUTED',text)
 def test_approved_alley_audit_in_pipeline(self):
  text=(Path(__file__).resolve().parents[1]/'run_all.sh').read_text()
  self.assertIn('check/test_alley_assets.py',text)
if __name__=='__main__':unittest.main()
