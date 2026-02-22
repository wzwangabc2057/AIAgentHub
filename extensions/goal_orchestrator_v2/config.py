from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 9120
    aiagent_base_url: str = "http://127.0.0.1:9100"
    default_chain_name_prefix: str = "goalv2"
    data_file: str = "extensions/goal_orchestrator_v2/goals_v2.json"

    dispatch_5005_url: str = "http://127.0.0.1:5005/ask"
    dispatch_5005_token: str = "your-token"

    day_poll_seconds: int = 120
    night_poll_seconds: int = 40
    night_start_hour: int = 21
    night_end_hour: int = 7

    run_stall_seconds: int = 900
    max_replans: int = 2
    ab_epsilon: float = 0.2

    class Config:
        env_prefix = "GOAL_ORCH_V2_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
