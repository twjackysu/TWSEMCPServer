"""Type definitions for TWSE API data structures."""

from typing import TypedDict, Protocol, Any


class TWSEDataItem(TypedDict, total=False):
    """Base type for TWSE API data items.
    
    Using total=False allows partial dictionaries since API may not always return all fields.
    Common fields that appear across different endpoints.
    """
    # Broker fields
    券商代號: str
    券商名稱: str
    總人數: str
    月份: str
    期間: str
    設立日期: str
    資本額: str
    開辦日期: str
    分公司代號: str
    分公司名稱: str
    總公司名稱: str
    男營業員人數: str
    女營業員人數: str
    
    # Stock fields
    Code: str
    Name: str
    Date: str
    TradeVolume: str
    TradeValue: str
    OpeningPrice: str
    HighestPrice: str
    LowestPrice: str
    ClosingPrice: str
    Change: str
    Transaction: str
    Month: str
    WeightedAvgPriceAB: str
    TradeValueA: str
    TradeVolumeB: str
    TurnoverRatio: str
    
    # Fund fields
    基金代號: str
    基金名稱: str
    基金種類: str
    
    # Bond fields
    債券代號: str
    債券名稱: str
    補息日期: str
    
    # Holiday fields
    日期: str
    是否為假期: str
    說明: str
    
    # Electronic trading fields
    總成交量: str
    電子式成交量: str


class DataFormatter(Protocol):
    """Protocol for data formatting functions."""
    
    def __call__(self, item: TWSEDataItem) -> str:
        """Format a single data item into a string."""
        ...
