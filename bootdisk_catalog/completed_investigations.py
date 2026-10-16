"""Completed static investigations, keyed by exact manifest bytes and entry.

A changed manifest never inherits a completion. This records source defects,
not human approval, executable selection or installed product identification.
"""

RECORDS = [{'manifest': 'sha256:349098bdd4b779564ed5dac206626fec586078d0a9626050612d5881b12edb43',
  'entry': 'K1D2',
  'completed_at': '2026-10-16',
  'explanation': 'CD-menyen viser til to forskjellige filer. Direkteknappen viser til samme fil '
                 'som Årsregister 1999; fortsett-knappen viser til Geometra-bildene. Avviket er '
                 'undersøkt og bevart fra originalen.',
  'finding': {'entry': 'K1D2',
              'title': 'Billeder til Geometra',
              'finding': 'different_targets_in_source_menu',
              'direct_target': 'Index/Norsk/Setup.exe',
              'also_referenced_by': {'entry': 'K3D1', 'title': 'Årsregister 1999'},
              'continuation_target': 'Geometra/GImages.exe',
              'conclusion': 'Two original menu paths refer to different content. Preserve '
                            'discrepancy; no runtime target selected.'},
  'source_checks': [{'path': 'K-CN.dxr',
                     'size': 4029204,
                     'sha256': '0ad0224bfeb9111bdd25e402a2feee8340ee8f84ba361e703a5d19ef111fe6e0',
                     'matches_inventory': True},
                    {'path': 'Constant.cxt',
                     'size': 3995550,
                     'sha256': '75f4595a062dc351bbc2ef57152202ed35fa3c9e16b8fbb32528e48afc193c56',
                     'matches_inventory': True},
                    {'path': 'Norsk.cxt',
                     'size': 6180006,
                     'sha256': '09e553fddfac2d2e3adc5b5dd1225c28dd59223fc5c9293be2b9d67f73409c3d',
                     'matches_inventory': True},
                    {'path': 'Index/Norsk/Setup.exe',
                     'size': 742109,
                     'sha256': '829a35cbc00316cfea1f052ec3d3f2df3c5767d2b3e4011a9a0a6b525fdd68e2',
                     'matches_inventory': True},
                    {'path': 'Geometra/GImages.exe',
                     'size': 569602,
                     'sha256': 'c9b1b45544b61ff75fb79c0ff9879c7463d6a306234d97d47ead880cd2431359',
                     'matches_inventory': True},
                    {'path': 'AabergNo/Setup.exe',
                     'size': 285874,
                     'sha256': '9b269e1acde6c96bf0de836a0005e6794b9543248900c95ec25c7fa82015951c',
                     'matches_inventory': True}]},
 {'manifest': 'sha256:349098bdd4b779564ed5dac206626fec586078d0a9626050612d5881b12edb43',
  'entry': 'K1D4',
  'completed_at': '2026-10-16',
  'explanation': 'Fortsett-knappen viser til en tom plass i CD-ens originale menytabell. '
                 'Installasjonsfilen til Albert Åberg finnes på CD-en. Avviket er undersøkt og '
                 'bevart fra originalen.',
  'finding': {'entry': 'K1D4',
              'title': 'Albert Åberg',
              'finding': 'empty_original_cast_slot',
              'frame': 357,
              'channel': 91,
              'library': 3,
              'member': 414,
              'source_file': 'Constant.cxt',
              'cast_table_resource': 5,
              'cast_first_member': 1,
              'slot_byte_offset': 1652,
              'slot_value': 0,
              'conclusion': 'Referenced physical cast slot is empty in the source, not a silently '
                            'skipped nonzero resource.'},
  'source_checks': [{'path': 'K-CN.dxr',
                     'size': 4029204,
                     'sha256': '0ad0224bfeb9111bdd25e402a2feee8340ee8f84ba361e703a5d19ef111fe6e0',
                     'matches_inventory': True},
                    {'path': 'Constant.cxt',
                     'size': 3995550,
                     'sha256': '75f4595a062dc351bbc2ef57152202ed35fa3c9e16b8fbb32528e48afc193c56',
                     'matches_inventory': True},
                    {'path': 'Norsk.cxt',
                     'size': 6180006,
                     'sha256': '09e553fddfac2d2e3adc5b5dd1225c28dd59223fc5c9293be2b9d67f73409c3d',
                     'matches_inventory': True},
                    {'path': 'Index/Norsk/Setup.exe',
                     'size': 742109,
                     'sha256': '829a35cbc00316cfea1f052ec3d3f2df3c5767d2b3e4011a9a0a6b525fdd68e2',
                     'matches_inventory': True},
                    {'path': 'Geometra/GImages.exe',
                     'size': 569602,
                     'sha256': 'c9b1b45544b61ff75fb79c0ff9879c7463d6a306234d97d47ead880cd2431359',
                     'matches_inventory': True},
                    {'path': 'AabergNo/Setup.exe',
                     'size': 285874,
                     'sha256': '9b269e1acde6c96bf0de836a0005e6794b9543248900c95ec25c7fa82015951c',
                     'matches_inventory': True}]}]


def completed_investigation(manifest_ref, entry_id):
    matches = [r for r in RECORDS if r['manifest'] == manifest_ref and r['entry'] == entry_id]
    if len(matches) > 1:
        raise ValueError('Duplicate completed source investigation')
    if not matches:
        return None
    r = matches[0]
    return {'pattern': 'documented_source_defect', 'explanation': r['explanation'],
            'completed_at': r['completed_at'], 'manifest': r['manifest'],
            'entry': r['entry']}
