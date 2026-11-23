### What's changed in v0.3.0

* feat(auth): the Zitadel client names its Login V2 UI (#14) (by @patrickleet)

  feat(auth): the Zitadel client names its Login V2 UI

  The generated Oidc sets loginVersion.loginV2.baseUri to the platform's
  auth.loginBaseURI, or Zitadel's hosted Login V2 at <issuerURL>/ui/v2/login.
  Zitadel ignores per-app login UIs while the instance requires Login V2;
  once it does not, apps without one fall back to Login V1.


See full diff: [v0.2.0...v0.3.0](https://github.com/hops-ops/webservice/compare/v0.2.0...v0.3.0)
