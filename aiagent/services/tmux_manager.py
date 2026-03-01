"""
tmux session lifecycle management

Manages tmux sessions for agent execution:
- Create/destroy sessions
- Send commands
- Check session status
- Pipe-pane logging
"""

import subprocess
import os
from typing import Optional, List
from loguru import logger


class TmuxManager:
    """Manages tmux sessions for AI agents"""

    SESSION_PREFIX = "aah_"

    def session_name(self, agent_id: str) -> str:
        return f"{self.SESSION_PREFIX}{agent_id}"

    def session_exists(self, agent_id: str) -> bool:
        name = self.session_name(agent_id)
        result = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True
        )
        return result.returncode == 0

    def create_session(self, agent_id: str, work_dir: str) -> bool:
        """Create a new tmux session for an agent"""
        name = self.session_name(agent_id)

        if self.session_exists(agent_id):
            logger.debug(f"tmux session {name} already exists")
            return True

        abs_work_dir = os.path.abspath(work_dir)
        os.makedirs(abs_work_dir, exist_ok=True)

        # Clean environment: remove CLAUDECODE to avoid nested session detection
        clean_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", name, "-c", abs_work_dir, "-x", "200", "-y", "50"],
            capture_output=True, text=True, env=clean_env
        )

        if result.returncode == 0:
            logger.info(f"Created tmux session: {name} (dir: {abs_work_dir})")
            # Unset CLAUDECODE inside the session to allow Claude CLI to run
            subprocess.run(
                ["tmux", "send-keys", "-t", name, "unset CLAUDECODE", "Enter"],
                capture_output=True
            )
            # Enable pipe-pane logging
            log_path = os.path.join(abs_work_dir, "_output.log")
            subprocess.run(
                ["tmux", "pipe-pane", "-t", name, f"cat >> {log_path}"],
                capture_output=True
            )
            return True
        else:
            logger.error(f"Failed to create tmux session {name}: {result.stderr}")
            return False

    def send_keys(self, agent_id: str, command: str) -> bool:
        """Send keys to a tmux session"""
        name = self.session_name(agent_id)
        result = subprocess.run(
            ["tmux", "send-keys", "-t", name, command, "Enter"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.debug(f"Sent keys to {name}")
            return True
        else:
            logger.error(f"Failed to send keys to {name}: {result.stderr}")
            return False

    def kill_session(self, agent_id: str) -> bool:
        """Kill a tmux session"""
        name = self.session_name(agent_id)
        result = subprocess.run(
            ["tmux", "kill-session", "-t", name],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info(f"Killed tmux session: {name}")
            return True
        return False

    def list_sessions(self) -> List[dict]:
        """List all aah_ tmux sessions"""
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}:#{session_created}:#{session_activity}"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return []

        sessions = []
        for line in result.stdout.strip().split("\n"):
            if not line or not line.startswith(self.SESSION_PREFIX):
                continue
            parts = line.split(":")
            sessions.append({
                "name": parts[0],
                "agent_id": parts[0][len(self.SESSION_PREFIX):],
                "created": parts[1] if len(parts) > 1 else "",
                "activity": parts[2] if len(parts) > 2 else "",
            })
        return sessions

    def capture_pane(self, agent_id: str, lines: int = 50) -> Optional[str]:
        """Capture recent output from a tmux pane"""
        name = self.session_name(agent_id)
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", name, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout
        return None


# Global instance
tmux_manager = TmuxManager()
