from src.gpu_lease import GpuLeaseManager


def test_gpu_lease_acquire_release_idempotent():
    lease = GpuLeaseManager()

    acquired = lease.acquire("req-1", reason="teleport")

    assert acquired.acquired is True
    assert acquired.reason == "acquired"
    assert acquired.handle is not None
    assert lease.status().owner == "req-1"

    assert acquired.handle.release() is True
    assert acquired.handle.release() is False
    assert lease.status().acquired is False


def test_gpu_lease_rejects_second_owner_without_wait():
    lease = GpuLeaseManager()
    first = lease.acquire("req-1")
    assert first.acquired is True

    second = lease.acquire("req-2")

    assert second.acquired is False
    assert second.reason == "occupied"
    assert second.owner == "req-1"


def test_gpu_lease_context_manager_releases_on_exit():
    lease = GpuLeaseManager()
    acquired = lease.acquire("req-1")
    assert acquired.handle is not None

    with acquired.handle:
        assert lease.status().acquired is True

    assert lease.status().acquired is False


def test_gpu_lease_cancelled_wait_returns_without_acquiring():
    lease = GpuLeaseManager()
    first = lease.acquire("req-1")
    assert first.acquired is True

    second = lease.acquire("req-2", wait=True, timeout_s=1.0, cancel_check=lambda: True)

    assert second.acquired is False
    assert second.reason == "cancelled"
    assert lease.status().owner == "req-1"
