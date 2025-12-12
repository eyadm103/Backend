# schwab_api/models.py
from django.db import models
from django.utils import timezone 
from .security import encrypt_token, decrypt_token # 🚨 نستورد دوال التشفير

class SchwabToken(models.Model):
    access_token = models.TextField(verbose_name="Encrypted Access Token")
    refresh_token = models.TextField(verbose_name="Encrypted Refresh Token")
    expires_in = models.IntegerField(verbose_name="Expires in seconds")
    acquisition_time = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-acquisition_time']

    @property
    def decrypted_access_token(self):
        return decrypt_token(self.access_token)

    @property
    def decrypted_refresh_token(self):
        return decrypt_token(self.refresh_token)

    @classmethod
    def create_or_update_from_data(cls, token_data):
        # تشفير التوكنات قبل الحفظ
        encrypted_access = encrypt_token(token_data.get("access_token", ""))
        encrypted_refresh = encrypt_token(token_data.get("refresh_token", ""))
        expires_in = token_data.get("expires_in", 3600)

        # إنشاء سجل جديد
        return cls.objects.create(
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            expires_in=expires_in,
            acquisition_time=timezone.now()
        )