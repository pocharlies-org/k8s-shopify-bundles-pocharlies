import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'k8s/components/private-review/sync.sh'


class PrivateReviewSync(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'source'
        self.target = self.root / 'target'
        self.bin = self.root / 'bin'
        for folder in [self.source, self.target, self.bin]:
            folder.mkdir()
        (self.source / 'model.glb').write_bytes(b'isolated-test-model')
        digest = hashlib.sha256((self.source / 'model.glb').read_bytes()).hexdigest()
        (self.source / 'manifest.sha256').write_text(f'{digest}  model.glb\n')
        self.manifest_hash = hashlib.sha256((self.source / 'manifest.sha256').read_bytes()).hexdigest()
        mock = self.bin / 'rclone'
        mock.write_text('#!/bin/sh\nset -eu\ncp "$SOURCE_DIR"/* "$3"/\n')
        mock.chmod(0o700)
        self.env = {**os.environ, 'PATH': f'{self.bin}:{os.environ["PATH"]}',
                    'SOURCE_DIR': str(self.source), 'REVIEW_DIR': str(self.target),
                    'REVIEW_BUCKET': 'private-test', 'REVIEW_VERSION': 'review-1234567890abcdef',
                    'REVIEW_MANIFEST_SHA256': self.manifest_hash}

    def run_script(self):
        return subprocess.run(['sh', str(SCRIPT)], env=self.env, capture_output=True, text=True)

    def test_valid_package_is_pinned_and_verified(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / '.review-version').read_text().strip(), self.env['REVIEW_VERSION'])

    def test_modified_file_cannot_pass(self):
        (self.source / 'model.glb').write_bytes(b'changed-after-manifest')
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertFalse((self.target / '.review-version').exists())

    def test_wrong_manifest_cannot_pass(self):
        self.env['REVIEW_MANIFEST_SHA256'] = '0' * 64
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertFalse((self.target / '.review-version').exists())

    def test_bad_version_does_not_copy(self):
        self.env['REVIEW_VERSION'] = '../outside'
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertFalse((self.target / 'model.glb').exists())

    def test_read_only_runtime_and_scoped_secret_are_declared(self):
        text = (ROOT / 'k8s/components/private-review/kustomization.yaml').read_text()
        self.assertIn('name: skirmshop-drive-s3-bundles', text)
        self.assertIn('maxUnavailable: 0', text)
        self.assertIn('mountPath: /review\n                    readOnly: true', text)
        self.assertNotIn('secretKeyRef:\n                        name: bundles-secrets', text)


if __name__ == '__main__':
    unittest.main()
