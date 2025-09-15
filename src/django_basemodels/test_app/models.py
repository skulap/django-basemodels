from django.db import models
from django_basemodels.models import BaseModel


class TestBaseModel(BaseModel):
    # добавим небольшое поле чтобы отличать
    title = models.CharField(max_length=255, default='test')

    class Meta:
        app_label = 'django_basemodels_tests'
