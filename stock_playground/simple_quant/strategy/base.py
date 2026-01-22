from abc import ABC, abstractmethod
from queue import Queue
from simple_quant.events import MarketEvent

class Strategy(ABC):
    """
    Strategy is an abstract base class providing an interface for
    all subsequent (inherited) strategy handling objects.
    """
    def __init__(self, bars, events: Queue):
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list

    @abstractmethod
    def calculate_signals(self, event: MarketEvent):
        """
        Provides the mechanisms to calculate the list of signals.
        """
        raise NotImplementedError("Should implement calculate_signals()")
