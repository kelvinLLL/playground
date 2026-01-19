from enum import Enum
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class EventType(str, Enum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"

class Event(BaseModel):
    """
    Base Event class for the event-driven system.
    """
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)

class MarketEvent(Event):
    """
    Handles the event of receiving a new market update with corresponding bars.
    """
    type: EventType = EventType.MARKET
    
    # We can store the data directly here, or just a reference/flag 
    # that data is available. For simplicity, we assume the data 
    # has been updated in the DataHandler and this event triggers the strategy.

class SignalEvent(Event):
    """
    Handles the event of sending a Signal from a Strategy object.
    This is received by a Portfolio object and acted upon.
    """
    type: EventType = EventType.SIGNAL
    symbol: str
    datetime: datetime
    signal_type: str  # 'LONG', 'SHORT', 'EXIT'
    strength: float = 1.0  # Allow for sizing based on strength if needed

class OrderEvent(Event):
    """
    Handles the event of sending an Order to an execution system.
    The order contains a symbol (e.g. GOOGNC), a type (market or limit),
    quantity and a direction.
    """
    type: EventType = EventType.ORDER
    symbol: str
    order_type: str = "MKT"  # 'MKT', 'LMT'
    quantity: int
    direction: str  # 'BUY', 'SELL'

class FillEvent(Event):
    """
    Encapsulates the notion of a Filled Order, as returned
    from a brokerage. Stores the quantity of an instrument
    actually filled and at what price. In addition, stores
    the commission of the trade from the brokerage.
    """
    type: EventType = EventType.FILL
    timeindex: datetime
    symbol: str
    exchange: str
    quantity: int
    direction: str
    fill_cost: Optional[float] = None
    commission: Optional[float] = None
