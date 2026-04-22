from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from pathlib import Path


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaType(Enum):
    IMAGE = "image"
    VIDEO = "video"


@dataclass
class ProcessingTask:
    user_id: int
    file_path: Path
    media_type: MediaType
    grid_x: int
    grid_y: int
    adaptation_method: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    result_files: List[Path] = None
    
    def __post_init__(self):
        if self.result_files is None:
            self.result_files = []