from app import db


class AppSetting(db.Model):
    __tablename__ = 'app_settings'
    key = db.Column(db.String(128), primary_key=True)
    value = db.Column(db.String(512), nullable=True)

    def __repr__(self):
        return f'<AppSetting {self.key}={self.value}>'

    @staticmethod
    def get_bool(key, default=False):
        s = AppSetting.query.get(key)
        if not s or s.value is None:
            return default
        return s.value.lower() in ('1', 'true', 'yes', 'on')

    @staticmethod
    def set(key, value):
        s = AppSetting.query.get(key)
        if not s:
            s = AppSetting(key=key, value=str(value))
            db.session.add(s)
        else:
            s.value = str(value)
        db.session.flush()
