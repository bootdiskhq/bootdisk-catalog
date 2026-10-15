import copy
import unittest
from bootdisk_catalog.file_association import explain_references


def ref(path, exists=True):
    return dict(path=path, exists=exists, size=12, sha256='a'*64) if exists else dict(path=path, exists=False)


def launch(path, offset=100):
    return dict(file=ref(path), frame=20, channel=91, library=3, member=4,
                script_resource=8, handler={'cp1252_view': 'mouseUp'}, offset=offset)


class FileAssociationTests(unittest.TestCase):
    def alternative(self):
        return {'issues': ['conflicting_launch_targets', 'missing_launch_file'],
                'files': {'referenced': {'direct': ref('old.exe', False), 'warning': ref('new.exe')}},
                'evidence': {'launches': {'direct': [launch('old.exe')], 'warning_continue': [launch('new.exe')]}}}

    def test_missing_alternative_preserves_input(self):
        entry = self.alternative(); before = copy.deepcopy(entry)
        self.assertEqual(explain_references(entry)['pattern'], 'missing_alternative_references')
        self.assertEqual(entry, before)

    def test_two_existing_targets_remain_unexplained(self):
        entry = self.alternative(); entry['files']['referenced']['direct'] = ref('old.exe')
        self.assertIsNone(explain_references(entry))

    def test_unknown_issue_blocks(self):
        entry = self.alternative(); entry['issues'].append('unknown')
        self.assertIsNone(explain_references(entry))

    def test_unresolved_control_blocks(self):
        entry = self.alternative(); entry['issues'].append('unresolved_warning_continue_launch')
        self.assertIsNone(explain_references(entry))

    def test_extra_file_or_missing_hash_blocks(self):
        entry = self.alternative(); entry['files']['referenced']['extra'] = ref('extra.exe')
        self.assertIsNone(explain_references(entry))
        entry = self.alternative(); del entry['files']['referenced']['warning']['sha256']
        self.assertIsNone(explain_references(entry))

    def multiple(self):
        return {'issues': ['conflicting_launch_targets'],
                'files': {'referenced': {'one': ref('one.exe'), 'two': ref('two.exe')}},
                'evidence': {'launches': {'direct': [launch('one.exe')],
                                        'warning_continue': [launch('one.exe'), launch('two.exe', 110)]}}}

    def test_multiple_files_one_handler(self):
        self.assertEqual(explain_references(self.multiple())['pattern'], 'multiple_files_in_same_handler')

    def test_different_handlers_or_missing_location_block(self):
        entry = self.multiple(); entry['evidence']['launches']['warning_continue'][1]['script_resource'] = 9
        self.assertIsNone(explain_references(entry))
        entry = self.multiple(); del entry['evidence']['launches']['warning_continue'][1]['member']
        self.assertIsNone(explain_references(entry))

    def damaged(self):
        return {'issues': ['missing_launch_file', 'conflicting_launch_targets'],
                'files': {'referenced': {'warning': ref('Game/game.exe')}},
                'evidence': {'primary_launch': {'path': 'Game/GAME.exe\x1b\x1b'},
                             'warning_continue': {'path': 'Game/game.exe'}}}

    def test_damaged_literal_is_not_rewritten(self):
        entry = self.damaged(); before = copy.deepcopy(entry)
        self.assertEqual(explain_references(entry)['pattern'], 'trailing_control_characters')
        self.assertEqual(entry, before)

    def test_different_or_unsafe_target_not_repaired(self):
        for path in ['Game/other.exe\x1b', '../Game/game.exe\x1b', 'Game/ga\x1bme.exe\x1b']:
            entry = self.damaged(); entry['evidence']['primary_launch']['path'] = path
            self.assertIsNone(explain_references(entry))
