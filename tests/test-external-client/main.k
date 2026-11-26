import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1

items = [metav1alpha1.CompositionTest {
    metadata.name = "external-client"
    spec = {
        compositionPath = "apis/webservices/composition.yaml"
        xrdPath = "apis/webservices/definition.yaml"
        timeoutSeconds = 120
        validate = False
        xr = {
            apiVersion = "workloads.hops.ops.com.ai/v1alpha1"
            kind = "WebService"
            metadata = {name = "echo", namespace = "preview-67"}
            spec = {
                image = "hashicorp/http-echo:1.0.0"
                auth = {
                    enabled = True
                    existingClient = {
                        clientSecretRef.name = "workforce-client"
                        cookieSecretRef.name = "workforce-session"
                    }
                }
            }
        }
        extraResources = [{
            apiVersion = "apiextensions.crossplane.io/v1beta1"
            kind = "EnvironmentConfig"
            metadata.name = "webservice-default"
            data = {
                baseDomain = "example.com"
                privateGateway = {namespace = "istio-ingress", service = "private.example.com"}
                auth = {
                    issuerURL = "https://auth.example.com"
                    allowedGroups = ["developer"]
                    requireExistingClient = True
                }
            }
        }]
        assertResources = [{
            apiVersion = "kubernetes.m.crossplane.io/v1alpha1"
            kind = "Object"
            metadata.name = "echo-service"
            spec.forProvider.manifest.spec.template.spec.containers = [{
                name = "login"
                env = [
                    {name = "OAUTH2_PROXY_CLIENT_ID", valueFrom.secretKeyRef = {name = "workforce-client", key = "client_id", optional = False}},
                    {name = "OAUTH2_PROXY_CLIENT_SECRET", valueFrom.secretKeyRef = {name = "workforce-client", key = "client_secret", optional = False}},
                    {name = "OAUTH2_PROXY_COOKIE_SECRET", valueFrom.secretKeyRef = {name = "workforce-session", key = "cookie_secret", optional = False}},
                ]
            }, {name = "app"}]
        }]
    }
}]
