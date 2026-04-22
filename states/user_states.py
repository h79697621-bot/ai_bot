from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    waiting_for_media = State()
    setting_grid_size_x = State()
    setting_grid_size_y = State()
    choosing_adaptation_method = State()
    previewing_adaptation = State()
    confirming_processing = State()
    processing_media = State()