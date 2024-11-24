"""
Class to return a redis singleton
"""
import redis

from takehome.config import settings
from takehome.logs import LOGGER


class Singleton(type):
    """
    An metaclass for singleton purpose.
    Every singleton class should inherit from this class by 'metaclass=Singleton'.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class RedisClient(metaclass=Singleton):
    """
    A Redis Client class using `Singleton` class as mterclass,
    for making redis object as sigleton
    """

    def __init__(self, redis_url):
        LOGGER.info("RedisConnection: initializing redis connection pool")
        self.pool = redis.ConnectionPool.from_url(redis_url)

    @property
    def conn(self):
        """
        Returns a active Singleton redis client connection
        """
        if not hasattr(self, '_conn') or not self.is_alive():
            self.get_connection()
        return self._conn

    def get_connection(self):
        """
        Makes a new redis connection
        """
        LOGGER.info("RedisConnection: making a new redis connection")
        self._conn = redis.Redis(connection_pool = self.pool)

    def is_alive(self):
        """
        Check for active connection if connection is not active create a new one
        """
        try:
            return self._conn.ping()
        except redis.ConnectionError:
            LOGGER.warn("RedisConnection: connection broken")
            return False

redis_client = RedisClient(settings.REDIS_URL).conn
