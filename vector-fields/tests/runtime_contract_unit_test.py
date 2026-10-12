import unittest
from runtime_contract import equipment_contract

class RuntimeContractTest(unittest.TestCase):
    def test_command_and_message_lengths_follow_appended_slots(self):
        c = equipment_contract()
        self.assertEqual(len(c['slots']), c['SlotCount'])
        self.assertEqual(c['slots'][c['HelmetSlot']], 'helmet')
        self.assertEqual(c['slots'][c['WeaponEnd']], 'helmet')
        self.assertEqual(c['BuildMessageSize'], 2+8+2*c['SlotCount']+12)
        self.assertEqual(c['StateMessageSize'], 4+12+5+2*c['SlotCount']+12)

    def test_central_validation_includes_new_integration_cases(self):
        from validate import SUITES
        expected = {'native': {'headgear_action_native_test', 'headgear_body_regression_test',
                              'headgear_feedback_test', 'traversal_posture_native_test',
                              'traversal_slide_combat_native_test'},
                    'multiplayer': {'headgear_action_network_test'}}
        for suite, names in expected.items():
            actual = {row[0].split('/')[-1].removesuffix('.py') for row in SUITES[suite]}
            self.assertTrue(names <= actual, names-actual)
