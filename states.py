from aiogram.fsm.state import State, StatesGroup

class NewsSetupStates(StatesGroup):
    waiting_channel = State()
    waiting_topics = State()
    waiting_schedule = State()