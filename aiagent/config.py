"""Configuration management for AIAgentHub"""

import os
import socket
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str = "mongodb://admin:yourpassword@localhost:27017/admin"
    mongo_db: str = "aiagent_hub"

    # API Server
    api_port: int = 9100
    api_base_url: str = "http://localhost:9100"

    # Node / Distributed
    node_id: str = ""
    max_concurrent: int = 8

    # Execution
    default_timeout: int = 300
    poll_interval: int = 2  # seconds between MongoDB polls
    heartbeat_interval: int = 30  # seconds between heartbeats
    heartbeat_timeout: int = 90  # seconds before marking node offline

    # Worker
    worker_poll_interval: int = 3  # seconds between task polling

    # Paths
    agents_dir: str = "agents"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_node_id(self) -> str:
        """Get node ID, auto-generate from hostname if not set"""
        if self.node_id:
            return self.node_id
        return f"node_{socket.gethostname().replace('.', '_').replace('-', '_')}"


settings = Settings()
