"""Opt-in checks against original media; no installer or extracted code is executed."""
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import unittest
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]


class PayloadEvidenceTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('BOOTDISK_KCD_ROOT'), 'original K-CD media not supplied')
    def test_observations_reproduce_from_original_bytes(self):
        bundle = json.loads((ROOT / 'data/curation/kcd15-2001.json').read_text())
        media = Path(os.environ['BOOTDISK_KCD_ROOT'])
        cache = {}
        checked = 0
        for record in bundle['records']:
            if record['type'] != 'identification':
                continue
            for evidence in record['evidence']:
                if evidence['field'] != 'payload_observation':
                    continue
                path = evidence['source_ref']['path']
                with self.subTest(path=path, value=evidence['value']):
                    if path not in cache:
                        cache[path] = (media / path).read_bytes()
                    data = cache[path]; value = evidence['value']
                    self.assertEqual(hashlib.sha256(data).hexdigest(), value['sha256'])
                    needle = value['text'].encode('ascii')
                    if value['method'] == 'literal_bytes':
                        offset = value['offset']
                        self.assertEqual(data[offset:offset + len(needle)], needle)
                    elif value['method'] == 'zip_member':
                        with zipfile.ZipFile(io.BytesIO(data)) as archive:
                            payload = archive.read(value['member'])
                        self.assertEqual(hashlib.sha256(payload).hexdigest(), value['member_sha256'])
                        self.assertIn(needle, payload)
                    elif value['method'] == 'raw_deflate_crc32':
                        offset = value['offset']; size = value['compressed_size']
                        decoder = zlib.decompressobj(-15)
                        payload = decoder.decompress(data[offset:offset + size], value['size'] + 1)
                        self.assertTrue(decoder.eof)
                        self.assertEqual(decoder.unused_data, b'')
                        self.assertEqual(len(payload), value['size'])
                        self.assertEqual(hashlib.sha256(payload).hexdigest(), value['payload_sha256'])
                        crc = struct.unpack_from('<I', data, offset + size)[0]
                        self.assertEqual(zlib.crc32(payload), crc)
                        self.assertEqual(f'{crc:08x}', value['crc32'])
                        self.assertIn(needle, payload)
                    else:
                        self.fail('Unknown evidence method')
                    checked += 1
        self.assertEqual(checked, 22)
