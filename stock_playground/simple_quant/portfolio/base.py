from abc import ABC, abstractmethod
from simple_quant.events import SignalEvent, FillEvent

class Portfolio(ABC):
    """
    The Portfolio class handles the positions and market value of all 
    instruments at a resolution of a "bar", i.e. secondly, minutely, 
    5-min, 30-min, 60 min or EOD.
    """

    @abstractmethod
    def update_signal(self, event: SignalEvent):
        """
        Acts on a SignalEvent to generate new orders 
        based on the portfolio logic.
        """
        raise NotImplementedError("Should implement update_signal()")

    @abstractmethod
    def update_fill(self, event: FillEvent):
        """
        Updates the portfolio current positions and holdings 
        from a FillEvent.
        """
        raise NotImplementedError("Should implement update_fill()")
