from app.services.welfare import is_dark_coat, clamp100, infer_breed_groups
from app.services import welfare

def test_is_dark_coat():
    assert is_dark_coat("Black/White") is True
    assert is_dark_coat("Dark-Brown") is True
    assert is_dark_coat("White") is False
    assert is_dark_coat(None) is False

def test_clamp100():
    assert clamp100(-10) == 0
    assert clamp100(0) == 0
    assert clamp100(50) == 50
    assert clamp100(150) == 100

def test_infer_breed_groups_known(monkeypatch):
    monkeypatch.setattr(welfare, "BREED_GROUPS", {"Pug": ["Toy"]}, raising=True)
    groups = welfare.infer_breed_groups("Pug Mix")
    assert "Toy" in groups

def test_infer_breed_groups_unknown(monkeypatch):
    monkeypatch.setattr(welfare, "BREED_GROUPS", {"Border Collie": ["Herding"]}, raising=True)
    groups = welfare.infer_breed_groups("German Shepherd Mix")
    assert groups == []
