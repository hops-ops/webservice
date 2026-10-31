# WebService configuration

Read the Hops xrd-authoring skill before changes. Follow its state, observed-resource, Usage, test and package conventions.
Avoid Upbound-hosted configuration packages; favor crossplane-contrib packages because Upbound packages can require paid accounts.
Target Crossplane 2+: namespaced XRD/MRs, managementPolicies, and providerConfigRef.kind. Never set managed-resource deletionPolicy.
Track intent and evidence in Hops KB tasks/app-xr-private-exposure. Do not use Harmony's KB for this package.
Local tests must use an explicit local context. Never run local fixtures against production.
