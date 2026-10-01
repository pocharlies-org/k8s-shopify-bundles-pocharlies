# ARCHITECTURE — k8s-shopify-bundles-pocharlies

Manifests de `shopify-bundle-app`. Código en `pocharlies-org/shopify-bundle-app`.

## Clientes y versiones
- Un Deployment web (`bundles-app`, puerto 3460, `skirmshop.e-dani.com/bundles`, ns `skirmshop` heredado de la base). Tronco: `main` (Application `shopify-bundles`, path `k8s`).

## Dependencias (ambos sentidos)
- Base `pocharlies/k8s-shopify-framework-pocharlies//base?ref=deploy/prod`; imagen `harbor.e-dani.com/homelab/shopify-bundle-app` por digest; Postgres compartido (`bundles`, pool `connection_limit=5`); secret `bundles-secrets`.

## Stack
Kustomize con base remota; sin Helm.

## Componentes compartidos
Base del framework; todo lo demás son parches inline (puerto 3460, `SHOPIFY_APP_URL`, `SCOPES`, `SHOPIFY_ALLOWED_SHOPS`, `SHOPIFY_APP_PROXY_MAX_AGE_SECONDS`, `match` del IngressRoute).

## Cómo se construye
Un solo `k8s/kustomization.yaml` (parches inline para que kubeconform no vea un Deployment sin selector).

## Tests y validaciones
`reusable-ci.yml` con `kustomize_paths: ". k8s"`.

## CI/CD y despliegue
`ci.yml` y `release.yml` (reusable-manifest-release). ArgoCD lee `main`.

## Decisiones y trampas
- `connection_limit=5` explícito: el pod corre en `sauvage` (48 vCPU) y Prisma dimensionaba el pool con las CPU del host (96 conexiones medidas el 28-07-2026).
