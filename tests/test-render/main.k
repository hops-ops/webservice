import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1

_platform = {
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

items = [
metav1alpha1.CompositionTest {
  "metadata": {
    "name": "private-default"
  },
  "spec": {
    "compositionPath": "apis/webservices/composition.yaml",
    "xrdPath": "apis/webservices/definition.yaml",
    "timeoutSeconds": 90,
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
      _platform
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
    "timeoutSeconds": 90,
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
      _platform
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
    "timeoutSeconds": 90,
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
      _platform
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
    "timeoutSeconds": 90,
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
      _platform
    ],
    "observedResources": [],
    "assertResources": [
      {
        "apiVersion": "application.zitadel.m.crossplane.io/v1alpha1",
        "kind": "Oidc",
        "metadata": {"name": "echo-oidc"},
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
          "name": "echo-service"
        },
        "spec": {
          "forProvider": {
            "manifest": {
              "spec": {"template": {"spec": {"containers": [
                {"name": "login", "ports": [{"name": "http1", "containerPort": 4180}]},
                {"name": "app", "env": [{"name": "PORT", "value": "5678"}]}
              ]}}}
            }
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
    "timeoutSeconds": 90,
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
      _platform
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
    "timeoutSeconds": 90,
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
      _platform
    ],
    "observedResources": [
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-service",
          "namespace": "preview-67",
          "annotations": {
            "crossplane.io/composition-resource-name": "service"
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
              "apiVersion": "serving.knative.dev/v1",
              "kind": "Service",
              "metadata": {
                "name": "echo",
                "namespace": "preview-67",
                "uid": "fixture-service"
              },
              "status": {
                "url": "http://echo.preview-67.svc.cluster.local",
                "latestReadyRevisionName": "echo-00001"
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-route",
          "namespace": "preview-67",
          "annotations": {
            "crossplane.io/composition-resource-name": "route"
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
              "apiVersion": "gateway.networking.k8s.io/v1",
              "kind": "HTTPRoute",
              "metadata": {
                "name": "echo-private",
                "namespace": "preview-67",
                "uid": "fixture-route"
              },
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
          "name": "echo-gateway",
          "namespace": "preview-67",
          "annotations": {
            "crossplane.io/composition-resource-name": "gateway"
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
              "apiVersion": "gateway.networking.k8s.io/v1",
              "kind": "Gateway",
              "metadata": {
                "name": "echo-preview-67",
                "namespace": "preview-67",
                "uid": "fixture-gateway"
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
          "namespace": "preview-67",
          "annotations": {
            "crossplane.io/composition-resource-name": "backend-grant"
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
              "apiVersion": "gateway.networking.k8s.io/v1beta1",
              "kind": "ReferenceGrant",
              "metadata": {
                "name": "echo-preview-67",
                "namespace": "preview-67",
                "uid": "fixture-backend-grant"
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
          "namespace": "preview-67",
          "annotations": {
            "crossplane.io/composition-resource-name": "certificate"
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
              "apiVersion": "networking.internal.knative.dev/v1alpha1",
              "kind": "Certificate",
              "metadata": {
                "name": "echo-tls",
                "namespace": "preview-67",
                "uid": "fixture-certificate"
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
          "namespace": "preview-67",
          "annotations": {
            "crossplane.io/composition-resource-name": "tls-grant"
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
              "apiVersion": "gateway.networking.k8s.io/v1beta1",
              "kind": "ReferenceGrant",
              "metadata": {
                "name": "echo-tls",
                "namespace": "preview-67",
                "uid": "fixture-tls-grant"
              }
            }
          }
        }
      },
      {
        "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
        "kind": "Object",
        "metadata": {
          "name": "echo-tls-secret",
          "namespace": "preview-67",
          "annotations": {
            "crossplane.io/composition-resource-name": "tls-secret"
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
              "kind": "Secret",
              "metadata": {
                "name": "echo-tls",
                "namespace": "preview-67",
                "uid": "fixture-tls-secret"
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
