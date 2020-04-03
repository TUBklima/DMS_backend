# test_models.py

import pytest
from mixer.backend.django import mixer
pytestmark = pytest.mark.django_db


class TestUC2Observation:
    def test_model(self):
        obj = mixer.blend('data.UC2Observation')
        assert obj.pk == 1, 'Should save an instance'
