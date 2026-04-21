"""Unit tests for the Device model."""
from datetime import datetime, timedelta

import pytest

from app.models import Device, DeviceDirectionMode, DeviceStatus


class TestDeviceBasics:
    def test_uuid_auto_generated(self, db, make_device):
        device, _ = make_device()
        assert device.device_uuid
        assert len(device.device_uuid) == 36  # UUID4 w/ dashes

    def test_name_unique_per_school(self, db, make_device, make_school):
        school = make_school()
        make_device(school=school, device_name="Gate A")
        db.session.commit()
        with pytest.raises(Exception):
            make_device(school=school, device_name="Gate A")
            db.session.commit()
        db.session.rollback()

    def test_invalid_direction(self, db, make_school):
        with pytest.raises(ValueError):
            d = Device(
                school_id=make_school().id,
                device_name="bad",
                direction_mode="sideways",
            )
            d.set_api_key()

    def test_invalid_pulse(self, db, make_school):
        d = Device(school_id=make_school().id, device_name="x")
        with pytest.raises(ValueError):
            d.turnstile_pulse_ms = 10


class TestDeviceAuth:
    def test_check_api_key(self, db, make_device):
        device, plain = make_device()
        assert device.check_api_key(plain)
        assert not device.check_api_key("wrong-key")

    def test_rotate_key_invalidates_old(self, db, make_device):
        device, old = make_device()
        new = device.set_api_key()
        assert new != old
        assert not device.check_api_key(old)
        assert device.check_api_key(new)

    def test_prefix_exposed(self, db, make_device):
        device, plain = make_device()
        assert device.api_key_prefix == plain[:12]


class TestDeviceStatus:
    def test_provisioning_when_no_heartbeat(self, db, make_device):
        device, _ = make_device()
        assert device.status == DeviceStatus.PROVISIONING.value

    def test_online_after_heartbeat(self, db, make_device):
        device, _ = make_device()
        device.touch_heartbeat(ip="1.2.3.4")
        assert device.status == DeviceStatus.ONLINE.value
        assert device.is_online()

    def test_offline_after_threshold(self, db, make_device):
        device, _ = make_device()
        device.touch_heartbeat()
        device.last_heartbeat_at = datetime.utcnow() - timedelta(minutes=5)
        assert not device.is_online(threshold_seconds=60)
        assert device.status == DeviceStatus.OFFLINE.value

    def test_disabled_when_inactive(self, db, make_device):
        device, _ = make_device()
        device.is_active = False
        assert device.status == DeviceStatus.DISABLED.value


class TestDeviceTelemetry:
    def test_heartbeat_records_stats(self, db, make_device):
        device, _ = make_device()
        device.touch_heartbeat(
            ip="192.168.1.10",
            firmware="0.1.0",
            stats={
                "cpu_percent": 12.3,
                "memory_percent": 45.6,
                "disk_percent": 7.8,
                "cpu_temp_c": 55.5,
                "uptime_seconds": 3600},
        )
        assert device.last_ip == "192.168.1.10"
        assert device.firmware_version == "0.1.0"
        assert device.cpu_percent == 12.3
        assert device.uptime_seconds == 3600

    def test_record_error(self, db, make_device):
        device, _ = make_device()
        device.record_error("camera disconnected")
        assert device.last_error == "camera disconnected"
        assert device.last_error_at is not None