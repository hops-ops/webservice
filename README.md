# WebService

Deploy an HTTP component with private exposure by default, automatic TLS, and optional platform sign-in. APIs, frontend servers, application gateways and Storybook sites use the same resource.

The configuration uses Knative underneath. It consumes the existing platform; it does not install Knative, Istio, DNS, or an identity provider for each service.

## Getting started

An operator first supplies an [EnvironmentConfig](examples/platform.yaml) named `webservice-default`. It holds the target Kubernetes ProviderConfig, base domain, private gateway, Knative local gateway and identity defaults. Developers then need:

```yaml
apiVersion: workloads.hops.ops.com.ai/v1alpha1
kind: WebService
metadata:
  name: ui
  namespace: api-pr-67
spec:
  image: ghcr.io/example/ui:v1
  port: 8080
  auth:
    enabled: true
```

The URL is `https://ui.api-pr-67.<baseDomain>`. The target namespace must exist. The image must support running as a non-root user; set the appropriate UID through `podTemplate.securityContext` if the image does not declare one.

`exposure` defaults to `private`. Authentication defaults **off**; enabling it provisions the complete browser login integration using the operator's issuer, project, provider and allowed-group defaults. Product login pages and APIs with native authentication can leave the browser gate off.

| Exposure | Result |
|---|---|
| `cluster` | Cluster-local Knative endpoint; no external route or app DNS record. |
| `private` | Exact HTTPS hostname through the operator's private gateway. |
| `public` | Native external Knative routing and certificates. |

Private exposure needs actual internal-only gateway connectivity. A hostname or private label alone does not create a VPN or enforce network policies. Cloudflare records remain DNS-only and may resolve publicly to an internal target.

## Growing

[Examples](examples/webservices) cover private, public, cluster-only, authenticated, configured and observe-only adoption. Each service chooses exposure independently, including services sharing a preview namespace.

Use `envFrom` for same-namespace Secret/ConfigMap environment sources, or `env` with Kubernetes `value`/`valueFrom` entries for configuration and same-namespace Secret references. `resources`, `probes.readiness`, `probes.startup` and `probes.liveness` configure the application container. `scaling.minReplicas` defaults to zero; use one for an always-running HTTP API. `scaling.maxReplicas`, `scaling.concurrency` and `requestTimeoutSeconds` bound concurrency and request duration. Private HTTPRoute request/backend timeouts use the same request timeout. Persistent connections and background work must be evaluated before moving an existing service to scale-to-zero.

Set the listening port through `spec.port`; `PORT` is reserved and is supplied to the application with or without the login sidecar.

`volumeMounts` configures application mounts against `podTemplate.volumes`, including projected Secret credentials and disposable `emptyDir` storage. Mount the directory rather than a `subPath` when credential files must rotate. `securityContext` adds application settings such as a read-only root filesystem while retaining disabled privilege escalation and dropped capabilities. Caller-supplied Secrets are not owned or deleted by WebService.

`sidecars` adds named companion containers. Names `app`, `login`, `queue-proxy` and `istio-proxy` are reserved; companions cannot declare request ports. Configure their probes, mounts, resources and security settings explicitly. Use the operator's Knative feature settings for init containers, multi-container probing and a shared process namespace. These features are not enabled by the XR.

An existing private endpoint can retain its exact DNS name through `hostname`. This override is accepted only with private exposure; ordinary services keep the default name. [Mounted service example](examples/webservices/mounted.yaml).

Keep background services at `scaling.minReplicas: 1` and verify idle CPU availability on the target platform. Scale bounds apply per revision, so a maximum of one does not prevent old and new revisions from overlapping during rollout; use application coordination for singleton workers.

`revisionAnnotations` supplies build identity and Knative startup progress deadlines; explicit scaling fields take precedence.

`podTemplate` passes additional Knative revision settings such as volumes, service account and scheduling. Its `containers` field is reserved; configure the application through the documented fields. Knative feature flags must permit any optional pod settings you select. Current defaults require `kubernetes.podspec-securitycontext: enabled` in Knative Serving. Authentication also requires `multi-container-probing: enabled`: the application has a TCP readiness default alongside the proxy readiness check.

An application gateway is another WebService. Its image and environment settings determine upstream routing, trusted headers, cookies and native sessions. This package does not rewrite that application behavior. The login proxy preserves the incoming Host; private ingress also supplies the original external hostname in `X-Forwarded-Host` after Knative routing rewrites. Configure the application to trust the platform proxy when it needs forwarded origin headers. A UI library is a build artifact; its deployed docs/demo server is the WebService.

## Enterprise scale

Operators can provide additional EnvironmentConfigs named `webservice-<name>` and select one with `spec.platformRef.name`. Provider references include their kind and can target another cluster. The remote namespace must exist; this XR does not take shared namespace ownership.

Platform auth defaults require a standard OIDC `groups` claim and a nonempty allowed-group policy. `auth.allowedGroups` explicitly overrides that list for a service. The Zitadel project must emit the corresponding groups claim (for example through the platform's existing role-to-group action). Successful login without an allowed group is denied by oauth2-proxy. The package does not create users or grant roles.

For private identity providers, `data.auth.caBundle` contains the public PEM trust bundle. It is copied to a per-service ConfigMap and used by the proxy to verify the issuer. TLS verification remains enabled. The session cookie is generated once through External Secrets' Password generator, is host-only, and is retained during ordinary reconciles. OIDC uses authorization code, confidential-client credentials and PKCE.

Treat EnvironmentConfig write access, provider credentials and cross-namespace gateway permissions as platform administration. Do not store tokens in EnvironmentConfigs or application YAML. Keep account numbers, deployment domains and identity IDs in operator configuration.

## Import existing

Kubernetes Object resources use deterministic native resource names. Start with `managementPolicies: [Observe]` to inspect a matching existing workload, then hand off its previous owner's management explicitly before enabling updates. A label or manifest rename is not an ownership migration.

`auth.externalName` can adopt an existing Zitadel application using the provider's external-name format. Imported OIDC clients require their existing client credentials to be available: providers cannot recover a previously issued client secret merely by importing its application ID. Use a newly provisioned client or an explicit credential migration; never rotate a production client silently.

For an existing frontend service: install and verify the new configuration; render equivalent WebService output using the same image, identity policy, host and gateway; plan the Argo/Helm ownership handoff for each resource; migrate a normal PR preview first; verify private/public/login/teardown; then update the app chart to emit the XR.

## Resources and status

Every WebService owns a provider-kubernetes Object for its Knative Service. Private services also own a native Knative Certificate, logical Gateway, exact-host HTTPRoute and scoped ReferenceGrants. Logical Gateways share the configured private gateway Service and pods; the XR does not create a load balancer per application. TLS is issued and renewed by Knative's cert-manager integration.

With auth enabled it also owns a Zitadel Oidc, a target credential Secret bridge, Password generator, CreatedOnce ExternalSecret, optional issuer CA ConfigMap, and an oauth2-proxy sidecar. Credentials are copied from the control-plane connection Secret through provider-kubernetes references, without exposing them in XR status.

Read `status.serviceUrl` for the observed Knative endpoint, `status.url` for the consumer URL, `status.latestReadyRevision` for rollout state, and `status.ready` / the standard Ready condition for reconciliation. Status never contains credentials.

Usages order route/gateway/certificate and workload/credential deletion. The private TLS Secret is observed for explicit teardown without writing certificate data. Native public TLS Secret cleanup follows the platform's cert-manager owner-reference policy. ExternalDNS must use a deletion policy appropriate to the environment: `upsert-only` retains records after a route is gone and requires separate DNS cleanup. This package does not silently change that shared controller policy.

See [lifecycle and reconciliation](docs/lifecycle.md) for the deletion dependency graph, readiness behavior and watch-event diagnosis.

## Development

Read `AGENTS.md` and the Hops `xrd-authoring` skill. Package layout follows the Hops XRD convention.

```sh
make render:all
make validate:all
make test
make build
```

Render/validation use `examples/platform.yaml` as an extra-resource fixture. Examples are serialized because `up` writes shared generated models in `.up`; pipeline failures propagate. CI uses the same Makefile rather than the older reusable validation workflow, which cannot pass extra-resource fixtures.

For source testing against an explicitly selected Hops local cluster:

```sh
hops local status --context kind-hops --json
hops config install --path . --context kind-hops \
  --cluster-provider kind --docker-provider dory
```

If the machine cluster has an active GitOps watcher, use its ownership handoff and retain the package pin plus ImageConfig rewrite in its local cluster tree before restoring it. Do not bypass an active owner. `local/` contains test resources, not production configuration. The local fixture uses a test CA/HTTP option to avoid requesting public certificates for localhost. Cloud VPN and authoritative DNS behavior still need cloud verification.

See [local validation](local/README.md) for the exact prerequisites and verification scope. Operational evidence belongs in the **Hops KB**, task `tasks/app-xr-private-exposure`.

## License

Apache-2.0.
