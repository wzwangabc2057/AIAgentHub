from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 9110
    aiagent_base_url: str = "http://127.0.0.1:9100"
    default_chain_name_prefix: str = "goal"
    data_file: str = "extensions/goal_orchestrator/goals.json"
    dispatch_5005_url: str = "http://127.0.0.1:5005/ask"
    dispatch_5005_token: str = "your-token"

    class Config:
        env_prefix = "GOAL_ORCH_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
