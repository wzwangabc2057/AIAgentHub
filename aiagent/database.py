"""
MongoDB database connection and collection management

Database: aiagent_hub
Collections:
- agents: Agent definitions + node affinity
- prompts: Prompt templates (with versioning)
- executions: Execution records + status + node_id
- chains: Chain step definitions
- results: Step results (written by Claude)
- workers: Node registration + heartbeat
- schedules: Cron/event triggers
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from loguru import logger
from typing import Optional

from aiagent.config import settings


class DatabaseManager:
    """MongoDB database manager (singleton)"""

    _instance: Optional["DatabaseManager"] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self):
        uri = settings.mongo_uri
        db_name = settings.mongo_db
        try:
            self._client = MongoClient(uri)
            self._db = self._client[db_name]
            self._client.admin.command("ping")
            logger.info(f"MongoDB connected: {db_name}")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise

    @property
    def db(self) -> Database:
        if self._db is None:
            self._connect()
        return self._db

    @property
    def agents(self) -> Collection:
        return self.db["agents"]

    @property
    def prompts(self) -> Collection:
        return self.db["prompts"]

    @property
    def prompt_history(self) -> Collection:
        return self.db["prompt_history"]

    @property
    def executions(self) -> Collection:
        return self.db["executions"]

    @property
    def chains(self) -> Collection:
        return self.db["chains"]

    @property
    def results(self) -> Collection:
        return self.db["results"]

    @property
    def workers(self) -> Collection:
        return self.db["workers"]

    @property
    def schedules(self) -> Collection:
        return self.db["schedules"]

    def ensure_indexes(self):
        """Create all necessary indexes"""
        # agents
        self.agents.create_index("status")
        self.agents.create_index("node_id")

        # prompts
        self.prompts.create_index("agent_id")
        self.prompts.create_index([("agent_id", ASCENDING), ("version", DESCENDING)])

        # prompt_history
        self.prompt_history.create_index("prompt_id")
        self.prompt_history.create_index([("prompt_id", ASCENDING), ("version", DESCENDING)])

        # executions
        self.executions.create_index("agent_id")
        self.executions.create_index("chain_id")
        self.executions.create_index("status")
        self.executions.create_index("node_id")
        self.executions.create_index("created_at")
        self.executions.create_index([("status", ASCENDING), ("agent_id", ASCENDING)])

        # chains
        self.chains.create_index("status")
        self.chains.create_index("created_at")

        # results
        self.results.create_index("execution_id")
        self.results.create_index("chain_id")
        self.results.create_index([("chain_id", ASCENDING), ("step", ASCENDING)])

        # workers
        self.workers.create_index("status")
        self.workers.create_index("last_heartbeat")

        # schedules
        self.schedules.create_index("enabled")
        self.schedules.create_index("type")

        logger.info("Database indexes created")

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")


# Global instance
_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
