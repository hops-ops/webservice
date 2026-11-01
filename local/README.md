# Local validation

Use an explicit Hops local context, currently `kind-hops` (kind on Dory). Never run these fixtures against a production context.

The existing cluster needs Crossplane 2+, provider-kubernetes and provider-upjet-zitadel, Istio/Gateway API, Knative Serving/net-gateway-api 1.21, cert-manager and External Secrets with the Password generator CRD. Knative config-domain must match the platform base domain. Its local gateway must route cluster-local Knative hosts.

`prerequisites.yaml` creates two isolated test namespaces, a separate private gateway and the Knative local gateway. Per-gateway ClusterIP overrides avoid the machine cluster's global NodePort 30080 default. These prerequisites are operator-owned; individual WebServices share them.

`platform.yaml` selects local provider defaults and HTTP transport for early checks. The identity project placeholder must be filled from a dedicated local test Project, not a production project. `knative-config.yaml` configures a dedicated local Serving installation during initial operator setup. The smoke script checks these values and refuses a different configuration; it never applies them to shared ConfigMaps. Authentication requires multi-container probing enabled. `webservices.yaml` supplies two same-named private services, a cluster-only API and a public gateway. `authenticated.yaml` adds an opted-in login service. Local issuer access may need a test-specific host alias because *.localhost resolves to loopback inside pods; do not disable issuer or certificate verification.

TLS verification uses a local CA ClusterIssuer and `tls.enabled: true` in a separate test platform. A private bootstrap gateway must expose port443 with an HTTPS listener; mixing a plaintext port443 bootstrap listener with exact-host HTTPS listeners prevents a valid TLS handshake.

For HTTP/private/public validation, port-forward the distinct private and public gateway Services separately, and send the exact app Host header. TLS checks must preserve SNI and verify the test CA and hostname. Do not use curl -k. Exercise private -> public -> private with the same hostname, verify the other namespace remains private, and verify a cluster-only service has no external route. Confirm zero application pods before a cold-start request.

Auth checks provision a real local Zitadel OIDC client and secrets, start the proxy, and verify the issuer redirect/callback. Test credentials and CA private keys belong in .tmp or ignored secrets directories. Do not print tokens, cookies, or complete OAuth headers in test logs. Full allowed/disallowed-user browser sign-in is a separate integration assertion unless explicitly exercised.

Delete WebService objects first and wait for their managed resources and cross-namespace grants to disappear before removing the test project/namespaces or credential dependencies. Keep shared local prerequisites installed unless their other consumers have been audited. No production resources are changed by these fixtures.

After installing the source configuration and local prerequisites, run `make smoke-local`. Use `make smoke-local CONTEXT=colima` for an explicitly prepared Colima cluster. Existing fixture namespaces are refused, and cleanup deletes only namespaces created by the current run. This exercises real HTTPS, OIDC redirect/PKCE, exposure transitions, cold start and ordered teardown in exclusive fixture namespaces. It leaves shared local prerequisites and the source package installed. The script creates/deletes only its test services, project, platform config and namespaces.
