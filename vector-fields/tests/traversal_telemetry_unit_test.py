import unittest
from traversal_pose_telemetry import anchored_lean

def telemetry(offset):
 return ('VFTraversalLean phase=3 weight=0 retreat=0 lift=0 support_extension=0.95 wall_yaw=0\n'
         'VFTraversalAnchor phase=3 hip=0,0,0 knee=0,0,0\n'
         'VFTraversalLean phase=3 weight=0 retreat=0 lift=0 support_extension=0.95 wall_yaw=0\n'
         f'VFTraversalAnchor phase=3 hip={offset},0,0 knee={offset},0,0\n')

class TelemetryTest(unittest.TestCase):
 def test_network_rounding_is_explicit(self):
  with self.assertRaises(AssertionError):anchored_lean(telemetry(.04))
  self.assertLess(anchored_lean(telemetry(.04),network_quantum=1/32)['max_world_error'],.065)
 def test_real_drift_still_fails(self):
  with self.assertRaises(AssertionError):anchored_lean(telemetry(.1),network_quantum=1/32)
 def test_local_contract_is_unchanged(self):
  self.assertEqual(anchored_lean(telemetry(.01))['tolerance'],.035)

if __name__=='__main__':unittest.main()
