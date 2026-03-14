"""Checkpoint state management for resumable audit runs."""

import json
import logging
import os

logger = logging.getLogger(__name__)


class CheckpointManager:
    def __init__(self, output_dir: str):
        self.filepath = os.path.join(output_dir, ".checkpoint.json")
        self._data: dict = {
            "stage": 0,
            "completed_tasks": {},
            "config": {},
        }

    def load(self) -> bool:
        """Load checkpoint from disk. Returns True if checkpoint exists."""
        if not os.path.exists(self.filepath):
            return False
        try:
            with open(self.filepath) as f:
                self._data = json.load(f)
            logger.info(f"Loaded checkpoint: stage={self._data.get('stage', 0)}, "
                        f"completed={sum(v for v in self._data['completed_tasks'].values())}")
            return True
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load checkpoint: {e}. Starting fresh.")
            return False

    def save(self):
        """Persist checkpoint to disk."""
        with open(self.filepath, "w") as f:
            json.dump(self._data, f, indent=2)

    def mark_complete(self, task_key: str):
        """Mark a task as complete and save."""
        self._data["completed_tasks"][task_key] = True
        self.save()
        logger.debug(f"Checkpoint: marked {task_key} complete")

    def is_complete(self, task_key: str) -> bool:
        return self._data["completed_tasks"].get(task_key, False)

    def set_stage(self, stage: int):
        self._data["stage"] = stage
        self.save()

    def get_stage(self) -> int:
        return self._data.get("stage", 0)

    def set_config(self, config: dict):
        self._data["config"] = config
        self.save()

    def get_config(self) -> dict:
        return self._data.get("config", {})
