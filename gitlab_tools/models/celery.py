import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from celery import schedules, states
from gitlab_tools.extensions import db


class ConstraintError(Exception):
    pass


class BaseTable(db.Model):  # type: ignore
    __abstract__ = True
    updated = db.Column(db.DateTime, default=func.now(), onupdate=func.current_timestamp())
    created = db.Column(db.DateTime, default=func.now())

    @classmethod
    def filter_by(cls, session, **kwargs):
        """
        session.query(MyClass).filter_by(name = 'some name')
        :param kwargs:
        :param session:
        """
        return session.query(cls).filter_by(**kwargs)

    @classmethod
    def get_or_create(cls, session_obj, defaults=None, **kwargs):
        obj = session_obj.query(cls).filter_by(**kwargs).first()
        if obj:
            return obj, False

        params = dict((k, v) for k, v in kwargs.items())
        params.update(defaults or {})
        obj = cls(**params)
        return obj, True

    @classmethod
    def update_or_create(cls, session_obj, defaults=None, **kwargs):
        obj = session_obj.query(cls).filter_by(**kwargs).first()
        if obj:
            for key, value in defaults.items():
                setattr(obj, key, value)
            created = False
        else:
            params = dict((k, v) for k, v in kwargs.items())
            params.update(defaults or {})
            obj = cls(**params)
            created = True
        return obj, created


class IntervalSchedule(BaseTable):
    __tablename__ = "interval_schedule"
    """
    PERIOD_CHOICES = (('days', 'Days'),
                      ('hours', 'Hours'),
                      ('minutes', 'Minutes'),
                      ('seconds', 'Seconds'),
                      ('microseconds', 'Microseconds'))
    """
    id = db.Column(db.Integer, primary_key=True)
    every = db.Column(db.Integer, nullable=False)
    period = db.Column(db.Unicode(255))
    periodic_tasks = relationship('PeriodicTask')

    @property
    def schedule(self):
        return schedules.schedule(datetime.timedelta(**{self.period.code: self.every}))

    @classmethod
    def from_schedule(cls, session, schedule, period='seconds'):
        every = max(schedule.run_every.total_seconds(), 0)
        obj = cls.filter_by(session, every=every, period=period).first()
        if obj is None:
            return cls(every=every, period=period)

        return obj

    def __str__(self):
        if self.every == 1:
            return 'every {0.period_singular}'.format(self)
        return 'every {0.every} {0.period}'.format(self)

    @property
    def period_singular(self):
        return self.period[:-1]


class CrontabSchedule(BaseTable):
    """
    Task result/status.
    """
    __tablename__ = "crontab_schedule"
    id = db.Column(db.Integer, primary_key=True)
    minute = db.Column(db.String(length=120), default="*")
    hour = db.Column(db.String(length=120), default="*")
    day_of_week = db.Column(db.String(length=120), default="*")
    day_of_month = db.Column(db.String(length=120), default="*")
    month_of_year = db.Column(db.String(length=120), default="*")
    periodic_tasks = relationship('PeriodicTask')

    def __str__(self):
        rfield = lambda f: f and str(f).replace(' ', '') or '*'
        return '{0} {1} {2} {3} {4} (m/h/d/dM/MY)'.format(
            rfield(self.minute), rfield(self.hour), rfield(self.day_of_week),
            rfield(self.day_of_month), rfield(self.month_of_year),
        )

    @property
    def schedule(self):
        return schedules.crontab(minute=self.minute,
                                 hour=self.hour,
                                 day_of_week=self.day_of_week,
                                 day_of_month=self.day_of_month,
                                 month_of_year=self.month_of_year)

    @classmethod
    def from_schedule(cls, session, schedule):
        spec = {'minute': schedule._orig_minute,
                'hour': schedule._orig_hour,
                'day_of_week': schedule._orig_day_of_week,
                'day_of_month': schedule._orig_day_of_month,
                'month_of_year': schedule._orig_month_of_year}
        obj = cls.filter_by(session, **spec).first()
        if obj is None:
            return cls(**spec)
        return obj


class PeriodicTasks(BaseTable):
    __tablename__ = "periodic_tasks"
    id = db.Column(db.Integer, primary_key=True)
    ident = db.Column(db.Integer, default=1, index=True)
    last_update = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @classmethod
    def changed(cls):
        found = PeriodicTasks.query.filter_by(ident=1).first()
        if not found:
            found = PeriodicTasks()
        found.last_update = datetime.datetime.now()
        db.session.add(found)

    @classmethod
    def last_change(cls, session):
        obj = cls.filter_by(session, ident=1).first()
        return obj.last_update if obj else None


class PeriodicTask(BaseTable):
    __tablename__ = "periodic_task"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=200), unique=True)
    task = db.Column(db.String(length=200))
    crontab_id = db.Column(db.Integer, db.ForeignKey('crontab_schedule.id'))
    crontab = relationship("CrontabSchedule", back_populates="periodic_tasks")
    interval_id = db.Column(db.Integer, db.ForeignKey('interval_schedule.id'))
    interval = relationship("IntervalSchedule", back_populates="periodic_tasks")
    args = db.Column(db.Text, default='[]')
    kwargs = db.Column(db.Text, default='{}')
    queue = db.Column(db.String(length=200))
    exchange = db.Column(db.String(length=200))
    routing_key = db.Column(db.String(length=200))
    headers = db.Column(db.Text, default='{}')
    priority = db.Column(db.Integer)
    expires = db.Column(db.DateTime)
    expire_seconds = db.Column(db.Integer)
    one_off = db.Column(db.Boolean, default=False)
    start_time = db.Column(db.DateTime)
    enabled = db.Column(db.Boolean, default=True)
    last_run_at = db.Column(db.DateTime)
    total_run_count = db.Column(db.Integer, default=0)

    pull_mirrors = relationship("PullMirror", order_by="PullMirror.id", backref="periodic_task", lazy='dynamic')
    no_changes = False

    def __str__(self):
        fmt = '{0.name}: {0.crontab}'
        return fmt.format(self)

    @property
    def schedule(self):
        if self.crontab:
            return self.crontab.schedule
        if self.interval:
            return self.interval.schedule

        return None


class TaskMeta(db.Model):
    __tablename__ = 'celery_taskmeta'
    __table_args__ = {'sqlite_autoincrement': True}
    id = db.Column(db.Integer, db.Sequence('task_id_sequence'),
                   primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(155), unique=True)
    status = db.Column(db.String(50), default=states.PENDING)
    result = db.Column(db.PickleType, nullable=True)
    date_done = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                          onupdate=datetime.datetime.utcnow, nullable=True)
    traceback = db.Column(db.Text, nullable=True)
    task_result = relationship("TaskResult", backref="taskmeta", uselist=False)


class TaskSet(db.Model):
    """TaskSet result."""
    __tablename__ = 'celery_tasksetmeta'
    __table_args__ = {'sqlite_autoincrement': True}

    id = db.Column(db.Integer, db.Sequence('taskset_id_sequence'),
                   autoincrement=True, primary_key=True)
    taskset_id = db.Column(db.String(155), unique=True)
    result = db.Column(db.PickleType, nullable=True)
    date_done = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                          nullable=True)
