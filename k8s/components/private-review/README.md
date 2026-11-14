# Private model review (SKIRM-470)

The root overlay enables this component together with the scanned and signed
application digest below. This is deployment configuration, not proof that the
rollout, database import or authenticated Shopify review has succeeded.

## Package

- Version: `review-8ab0d624b90ec479`.
- S3 prefix: `skirmshop-drive/hideout-review/review-8ab0d624b90ec479/`.
- Manifest SHA-256: `8ab0d624b90ec47957c87697bc881d9a3933155ddcdc6b3d3094cafa64de48a7`.
- 87 self-contained GLB files and three review manifests, 74,728,306 bytes.
- These are private visual drafts, NOT dimensionally approved models.

The package contains the 22 existing model families, six revised VKS variants and
59 consumables. Files retain the relative paths expected by the private review
loader. The package manifest pins every file, and its own digest is pinned in Git.
Do not overwrite a published version; create a new package version instead.

## Preconditions for activation

1. A scanned and signed bundles image containing `shopify-bundle-app#8` and the
   dependency remediation in `shopify-bundle-app#10`. Release run `43618314437`
   published source `1def229147a51b905b055bb32d8c091ae2a17345` with digest
   `sha256:d52fb18f6833d5779f6d3a928d7df918293ed4cddeb9e88c7cbc34f808c2b472`.
   The root overlay pins that exact digest; migrations run through deployment.
2. Security provisions `skirmshop/skirmshop-drive-s3-bundles`, using the existing
   1Password Connect / ExternalSecret mechanism. The runtime key must have only
   read/list access to `hideout-review/*`; no upload or deletion permissions.
   Required secret keys: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.
3. The versioned package is uploaded to the private bucket through an authorized
   upload path, and its manifest digest is checked against the value above.
4. The new image includes Prisma as an explicit runtime dependency and the
   compiled `/app/build/review-tools/import-model-review.mjs` and
   `/app/build/review-tools/import-private-review.mjs` tools. Startup runs additive
   migrations, both dry-runs and both idempotent imports before serving. Imports
   create only drafts, never overwrite existing rows and never approve geometry.
   The server starts with `node ./node_modules/@remix-run/serve/dist/cli.js
   ./build/server/index.js`; npm and Yarn are build-time tools, absent from the
   runtime image. No native TypeScript loader or extra runtime install is needed.
5. Security reviews the new admin file-serving boundary and this storage component.

The component and image pin change in the same deployment PR. Before merging,
require green CI and Security's verdict on the final activation head. Merging
this configuration triggers the normal ArgoCD rollout; no manual apply, restart
or live patch is needed.

## Behavior and rollback

An init container copies only the pinned S3 prefix into an emptyDir, verifies the
pinned manifest digest, then verifies all listed files. The application mounts
that directory read-only as `/review`; `HIDEOUT_REVIEW_ROOT=/review` is enabled.
S3 credentials are available only to the init container, not to the application.
Admin authentication remains mandatory for reading a GLB; there is no new public
asset origin or public catalog approval.

Rolling updates keep the existing pod available (`maxUnavailable: 0`). A failed
copy, hash verification, migration or import blocks the new pod rather than
serving partial data. The directory is ephemeral and limited to 256 MiB. No
persistent volume is added. Database migrations remain additive so the old pod
can keep serving during startup.

Rollback is a Git revert of the component/image/package pin. Do not delete an
ArgoCD Application. Keep additive database fields and review drafts unless a
separate data-removal plan explicitly authorizes their deletion. The public
storefront is not changed by importing drafts.

## Checks performed

- Seven script/configuration tests, including modified model, wrong manifest,
  invalid version, startup failure and exact activation namePrefix composition:
  `python3 -I tests/test_private_review.py`.
- Local isolated PostgreSQL: six migrations applied to an empty database; all 70
  app tests passed. Real package imports created 3,839 references and 65 revised
  drafts, then created zero rows on repetition. Zero models were approved.
- `sh -n k8s/components/private-review/sync.sh`.
- Kustomize build of an isolated copy of the real overlay with this component
  enabled in that overlay (not an outer wrapper): ConfigMap, initContainer and
  volume references resolve to `bundles-private-review-sync-8ab0d624b90ec479`.
  This bundles-only component pins patched references to the final `namePrefix`;
  the regression test exercises that exact composition without network access.
  The test uses the checked-in activation and exact application digest rather
  than adding a second synthetic component declaration.

Verified on 2026-11-14 (SKIRM-478): separate runtime read-only and upload-only
credentials are provisioned through Connect/ExternalSecrets. The versioned package
was uploaded without overwriting an existing version; the manifest and all 90
listed file hashes were read back and verified with the runtime identity. There
are 91 remote objects including manifest.sha256; zero models were approved.

Application PR10 merged the dependency remediation as
`1def229147a51b905b055bb32d8c091ae2a17345`. Release run `43618314437` succeeded:
registry-verified digest, Sigstore keyless signature, SBOM and SLSA provenance.
The detailed Trivy report has no active blocking findings and one ignored finding:
CVE-2026-34077 on turbo-stream 2.4.1, authorized by SKIRM-480 only while Remix
Single Fetch is disabled, expiring on 2026-12-14 or immediately upon an incompatible
configuration/framework change. The evidence summary counter says zero suppressed
findings; the detailed report records one, which is the authoritative count.

Not yet verified: copy in the real initContainer, the new image running, destination
database import, rollout and an authenticated Shopify admin session. Do not report
this component as deployed or the complete hideout as delivered from CI alone.
