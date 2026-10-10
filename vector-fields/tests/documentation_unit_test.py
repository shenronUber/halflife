"""Documentation facts stay tied to executable declarations."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import contract_documentation as docs


class DocumentationTests(unittest.TestCase):
    def test_current_documents_match_source_declarations(self):
        docs.generate(check=True)

    def test_stale_contract_values_are_replaced(self):
        source='# Example\n'+docs.START+'\nAPI v1; 16 parts\n'+docs.END+'\nKeep these instructions.\n'
        result=docs.update(source)
        self.assertIn(docs.block(),result);self.assertNotIn('API v1',result)
        self.assertIn('Keep these instructions.',result)
        self.assertEqual(result,docs.update(result))


if __name__=='__main__':unittest.main()
