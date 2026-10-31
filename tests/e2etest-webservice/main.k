import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1

items = [metav1alpha1.E2ETest {
  "metadata": {
    "name": "webservice-cluster-lifecycle"
  },
  "spec": {
    "crossplane": {
      "autoUpgrade": {
        "channel": "Rapid"
      }
    },
    "defaultConditions": [
      "Ready"
    ],
    "timeoutSeconds": 1800,
    "cleanupTimeoutSeconds": 1200,
    "skipDelete": False,
    "initResources": [
      {
        "apiVersion": "pkg.crossplane.io/v1",
        "kind": "Configuration",
        "metadata": {
          "name": "hops-ops-gateway-api-stack"
        },
        "spec": {
          "package": "ghcr.io/hops-ops/gateway-api-stack:v0.4.1"
        }
      },
      {
        "apiVersion": "pkg.crossplane.io/v1",
        "kind": "Configuration",
        "metadata": {
          "name": "hops-ops-istio-stack"
        },
        "spec": {
          "package": "ghcr.io/hops-ops/istio-stack:v1.4.1"
        }
      },
      {
        "apiVersion": "pkg.crossplane.io/v1",
        "kind": "Configuration",
        "metadata": {
          "name": "hops-ops-knative-stack"
        },
        "spec": {
          "package": "ghcr.io/hops-ops/knative-stack:v1.7.0"
        }
      }
    ],
    "extraResources": [
      {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "ClusterRoleBinding",
        "metadata": {
          "name": "webservice-e2e-providers"
        },
        "roleRef": {
          "apiGroup": "rbac.authorization.k8s.io",
          "kind": "ClusterRole",
          "name": "cluster-admin"
        },
        "subjects": [
          {
            "kind": "Group",
            "name": "system:serviceaccounts:crossplane-system",
            "apiGroup": "rbac.authorization.k8s.io"
          }
        ]
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1beta1",
        "kind": "ClusterProviderConfig",
        "metadata": {
          "name": "default"
        },
        "spec": {
          "credentials": {
            "source": "InjectedIdentity"
          }
        }
      },
      {
        "apiVersion": "helm.m.crossplane.io/v1beta1",
        "kind": "ClusterProviderConfig",
        "metadata": {
          "name": "default"
        },
        "spec": {
          "credentials": {
            "source": "InjectedIdentity"
          }
        }
      },
      {
        "apiVersion": "apiextensions.crossplane.io/v1beta1",
        "kind": "EnvironmentConfig",
        "metadata": {
          "name": "webservice-e2e"
        },
        "data": {
          "providerConfigRef": {
            "name": "default",
            "kind": "ClusterProviderConfig"
          }
        }
      }
    ],
    "manifests": [
      {
        "apiVersion": "hops.ops.com.ai/v1alpha1",
        "kind": "GatewayAPIStack",
        "metadata": {
          "name": "e2e",
          "namespace": "default"
        },
        "spec": {
          "clusterName": "default"
        }
      },
      {
        "apiVersion": "hops.ops.com.ai/v1alpha1",
        "kind": "IstioStack",
        "metadata": {
          "name": "e2e",
          "namespace": "default"
        },
        "spec": {
          "clusterName": "default"
        }
      },
      {
        "apiVersion": "hops.ops.com.ai/v1alpha1",
        "kind": "KnativeStack",
        "metadata": {
          "name": "e2e",
          "namespace": "default"
        },
        "spec": {
          "clusterName": "default",
          "nats": {
            "enabled": False
          },
          "knativeEventing": {
            "enabled": False
          },
          "knativeServing": {
            "spec": {
              "config": {
                "features": {
                  "kubernetes.podspec-securitycontext": "enabled"
                }
              }
            }
          }
        }
      },
      {
        "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
        "kind": "WebService",
        "metadata": {
          "name": "webservice-e2e",
          "namespace": "default"
        },
        "spec": {
          "image": "hashicorp/http-echo:1.0.0",
          "port": 5678,
          "args": [
            "-text=webservice-e2e"
          ],
          "exposure": "cluster",
          "platformRef": {
            "name": "e2e"
          },
          "podTemplate": {
            "securityContext": {
              "runAsUser": 65532
            }
          }
        }
      }
    ]
  }
}]
