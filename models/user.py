from dataclasses import dataclass
from typing import Optional


@dataclass
class UserSettings:
    user_id: int
    grid_x: int = 2
    grid_y: int = 2
    adaptation_method: str = "pad"
    quality_level: str = "high"
    background_mode: str = "keep"  # keep, remove_white, remove_black, remove_smart

    def __post_init__(self):
        if self.adaptation_method not in ["pad", "stretch", "crop"]:
            self.adaptation_method = "pad"
        if self.quality_level not in ["low", "medium", "high"]:
            self.quality_level = "high"
        if self.background_mode not in ["keep", "remove_white", "remove_black", "remove_smart"]:
            self.background_mode = "keep"
