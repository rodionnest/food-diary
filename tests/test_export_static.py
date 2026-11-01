import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from export_static import DIARIES, ROOT, export


class ExportTests(unittest.TestCase):
    def fixture(self, root):
        for filename in [*(name for name, _ in DIARIES.values()), 'static-diary.js', 'pin-gate.js', 'favicon.svg', 'nutrients.json']:
            (root / filename).write_text((ROOT / filename).read_text(encoding='utf-8'), encoding='utf-8')
        for diary in DIARIES:
            folder = root / 'data' / diary
            folder.mkdir(parents=True)
            days = {'2026-10-31': {'date': '2026-10-31', 'note': diary + '</script>', 'meals': []}}
            (folder / 'days.json').write_text(json.dumps(days), encoding='utf-8')
        (root / '.env').write_text('PRIVATE=secret', encoding='utf-8')

    def test_snapshot_preserves_data_and_only_copies_public_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            (root / 'docs').mkdir()
            (root / 'docs' / 'snapshot-data.js').write_text('old plaintext')
            (root / 'docs' / 'nutrients.json').write_text('{}')
            snapshot = export(root, pin="1234")
            docs = root / 'docs'
            payload = (docs / 'snapshot-encrypted.js').read_text(encoding='utf-8')
            envelope = json.loads(payload.removeprefix('window.ENCRYPTED_DIARY = ').strip().removesuffix(';'))
            self.assertNotIn('2026-10-31', payload)
            self.assertNotIn('1234', (docs / 'pin-gate.js').read_text())
            script = """
const {webcrypto} = require('node:crypto');
let data=''; process.stdin.on('data', c=>data+=c); process.stdin.on('end', async()=>{
const {envelope:e,pin}=JSON.parse(data);
try {
 const material=await webcrypto.subtle.importKey('raw',new TextEncoder().encode(pin),'PBKDF2',false,['deriveKey']);
 const key=await webcrypto.subtle.deriveKey({name:'PBKDF2',salt:Buffer.from(e.salt,'base64'),iterations:e.iterations,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['decrypt']);
 const decrypted=await webcrypto.subtle.decrypt({name:'AES-GCM',iv:Buffer.from(e.iv,'base64')},key,Buffer.from(e.ciphertext,'base64'));
 process.stdout.write(new TextDecoder().decode(decrypted));
} catch(error) {process.exitCode=1;}
});
"""
            def decrypt(pin, data=envelope):
                return subprocess.run(['node', '-e', script], input=json.dumps({'envelope': data, 'pin': pin}), text=True, capture_output=True)
            self.assertEqual(json.loads(decrypt('1234').stdout), snapshot)
            self.assertNotEqual(decrypt('0000').returncode, 0)
            altered = {**envelope, 'ciphertext': ('A' if envelope['ciphertext'][0] != 'A' else 'B') + envelope['ciphertext'][1:]}
            self.assertNotEqual(decrypt('1234', altered).returncode, 0)
            self.assertNotIn('</script>', payload)
            self.assertEqual({p.name for p in docs.iterdir()}, {
                *(name for name, _ in DIARIES.values()), 'index.html', 'snapshot-encrypted.js',
                'static-diary.js', 'pin-gate.js', 'favicon.svg', '.nojekyll'})
            for diary, (filename, _) in DIARIES.items():
                self.assertEqual(snapshot['diaries'][diary]['days'], json.loads((root / 'data' / diary / 'days.json').read_text()))
                self.assertEqual(snapshot['diaries'][diary]['products'], {})
                page = (docs / filename).read_text(encoding='utf-8')
                self.assertIn('snapshot-encrypted.js', page)
                self.assertIn('data-pin-locked', page)
                self.assertIn('pin-gate.js', page)
                self.assertNotIn('local-claude.js', page)
                self.assertNotIn('/api/', page)
                self.assertNotIn('id="entryText"', page)

    def test_missing_days_does_not_overwrite_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            export(root, pin="1234")
            old = (root / 'docs' / 'snapshot-encrypted.js').read_bytes()
            (root / 'data' / 'anna' / 'days.json').unlink()
            with self.assertRaises(ValueError):
                export(root, pin="1234")
            self.assertEqual((root / 'docs' / 'snapshot-encrypted.js').read_bytes(), old)
