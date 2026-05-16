from app.core.fingerprint import fingerprint_device
def test_returns_fingerprint():
    fp = fingerprint_device("192.168.1.10", "aa:bb:cc:dd:ee:ff")
    assert hasattr(fp, "vendor")
