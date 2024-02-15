from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    connection_string: str = 'mongodb://localhost:27017'
    auth_private_key_path: str = 'private.pem'
    auth_public_key_path: str = 'public.pem'
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', env_prefix='rss_server_')

@lru_cache
def get_settings():
    return Settings()