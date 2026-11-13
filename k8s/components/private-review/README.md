# Private model review (SKIRM-470)

Prepared component, NOT enabled in the root overlay. It must not be enabled until
all prerequisites below are verified. No existing image pin is changed here.

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

1. A newly built bundles image containing the private review code from
   `shopify-bundle-app#8`, with database migrations applied through the deployment
   process. The current image does NOT contain this feature.
2. Security provisions `skirmshop/skirmshop-drive-s3-bundles`, using the existing
   1Password Connect / ExternalSecret mechanism. The runtime key must have only
   read/list access to `hideout-review/*`; no upload or deletion permissions.
   Required secret keys: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.
3. The versioned package is uploaded to the private bucket through an authorized
   upload path, and its manifest digest is checked against the value above.
4. The review references are imported idempotently into the destination database
   as `quality=draft`, using `import-model-review.mjs` and
   `import-private-review.mjs` from the application repository. Those scripts need
   a Node version capable of native TypeScript loading (22.15+), or an equivalent
   precompiled release tool. Do not assume the current Node 20 runtime can execute
   the source scripts directly. A dry-run is required before writes.
5. Security reviews the new admin file-serving boundary and this storage component.

Then add `components/private-review` to the root kustomization and pin the new
application image in the same deployment PR. This preparatory PR intentionally
leaves the root unchanged and cannot expose the review UI or restart workloads.

## Behavior and rollback

An init container copies only the pinned S3 prefix into an emptyDir, verifies the
pinned manifest digest, then verifies all listed files. The application mounts
that directory read-only as `/review`; `HIDEOUT_REVIEW_ROOT=/review` is enabled.
S3 credentials are available only to the init container, not to the application.
Admin authentication remains mandatory for reading a GLB; there is no new public
asset origin or public catalog approval.

Rolling updates keep the existing pod available (`maxUnavailable: 0`). A failed
copy or hash verification blocks the new pod rather than serving partial files.
The directory is ephemeral and limited to 256 MiB. No persistent volume is added.

Rollback is a Git revert of the component/image/package pin. Do not delete an
ArgoCD Application. Keep additive database fields and review drafts unless a
separate data-removal plan explicitly authorizes their deletion. The public
storefront is not changed by importing drafts.

## Checks performed

- Five script/configuration unit tests, including modified model, wrong manifest
  and invalid version rejection: `python3 -I tests/test_private_review.py`.
- `sh -n k8s/components/private-review/sync.sh`.
- Kustomize build of a temporary local wrapper containing the real overlay and
  this component: ConfigMap, initContainer and volume references resolve to the
  same versioned name. The root overlay itself remains unchanged.

Not yet verified: upload, private runtime credential, S3 copy in the real image,
new application image, destination database import, rollout and admin Shopify
session in production. Do not report this component as deployed.
