import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hub.file_handoff import snapshot_listing, resolve_listing_ref


class FileHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.task = {'id': 'task-1', 'workspace': str(self.root), 'mode': 'code'}
        self.failed_id = '961841f95a974b459b05396bd6bfe2f7'
        self.other_id = '06ac47fe250f42a6b2a3d87d1b7dcca8'
        (self.root / self.failed_id).mkdir()
        (self.root / self.other_id).mkdir()
        (self.root / self.failed_id / 'supervisor.log').write_text('target')
        (self.root / self.other_id / 'supervisor.log').write_text('other')

    def test_exact_32_character_path_without_retyping(self):
        visible, obs = snapshot_listing(self.task, self.root / self.failed_id)
        ref = next(row['ref'] for row in visible if row['name']=='supervisor.log')
        path = resolve_listing_ref(self.task, ref, obs)
        self.assertEqual(Path(path).read_text(), 'target')
        self.assertIn(self.failed_id, path)

    def test_wrong_sibling_does_not_match_observed_ref(self):
        visible, obs = snapshot_listing(self.task, self.root / self.failed_id)
        wrong_visible, _ = snapshot_listing(self.task, self.root / self.other_id)
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            resolve_listing_ref(self.task, wrong_visible[0]['ref'], obs)

    def test_stale_entry_is_rejected(self):
        visible, obs = snapshot_listing(self.task, self.root / self.failed_id)
        target = self.root / self.failed_id / 'supervisor.log'
        target.write_text('new changed content')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            resolve_listing_ref(self.task, visible[0]['ref'], obs)

    def test_cross_task_reference_rejected(self):
        visible, obs = snapshot_listing(self.task, self.root / self.failed_id)
        with self.assertRaisesRegex(ValueError, 'matching file listing'):
            resolve_listing_ref({'id': 'task-2'}, visible[0]['ref'], obs)

    def test_exact_directory_reference_and_wrong_kind(self):
        visible, obs = snapshot_listing(self.task, self.root)
        ref = next(row['ref'] for row in visible if row['name']==self.failed_id)
        with self.assertRaisesRegex(ValueError, 'wrong file/directory kind'):
            resolve_listing_ref(self.task, ref, obs)
        result = resolve_listing_ref(self.task, ref, obs, directory=True)
        self.assertEqual(Path(result).resolve(), (self.root / self.failed_id).resolve())


if __name__ == '__main__':
    unittest.main()
