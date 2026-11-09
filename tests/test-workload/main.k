import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1

items = [metav1alpha1.CompositionTest {**test} for test in [
  {
    "apiVersion": "meta.dev.upbound.io/v1alpha1",
    "kind": "CompositionTest",
    "metadata": {
      "name": "mounted-auth-false"
    },
    "spec": {
      "compositionPath": "apis/webservices/composition.yaml",
      "xrdPath": "apis/webservices/definition.yaml",
      "timeoutSeconds": 120,
      "validate": False,
      "xr": {
        "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
        "kind": "WebService",
        "metadata": {
          "name": "collector",
          "namespace": "staging"
        },
        "spec": {
          "image": "example/collector:v1",
          "port": 8080,
          "exposure": "private",
          "hostname": "legacy-collector.example.com",
          "auth": {
            "enabled": False
          },
          "scaling": {
            "minReplicas": 1,
            "maxReplicas": 1
          },
          "volumeMounts": [
            {
              "name": "credentials",
              "mountPath": "/var/run/collector",
              "readOnly": True
            }
          ],
          "securityContext": {
            "readOnlyRootFilesystem": True
          },
          "sidecars": [
            {
              "name": "worker",
              "image": "example/worker:v1",
              "volumeMounts": [
                {
                  "name": "scratch",
                  "mountPath": "/tmp"
                }
              ]
            }
          ],
          "podTemplate": {
            "volumes": [
              {
                "name": "credentials",
                "secret": {
                  "secretName": "collector-credentials"
                }
              },
              {
                "name": "scratch",
                "emptyDir": {}
              }
            ]
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
            "privateGateway": {
              "namespace": "istio-ingress",
              "service": "private.example.com"
            },
            "auth": {
              "issuerURL": "https://auth.example.com",
              "projectId": "fixture",
              "allowedGroups": [
                "developer"
              ],
              "caBundle": "test-public-ca"
            }
          }
        }
      ],
      "assertResources": [
        {
          "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
          "kind": "Object",
          "metadata": {
            "name": "collector-service"
          },
          "spec": {
            "forProvider": {
              "manifest": {
                "spec": {
                  "template": {
                    "metadata": {
                      "annotations": {
                        "autoscaling.knative.dev/min-scale": "1",
                        "autoscaling.knative.dev/max-scale": "1"
                      }
                    },
                    "spec": {
                      "containers": [
                        {
                          "name": "app",
                          "volumeMounts": [
                            {
                              "name": "credentials",
                              "mountPath": "/var/run/collector",
                              "readOnly": True
                            }
                          ],
                          "securityContext": {
                            "readOnlyRootFilesystem": True,
                            "allowPrivilegeEscalation": False,
                            "capabilities": {
                              "drop": [
                                "ALL"
                              ]
                            }
                          }
                        },
                        {
                          "name": "worker",
                          "image": "example/worker:v1",
                          "volumeMounts": [
                            {
                              "name": "scratch",
                              "mountPath": "/tmp"
                            }
                          ]
                        }
                      ]
                    }
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
            "name": "collector-route"
          },
          "spec": {
            "forProvider": {
              "manifest": {
                "spec": {
                  "hostnames": [
                    "legacy-collector.example.com"
                  ]
                }
              }
            }
          }
        }
      ]
    }
  },
  {
    "apiVersion": "meta.dev.upbound.io/v1alpha1",
    "kind": "CompositionTest",
    "metadata": {
      "name": "mounted-auth-true"
    },
    "spec": {
      "compositionPath": "apis/webservices/composition.yaml",
      "xrdPath": "apis/webservices/definition.yaml",
      "timeoutSeconds": 120,
      "validate": False,
      "xr": {
        "apiVersion": "workloads.hops.ops.com.ai/v1alpha1",
        "kind": "WebService",
        "metadata": {
          "name": "collector",
          "namespace": "staging"
        },
        "spec": {
          "image": "example/collector:v1",
          "port": 8080,
          "exposure": "private",
          "hostname": "legacy-collector.example.com",
          "auth": {
            "enabled": True
          },
          "scaling": {
            "minReplicas": 1,
            "maxReplicas": 1
          },
          "volumeMounts": [
            {
              "name": "credentials",
              "mountPath": "/var/run/collector",
              "readOnly": True
            }
          ],
          "securityContext": {
            "readOnlyRootFilesystem": True
          },
          "sidecars": [
            {
              "name": "worker",
              "image": "example/worker:v1",
              "volumeMounts": [
                {
                  "name": "scratch",
                  "mountPath": "/tmp"
                }
              ]
            }
          ],
          "podTemplate": {
            "volumes": [
              {
                "name": "credentials",
                "secret": {
                  "secretName": "collector-credentials"
                }
              },
              {
                "name": "scratch",
                "emptyDir": {}
              }
            ]
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
            "privateGateway": {
              "namespace": "istio-ingress",
              "service": "private.example.com"
            },
            "auth": {
              "issuerURL": "https://auth.example.com",
              "projectId": "fixture",
              "allowedGroups": [
                "developer"
              ],
              "caBundle": "test-public-ca"
            }
          }
        }
      ],
      "assertResources": [
        {
          "apiVersion": "kubernetes.m.crossplane.io/v1alpha1",
          "kind": "Object",
          "metadata": {
            "name": "collector-service"
          },
          "spec": {
            "forProvider": {
              "manifest": {
                "spec": {
                  "template": {
                    "metadata": {
                      "annotations": {
                        "autoscaling.knative.dev/min-scale": "1",
                        "autoscaling.knative.dev/max-scale": "1"
                      }
                    },
                    "spec": {
                      "containers": [
                        {
                          "name": "login"
                        },
                        {
                          "name": "app",
                          "volumeMounts": [
                            {
                              "name": "credentials",
                              "mountPath": "/var/run/collector",
                              "readOnly": True
                            }
                          ],
                          "securityContext": {
                            "readOnlyRootFilesystem": True,
                            "allowPrivilegeEscalation": False,
                            "capabilities": {
                              "drop": [
                                "ALL"
                              ]
                            }
                          }
                        },
                        {
                          "name": "worker",
                          "image": "example/worker:v1",
                          "volumeMounts": [
                            {
                              "name": "scratch",
                              "mountPath": "/tmp"
                            }
                          ]
                        }
                      ]
                    }
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
            "name": "collector-route"
          },
          "spec": {
            "forProvider": {
              "manifest": {
                "spec": {
                  "hostnames": [
                    "legacy-collector.example.com"
                  ]
                }
              }
            }
          }
        }
      ]
    }
  }
]]
