#!/bin/sh
set -eu

case "${REVIEW_VERSION:-}" in
  review-????????????????) ;;
  *) printf '%s\n' 'Invalid private review version' >&2; exit 1 ;;
esac
case "$REVIEW_VERSION" in *[!a-z0-9-]*) exit 1 ;; esac
case "${REVIEW_MANIFEST_SHA256:-}" in
  *[!a-f0-9]*|'') printf '%s\n' 'Invalid private review manifest digest' >&2; exit 1 ;;
esac
[ "${#REVIEW_MANIFEST_SHA256}" -eq 64 ] || exit 1
: "${REVIEW_BUCKET:?Missing private review bucket}"

review_dir=${REVIEW_DIR:-/review}
rclone copy "review:${REVIEW_BUCKET}/hideout-review/${REVIEW_VERSION}/" "$review_dir" \
  --config /dev/null --transfers 2 --checkers 2 --retries 3 --low-level-retries 3
cd "$review_dir"
printf '%s  %s\n' "$REVIEW_MANIFEST_SHA256" manifest.sha256 | sha256sum -c -
# The hash above pins the curated file list; a partial or stale copy cannot pass.
sha256sum -c manifest.sha256
printf '%s\n' "$REVIEW_VERSION" > .review-version
printf '%s\n' 'Private review package verified'
