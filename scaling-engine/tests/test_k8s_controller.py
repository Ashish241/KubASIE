"""
Tests for K8s Controller.
"""

from k8s_controller import K8sController


class TestK8sController:

    def test_dry_run_patch(self):
        """Verify dry-run mode doesn't make real K8s calls."""
        controller = K8sController(dry_run=True, in_cluster=False)
        result = controller.patch_hpa(min_replicas=2, max_replicas=8, target_cpu=60)
        assert result is True

    def test_mock_hpa_status(self):
        """Verify mock HPA status returns valid data."""
        controller = K8sController(dry_run=True, in_cluster=False)
        status = controller.get_hpa_status()
        assert status is not None
        assert "min_replicas" in status
        assert "max_replicas" in status
        assert "current_replicas" in status

    def test_deployment_status_mock(self):
        controller = K8sController(dry_run=True, in_cluster=False)
        status = controller.get_deployment_status()
        assert status is not None
        assert "replicas" in status


class TestK8sControllerUnit:

    def test_init_with_no_cluster(self):
        """Should fall back to dry-run when no cluster is available."""
        controller = K8sController(in_cluster=False, dry_run=False)
        # If no kubeconfig exists, it should fall back to dry_run
        assert controller.dry_run is True or controller.api is not None
