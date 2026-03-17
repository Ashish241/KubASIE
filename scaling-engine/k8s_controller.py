"""
Kubernetes HPA Controller — Dynamically patches HPA configuration.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger("scaling-engine.k8s")


class K8sController:
    """
    Manages Kubernetes HPA through the official Python client.

    Supports dry-run mode for safe testing.
    """

    def __init__(
        self,
        namespace: str = "autoscaler",
        deployment: str = "target-app",
        hpa_name: str = "target-app-hpa",
        dry_run: bool = False,
        in_cluster: bool = True,
    ):
        self.namespace = namespace
        self.deployment = deployment
        self.hpa_name = hpa_name
        self.dry_run = dry_run
        self.api = None

        try:
            from kubernetes import client, config as k8s_config

            if in_cluster:
                try:
                    k8s_config.load_incluster_config()
                except k8s_config.ConfigException:
                    k8s_config.load_kube_config()
            else:
                k8s_config.load_kube_config()

            self.api = client.AutoscalingV2Api()
            self.apps_api = client.AppsV1Api()
            logger.info("K8s client initialized (namespace=%s, dry_run=%s)", namespace, dry_run)

        except Exception as e:
            logger.warning("K8s client init failed (dry_run mode will be used): %s", e)
            self.dry_run = True

    def get_hpa_status(self) -> Optional[Dict]:
        """Get current HPA status."""
        if self.dry_run or self.api is None:
            return self._mock_hpa_status()

        try:
            hpa = self.api.read_namespaced_horizontal_pod_autoscaler(
                name=self.hpa_name,
                namespace=self.namespace,
            )
            return {
                "name": hpa.metadata.name,
                "min_replicas": hpa.spec.min_replicas,
                "max_replicas": hpa.spec.max_replicas,
                "current_replicas": hpa.status.current_replicas,
                "desired_replicas": hpa.status.desired_replicas,
                "conditions": [
                    {"type": c.type, "status": c.status, "reason": c.reason}
                    for c in (hpa.status.conditions or [])
                ],
            }
        except Exception as e:
            logger.error("Failed to get HPA status: %s", e)
            return self._mock_hpa_status()

    def patch_hpa(
        self,
        min_replicas: int = 1,
        max_replicas: int = 10,
        target_cpu: int = 50,
    ) -> bool:
        """
        Patch the HPA with new scaling parameters.

        Returns True if successful.
        """
        logger.info(
            "%s HPA %s: min=%d, max=%d, target_cpu=%d%%",
            "DRY-RUN:" if self.dry_run else "PATCHING",
            self.hpa_name,
            min_replicas,
            max_replicas,
            target_cpu,
        )

        if self.dry_run:
            logger.info("Dry-run mode — no changes applied to cluster.")
            return True

        if self.api is None:
            logger.error("No K8s API client available.")
            return False

        try:
            patch_body = {
                "spec": {
                    "minReplicas": min_replicas,
                    "maxReplicas": max_replicas,
                    "metrics": [
                        {
                            "type": "Resource",
                            "resource": {
                                "name": "cpu",
                                "target": {
                                    "type": "Utilization",
                                    "averageUtilization": target_cpu,
                                },
                            },
                        }
                    ],
                }
            }

            self.api.patch_namespaced_horizontal_pod_autoscaler(
                name=self.hpa_name,
                namespace=self.namespace,
                body=patch_body,
            )
            logger.info("✅ HPA patched successfully.")
            return True

        except Exception as e:
            logger.error("❌ Failed to patch HPA: %s", e)
            return False

    def get_deployment_status(self) -> Optional[Dict]:
        """Get current deployment status."""
        if self.dry_run or self.apps_api is None:
            return {"replicas": 2, "ready_replicas": 2, "available_replicas": 2}

        try:
            dep = self.apps_api.read_namespaced_deployment(
                name=self.deployment,
                namespace=self.namespace,
            )
            return {
                "replicas": dep.status.replicas,
                "ready_replicas": dep.status.ready_replicas,
                "available_replicas": dep.status.available_replicas,
                "updated_replicas": dep.status.updated_replicas,
            }
        except Exception as e:
            logger.error("Failed to get deployment status: %s", e)
            return None

    def _mock_hpa_status(self) -> Dict:
        """Return mock HPA status when K8s is unavailable."""
        return {
            "name": self.hpa_name,
            "min_replicas": 1,
            "max_replicas": 10,
            "current_replicas": 2,
            "desired_replicas": 2,
            "conditions": [],
        }
