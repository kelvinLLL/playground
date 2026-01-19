from simple_quant.events import FillEvent, OrderEvent, EventType
from simple_quant.execution.base import ExecutionHandler
from simple_quant.data.base import DataHandler
from queue import Queue
from datetime import datetime

class SimulatedExecutionHandler(ExecutionHandler):
    """
    The simulated execution handler simply converts all order
    objects into fill objects automatically at the current market
    prices (mocking). 
    
    This allows for a straightforward "first-go" test of any 
    strategy, before implementation with a more sophisticated
    execution handler.
    """
    
    def __init__(self, events: Queue, bars: DataHandler):
        """
        Initializes the handler. Setting the event queue.
        """
        self.events = events
        self.bars = bars

    def execute_order(self, event: OrderEvent):
        """
        Simply converts Order objects into Fill objects naively,
        i.e. without any latency, slippage or fill-ratio problems.
        
        Parameters:
        event - Contains an Event object with order information.
        """
        if event.type == EventType.ORDER:
            # Obtain the fill price
            # We use the latest "Close" price for the symbol
            fill_price = self.bars.get_latest_bar_value(event.symbol, "Close")
            
            # Create the Fill Event
            fill_event = FillEvent(
                timeindex=datetime.now(), 
                symbol=event.symbol, 
                exchange='ARCA',
                quantity=event.quantity, 
                direction=event.direction, 
                fill_cost=None, # None = use the 'close' price
                commission=self.calculate_commission(event.quantity, fill_price)
            )
            self.events.put(fill_event)

    def calculate_commission(self, quantity, fill_price):
        """
        Calculates the commission for a transaction.
        Based on Interactive Brokers simplified structure.
        
        https://www.interactivebrokers.com/en/index.php?f=commission&p=stocks2
        """
        # Minimal commission using IB as an example
        # max(1.0, 0.005 * quantity) // Min 1 USD
        commission = max(1.0, 0.005 * quantity)
        return commission
