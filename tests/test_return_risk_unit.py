from app.services.return_risk import is_dark_coat, clamp100

def test_is_dark_coat():
    assert is_dark_coat("Black/Gray") is True
    assert is_dark_coat("Dark-Brown") is True
    assert is_dark_coat("White") is False
    assert is_dark_coat(None) is False

def test_clamp100():
    assert clamp100(-5) == 0
    assert clamp100(0) == 0
    assert clamp100(100) == 100
    assert clamp100(101) == 100