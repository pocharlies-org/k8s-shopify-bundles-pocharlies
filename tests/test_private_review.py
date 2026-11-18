import hashlib
import os
from pathlib import Path
import subprocess
import shutil
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

    @unittest.skipUnless(shutil.which('kustomize'), 'kustomize is required for the composition check')
    def test_activation_references_use_the_final_prefixed_configmap(self):
        overlay = self.root / 'overlay'
        shutil.copytree(ROOT / 'k8s', overlay)
        config = overlay / 'kustomization.yaml'
        remote = 'https://github.com/pocharlies-org/k8s-shopify-framework-pocharlies.git//base?ref=deploy/prod'
        text = config.read_text()
        self.assertIn(remote, text)
        self.assertIn('components:\n  - components/private-review\n', text)
        config.write_text(text.replace(remote, 'base.yaml'))
        (overlay / 'base.yaml').write_text('''apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
        - name: app
          image: shopify-app:latest
          ports:
            - containerPort: 3000
''')
        result = subprocess.run(['kustomize', 'build', str(overlay)], capture_output=True, text=True, check=True)
        names = [line.strip() for line in result.stdout.splitlines()
                 if 'name:' in line and 'private-review-sync-8ab0d624b90ec479' in line]
        self.assertEqual(names, ['name: bundles-private-review-sync-8ab0d624b90ec479'] * 3)
        self.assertIn('image: harbor.e-dani.com/homelab/shopify-bundle-app@sha256:'
                      'a6d66a963dae5a023690c7708bbbe97220203b1468460102e83afead7d0973b0', result.stdout)
        self.assertIn('exec node ./node_modules/@remix-run/serve/dist/cli.js ./build/server/index.js', result.stdout)

    def test_startup_migrates_and_imports_before_serving(self):
        text = (ROOT / 'k8s/components/private-review/kustomization.yaml').read_text()
        block = text.split('                  - |\n', 1)[1].split('                env:', 1)[0]
        script = '\n'.join(line[20:] for line in block.splitlines())
        executable = self.root / 'node_modules/.bin'
        executable.mkdir(parents=True)
        mock = '#!/bin/sh\nset -eu\nprintf "%s %s\\n" "$0" "$*" >> "$CALL_LOG"\n[ "${FAIL_STEP:-}" != "$(basename "$0")" ]\n'
        for path in [executable / 'prisma', self.bin / 'node']:
            path.write_text(mock)
            path.chmod(0o700)
        log = self.root / 'calls.log'
        env = {**self.env, 'CALL_LOG': str(log)}
        result = subprocess.run(['sh', '-ec', script], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = log.read_text().splitlines()
        self.assertEqual(len(calls), 6)
        self.assertTrue(calls[0].endswith('prisma migrate deploy'))
        self.assertNotIn('--apply', calls[1])
        self.assertNotIn('--apply', calls[2])
        self.assertTrue(calls[3].endswith('--apply'))
        self.assertTrue(calls[4].endswith('--apply'))
        self.assertTrue(calls[5].endswith('node ./node_modules/@remix-run/serve/dist/cli.js ./build/server/index.js'))
        for failed, expected_calls in [('prisma', 1), ('node', 2)]:
            log.unlink()
            failed_run = subprocess.run(['sh', '-ec', script], cwd=self.root,
                                        env={**env, 'FAIL_STEP': failed}, capture_output=True, text=True)
            self.assertNotEqual(failed_run.returncode, 0)
            self.assertEqual(len(log.read_text().splitlines()), expected_calls)

    def test_read_only_runtime_and_ovh_secret_are_declared(self):
        # INFRA-1175: el paquete se sirve ya desde OVH Object Storage; la
        # credencial es el ExternalSecret bundles-s3-ovh (usuario compartido
        # k8s-objectstore hasta que security cree el usuario OVH propio).
        text = (ROOT / 'k8s/components/private-review/kustomization.yaml').read_text()
        self.assertIn('name: bundles-s3-ovh', text)
        self.assertIn('value: https://s3.sbg.io.cloud.ovh.net', text)
        self.assertIn('value: Other', text)
        self.assertIn('value: sbg', text)
        self.assertIn('name: RCLONE_CONFIG_REVIEW_FORCE_PATH_STYLE', text)
        self.assertNotIn('backup-hub', text)
        self.assertIn('maxUnavailable: 0', text)
        self.assertIn('mountPath: /review\n                    readOnly: true', text)
        self.assertNotIn('secretKeyRef:\n                        name: bundles-secrets', text)
        es = (ROOT / 'k8s/components/private-review/s3-ovh.externalsecret.yaml').read_text()
        self.assertIn('key: ovh-object-storage-s3', es)
        self.assertIn('name: bundles-s3-ovh', es)
        self.assertIn('security.e-dani.com/rotation-class: object-storage', es)


if __name__ == '__main__':
    unittest.main()
