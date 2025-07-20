from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from application.models import Appconfig


class DatabaseChangeEvent:
    def __init__(self):
        pass


class DatabaseEventHandler:
    def __init__(self):
        self._listeners = []

    def register_listener(self, listener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def notify_listener(self, event: DatabaseChangeEvent):
        for listener in self._listeners:
            listener.handle_database_event(event)

    def on_change_database(self):
        event = DatabaseChangeEvent()
        self.notify_listener(event)


class DBHandler:
    def __init__(self, db_url, curr_session):
        if curr_session is None:
            engine = create_engine(db_url)
            self.conn = engine.connect()
            session = sessionmaker(bind=engine)
            self.session = session()
        else:
            self.session = curr_session
            self.conn = None

    def close(self):
        self.session.close()
        if self.conn is not None:
            self.conn.close()

    def get_config_entry(self, app_area, config_key):
        if self.check_config_entry_exists(app_area, config_key):
            entry = self.session.query(Appconfig).filter_by(config_area=app_area, config_key=config_key).first()
            self.close()
            if entry is not None:
                return entry.config_value
            else:
                return None
        else:
            return None

    def check_config_entry_exists(self, app_area, config_key):
        entry = self.session.query(Appconfig).filter_by(config_area=app_area, config_key=config_key).first()
        self.close()
        if entry is None:
            return False
        else:
            return True

    def get_all_config_entries_for_area(self, app_area):
        entries = self.session.query(Appconfig).filter_by(config_area=app_area).all()
        self.close()
        return entries

    def create_update_config_entry(self, app_area, config_key, config_value):
        if self.check_config_entry_exists(app_area, config_key):
            entry = self.session.query(Appconfig).filter_by(config_area=app_area, config_key=config_key).first()
            entry.config_value = config_value
        else:
            config_record = Appconfig()
            config_record.config_area = app_area
            config_record.config_key = config_key
            config_record.config_value = config_value
            self.session.add(config_record)
        self.session.commit()
        self.close()
