# Reconciliation and deletion dependencies

WebService renders a stable set of managed resources for the selected exposure,
authentication and TLS options. Resource readiness changes status and deletion
locks; a temporary readiness failure does not remove workload or credential
resources from the desired set.

## Deletion ordering

Each Usage protects an `of` resource until its `by` resource is deleted. Arrows
below mean **delete first → delete afterward**. These are managed-resource keys;
most represent provider-kubernetes Objects managing the corresponding native
resources. `oidc` is the identity-provider managed resource.

| Delete first (`by`) | Protected dependency (`of`) | Purpose |
| --- | --- | --- |
| `route` | `gateway`, `backend-grant`, `service` | Withdraw the private route and its DNS source before dismantling the path it exposes. |
| `gateway` | `certificate`, `tls-grant` | Keep TLS issuance and cross-namespace Secret permission available while the gateway exists. |
| `certificate` | `tls-secret` | Stop the certificate producer before deleting its generated Secret, avoiding recreation after cleanup. |
| `service` | `client-secret`, `cookie`, optional `issuer-ca` | Keep login credentials and trust material available until the workload is gone. |
| `client-secret` | `oidc` | Retain the connection-secret producer while its credential bridge exists. |
| `cookie` | `cookie-generator` | Retain the generator while the ExternalSecret consuming it exists. |

Private TLS with authentication and a custom issuer CA has 11 direct edges.
Public authentication without a custom CA has four; private HTTP without auth
has three; an unauthenticated cluster-only service has none.

There is no total deletion order. Identity registration, cookie generation and
TLS issuance are independent branches. Transitive protection already preserves
the OIDC client behind the workload and the TLS Secret behind the gateway; extra
direct locks between those same resources are unnecessary.

All Usage names are deterministic and `replayDeletion` is enabled so a blocked
deletion can be retried when its dependent disappears. Usages are established
after both endpoints become ready. A readiness dip can remove a Usage, but does
not un-render either managed resource. Failed-bootstrap cleanup must also work
when a resource never becomes ready and never acquires a lock.

The XR does not take ownership of shared providers, platform gateways, namespace
lifetimes or developer-supplied Secrets. Public Knative certificates follow the
platform's certificate-controller ownership policy. ExternalDNS cleanup follows
the operator's registry and synchronization policy. Those shared policies are
separate from these per-service deletion locks.

## Watch-event warnings

`Ready` describes resource readiness; `Responsive` describes Crossplane's watch
circuit breaker. A ready workload can coexist with `Responsive=False` while
Crossplane throttles events. Inspect the resource named in the condition message
and measure its modifications before changing a composition or controller limit.

Crossplane has an [upstream stale-condition write issue](https://github.com/crossplane/crossplane/issues/7062)
and an [open status-write fix](https://github.com/crossplane/crossplane/pull/7658).
In local testing on Crossplane 2.4.0, a cluster-only WebService with no Usages
repeatedly alternated the standard Ready condition at one generation while the
rendered `status.ready` and ready revision remained unchanged. It subsequently
settled. This matches the upstream issue; it does not demonstrate a Usage loop.

The render function outputs observed URL, revision and readiness fields, not
Crossplane's system conditions. Do not work around stale system conditions by
forcing them in a function, ignoring genuine readiness failures or increasing
circuit-breaker thresholds. An upstream fix needs a release or an independently
reviewed control-plane change; a WebService package release alone cannot patch
the Crossplane controller.

## Verification

`make check-lifecycle` renders bootstrap, ready and unready observations. It
checks the exact applicable dependency graph, endpoint kinds, replay behavior,
absence of cycles, stable repeated output and retention of managed resources
during readiness failures. `make validate:all` includes this check.

Local lifecycle tests must delete the XR while retaining its namespace and
credential providers, then verify managed resources, native workload, routing,
grants, generated Secrets and TLS assets disappear. Only afterward delete the
test identity project and namespace. Namespace deletion alone can hide orphaned
native resources and is not evidence of correct XR cleanup. Test both a fully
ready authenticated TLS service and failed authentication bootstrap.
