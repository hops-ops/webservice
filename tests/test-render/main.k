import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1

items = [
metav1alpha1.CompositionTest {
  "metadata": {
    "name": "private-default"
  },
  "spec": {
    "compositionPath": "apis/webservices/composition.yaml",
    "xrdPath": "apis/webservices/definition.yaml",
    "timeoutSeconds": 10,
    "validate": False,
    "xr": {
      "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
      "kind": "WebService",
      "metadata": {
        "name": "echo",
        "namespace": "preview-67"
      },
      "spec": {
        "image": "hashicorp/http-echo:1.0.0",
        "port": 5678
      }
    },
    "extraResources": [
      {
        "apiVersion": "apiextensions.crossplane.io/v1beta1",
        "kind": "EnvironmentConfig",
        "metadata": {
          "name": "webservice-default"
        },
        "data": {
          "baseDomain": "example.com",
          "providerConfigRef": {
            "name": "default",
            "kind": "ClusterProviderConfig"
          },
          "privateGateway": {
            "namespace": "istio-ingress",
            "service": "private-preview-istio.istio-ingress.svc.cluster.local"
          },
          "knativeLocalGateway": {
            "name": "knative-local-gateway-istio",
            "namespace": "knative-serving",
            "port": 80
          },
          "auth": {
            "issuerURL": "https://auth.example.com",
            "projectId": "example-project",
            "allowedGroups": [
              "platform.developer"
            ],
            "providerConfigRef": {
              "name": "default",
              "kind": "ClusterProviderConfig"
            }
          }
        }
      }
    ],
    "observedResources": [],
    "assertResources": [
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-service"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "metadata": {
                "labels": {
                  "networking.knative.dev/visibility": "cluster-local"
                },
                "annotations": {
                  "external-dns.alpha.kubernetes.io/cloudflare-proxied": "false"
                }
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-route"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "spec": {
                "hostnames": [
                  "echo.preview-67.example.com"
                ]
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-gateway"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "spec": {
                "addresses": [
                  {
                    "type": "Hostname",
                    "value": "private-preview-istio.istio-ingress.svc.cluster.local"
                  }
                ]
              }
            }
          }
        }
      }
    ]
  }
},
metav1alpha1.CompositionTest {
  "metadata": {
    "name": "cluster-endpoint"
  },
  "spec": {
    "compositionPath": "apis/webservices/composition.yaml",
    "xrdPath": "apis/webservices/definition.yaml",
    "timeoutSeconds": 10,
    "validate": False,
    "xr": {
      "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
      "kind": "WebService",
      "metadata": {
        "name": "echo",
        "namespace": "preview-67"
      },
      "spec": {
        "image": "hashicorp/http-echo:1.0.0",
        "port": 5678,
        "exposure": "cluster"
      }
    },
    "extraResources": [
      {
        "apiVersion": "apiextensions.crossplane.io/v1beta1",
        "kind": "EnvironmentConfig",
        "metadata": {
          "name": "webservice-default"
        },
        "data": {
          "baseDomain": "example.com",
          "providerConfigRef": {
            "name": "default",
            "kind": "ClusterProviderConfig"
          },
          "privateGateway": {
            "namespace": "istio-ingress",
            "service": "private-preview-istio.istio-ingress.svc.cluster.local"
          },
          "knativeLocalGateway": {
            "name": "knative-local-gateway-istio",
            "namespace": "knative-serving",
            "port": 80
          },
          "auth": {
            "issuerURL": "https://auth.example.com",
            "projectId": "example-project",
            "allowedGroups": [
              "platform.developer"
            ],
            "providerConfigRef": {
              "name": "default",
              "kind": "ClusterProviderConfig"
            }
          }
        }
      }
    ],
    "observedResources": [],
    "assertResources": [
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-service"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "metadata": {
                "labels": {
                  "networking.knative.dev/visibility": "cluster-local"
                }
              }
            }
          }
        }
      }
    ]
  }
},
metav1alpha1.CompositionTest {
  "metadata": {
    "name": "public-dns-only"
  },
  "spec": {
    "compositionPath": "apis/webservices/composition.yaml",
    "xrdPath": "apis/webservices/definition.yaml",
    "timeoutSeconds": 10,
    "validate": False,
    "xr": {
      "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
      "kind": "WebService",
      "metadata": {
        "name": "echo",
        "namespace": "preview-67"
      },
      "spec": {
        "image": "hashicorp/http-echo:1.0.0",
        "port": 5678,
        "exposure": "public"
      }
    },
    "extraResources": [
      {
        "apiVersion": "apiextensions.crossplane.io/v1beta1",
        "kind": "EnvironmentConfig",
        "metadata": {
          "name": "webservice-default"
        },
        "data": {
          "baseDomain": "example.com",
          "providerConfigRef": {
            "name": "default",
            "kind": "ClusterProviderConfig"
          },
          "privateGateway": {
            "namespace": "istio-ingress",
            "service": "private-preview-istio.istio-ingress.svc.cluster.local"
          },
          "knativeLocalGateway": {
            "name": "knative-local-gateway-istio",
            "namespace": "knative-serving",
            "port": 80
          },
          "auth": {
            "issuerURL": "https://auth.example.com",
            "projectId": "example-project",
            "allowedGroups": [
              "platform.developer"
            ],
            "providerConfigRef": {
              "name": "default",
              "kind": "ClusterProviderConfig"
            }
          }
        }
      }
    ],
    "observedResources": [],
    "assertResources": [
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-service"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "metadata": {
                "annotations": {
                  "external-dns.alpha.kubernetes.io/cloudflare-proxied": "false"
                }
              }
            }
          }
        }
      }
    ]
  }
},
metav1alpha1.CompositionTest {
  "metadata": {
    "name": "auth-switch"
  },
  "spec": {
    "compositionPath": "apis/webservices/composition.yaml",
    "xrdPath": "apis/webservices/definition.yaml",
    "timeoutSeconds": 10,
    "validate": False,
    "xr": {
      "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
      "kind": "WebService",
      "metadata": {
        "name": "echo",
        "namespace": "preview-67"
      },
      "spec": {
        "image": "hashicorp/http-echo:1.0.0",
        "port": 5678,
        "auth": {
          "enabled": True
        }
      }
    },
    "extraResources": [
      {
        "apiVersion": "apiextensions.crossplane.io/v1beta1",
        "kind": "EnvironmentConfig",
        "metadata": {
          "name": "webservice-default"
        },
        "data": {
          "baseDomain": "example.com",
          "providerConfigRef": {
            "name": "default",
            "kind": "ClusterProviderConfig"
          },
          "privateGateway": {
            "namespace": "istio-ingress",
            "service": "private-preview-istio.istio-ingress.svc.cluster.local"
          },
          "knativeLocalGateway": {
            "name": "knative-local-gateway-istio",
            "namespace": "knative-serving",
            "port": 80
          },
          "auth": {
            "issuerURL": "https://auth.example.com",
            "projectId": "example-project",
            "allowedGroups": [
              "platform.developer"
            ],
            "providerConfigRef": {
              "name": "default",
              "kind": "ClusterProviderConfig"
            }
          }
        }
      }
    ],
    "observedResources": [],
    "assertResources": [
      {
        "apiVersion": "application.zitadel.m.crossplane.io/v1alpha1",
        "kind": "Oidc",
        "spec": {
          "forProvider": {
            "redirectUris": [
              "https://echo.preview-67.example.com/oauth2/callback"
            ]
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-client-secret"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "type": "Opaque"
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-cookie"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "spec": {
                "refreshPolicy": "CreatedOnce",
                "target": {
                  "creationPolicy": "Owner"
                }
              }
            }
          }
        }
      }
    ]
  }
},
metav1alpha1.CompositionTest {
  "metadata": {
    "name": "settings-and-labels"
  },
  "spec": {
    "compositionPath": "apis/webservices/composition.yaml",
    "xrdPath": "apis/webservices/definition.yaml",
    "timeoutSeconds": 10,
    "validate": False,
    "xr": {
      "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
      "kind": "WebService",
      "metadata": {
        "name": "echo",
        "namespace": "preview-67"
      },
      "spec": {
        "image": "hashicorp/http-echo:1.0.0",
        "port": 5678,
        "exposure": "cluster",
        "labels": {
          "team": "platform"
        },
        "scaling": {
          "minReplicas": 1,
          "maxReplicas": 5
        },
        "env": [
          {
            "name": "LOG_LEVEL",
            "value": "info"
          }
        ]
      }
    },
    "extraResources": [
      {
        "apiVersion": "apiextensions.crossplane.io/v1beta1",
        "kind": "EnvironmentConfig",
        "metadata": {
          "name": "webservice-default"
        },
        "data": {
          "baseDomain": "example.com",
          "providerConfigRef": {
            "name": "default",
            "kind": "ClusterProviderConfig"
          },
          "privateGateway": {
            "namespace": "istio-ingress",
            "service": "private-preview-istio.istio-ingress.svc.cluster.local"
          },
          "knativeLocalGateway": {
            "name": "knative-local-gateway-istio",
            "namespace": "knative-serving",
            "port": 80
          },
          "auth": {
            "issuerURL": "https://auth.example.com",
            "projectId": "example-project",
            "allowedGroups": [
              "platform.developer"
            ],
            "providerConfigRef": {
              "name": "default",
              "kind": "ClusterProviderConfig"
            }
          }
        }
      }
    ],
    "observedResources": [],
    "assertResources": [
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-service"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "metadata": {
                "labels": {
                  "team": "platform"
                }
              },
              "spec": {
                "template": {
                  "metadata": {
                    "annotations": {
                      "autoscaling.knative.dev/min-scale": "1",
                      "autoscaling.knative.dev/max-scale": "5"
                    }
                  }
                }
              }
            }
          }
        }
      }
    ]
  }
},
metav1alpha1.CompositionTest {
  "metadata": {
    "name": "dependency-usages"
  },
  "spec": {
    "compositionPath": "apis/webservices/composition.yaml",
    "xrdPath": "apis/webservices/definition.yaml",
    "timeoutSeconds": 10,
    "validate": False,
    "xr": {
      "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
      "kind": "WebService",
      "metadata": {
        "name": "echo",
        "namespace": "preview-67"
      },
      "spec": {
        "image": "hashicorp/http-echo:1.0.0",
        "port": 5678
      }
    },
    "extraResources": [
      {
        "apiVersion": "apiextensions.crossplane.io/v1beta1",
        "kind": "EnvironmentConfig",
        "metadata": {
          "name": "webservice-default"
        },
        "data": {
          "baseDomain": "example.com",
          "providerConfigRef": {
            "name": "default",
            "kind": "ClusterProviderConfig"
          },
          "privateGateway": {
            "namespace": "istio-ingress",
            "service": "private-preview-istio.istio-ingress.svc.cluster.local"
          },
          "knativeLocalGateway": {
            "name": "knative-local-gateway-istio",
            "namespace": "knative-serving",
            "port": 80
          },
          "auth": {
            "issuerURL": "https://auth.example.com",
            "projectId": "example-project",
            "allowedGroups": [
              "platform.developer"
            ],
            "providerConfigRef": {
              "name": "default",
              "kind": "ClusterProviderConfig"
            }
          }
        }
      }
    ],
    "observedResources": [
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-route",
          "annotations": {
            "crossplane.io/composition-resource-name": "route",
            "gotemplating.fn.crossplane.io/composition-resource-name": "route"
          }
        },
        "status": {
          "conditions": [
            {
              "type": "Ready",
              "status": "True"
            }
          ],
          "atProvider": {
            "manifest": {
              "apiVersion": "v1",
              "kind": "ConfigMap",
              "metadata": {
                "name": "fixture",
                "uid": "test-uid"
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-gateway",
          "annotations": {
            "crossplane.io/composition-resource-name": "gateway",
            "gotemplating.fn.crossplane.io/composition-resource-name": "gateway"
          }
        },
        "status": {
          "conditions": [
            {
              "type": "Ready",
              "status": "True"
            }
          ],
          "atProvider": {
            "manifest": {
              "apiVersion": "v1",
              "kind": "ConfigMap",
              "metadata": {
                "name": "fixture",
                "uid": "test-uid"
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-service",
          "annotations": {
            "crossplane.io/composition-resource-name": "service",
            "gotemplating.fn.crossplane.io/composition-resource-name": "service"
          }
        },
        "status": {
          "conditions": [
            {
              "type": "Ready",
              "status": "True"
            }
          ],
          "atProvider": {
            "manifest": {
              "apiVersion": "v1",
              "kind": "ConfigMap",
              "metadata": {
                "name": "fixture",
                "uid": "test-uid"
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-backend-grant",
          "annotations": {
            "crossplane.io/composition-resource-name": "backend-grant",
            "gotemplating.fn.crossplane.io/composition-resource-name": "backend-grant"
          }
        },
        "status": {
          "conditions": [
            {
              "type": "Ready",
              "status": "True"
            }
          ],
          "atProvider": {
            "manifest": {
              "apiVersion": "v1",
              "kind": "ConfigMap",
              "metadata": {
                "name": "fixture",
                "uid": "test-uid"
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-certificate",
          "annotations": {
            "crossplane.io/composition-resource-name": "certificate",
            "gotemplating.fn.crossplane.io/composition-resource-name": "certificate"
          }
        },
        "status": {
          "conditions": [
            {
              "type": "Ready",
              "status": "True"
            }
          ],
          "atProvider": {
            "manifest": {
              "apiVersion": "v1",
              "kind": "ConfigMap",
              "metadata": {
                "name": "fixture",
                "uid": "test-uid"
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-tls-grant",
          "annotations": {
            "crossplane.io/composition-resource-name": "tls-grant",
            "gotemplating.fn.crossplane.io/composition-resource-name": "tls-grant"
          }
        },
        "status": {
          "conditions": [
            {
              "type": "Ready",
              "status": "True"
            }
          ],
          "atProvider": {
            "manifest": {
              "apiVersion": "v1",
              "kind": "ConfigMap",
              "metadata": {
                "name": "fixture",
                "uid": "test-uid"
              }
            }
          }
        }
      }
    ],
    "assertResources": [
      {
        "apiVersion": "protection.crossplane.io/v1beta1",
        "kind": "Usage",
        "metadata": {
          "name": "echo-delete-route-before-gateway"
        },
        "spec": {
          "replayDeletion": True
        }
      }
    ]
  }
}
]
