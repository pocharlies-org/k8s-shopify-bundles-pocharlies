#!/usr/bin/env python3
"""Fail closed when bundle admin and App Proxy shops diverge."""

from pathlib import Path


manifest = Path("k8s/kustomization.yaml").read_text(encoding="utf-8")
canonical = "ymimst-yh.myshopify.com"

expected = {
    f'{{ name: SHOPIFY_STORE, value: "{canonical}" }}',
    f'{{ name: SHOPIFY_ALLOWED_SHOPS, value: "{canonical}" }}',
}
missing = sorted(value for value in expected if value not in manifest)
if missing:
    raise SystemExit(f"canonical bundle shop contract missing: {missing}")

if 'SHOPIFY_ALLOWED_SHOPS, value: "skirmshop-spain.myshopify.com' in manifest:
    raise SystemExit("historical alias must not be accepted as a second App Proxy shop")

print("bundle canonical shop contract: OK")
