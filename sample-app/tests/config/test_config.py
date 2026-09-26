from shop.config import get_settings


def test_get_settings_defaults():
    settings = get_settings()
    assert settings.sender == "shop@example.com"
    assert settings.smtp_host == "localhost"
