"""Schema test configuration for all TWSE APIs.

This file defines which fields each API endpoint should have.
Run tests to detect when TWSE changes their API schema.
"""

from typing import List, Dict

# Define expected fields for each endpoint
# Format: {endpoint: [list of required fields]}
API_SCHEMA_MAP: Dict[str, List[str]] = {
    # Broker APIs
    "/opendata/t187ap01": ["職位", "出表日期", "合計", "受託買賣", "自行買賣"],
    "/opendata/t187ap20": ["出表日期", "券商代號", "券商名稱", "科目", "會計科目名稱", "本月借方總額", "本月貸方總額", "借方餘額"],
    "/opendata/t187ap21": ["出表日期", "券商代號", "券商名稱", "科目", "會計科目名稱", "本月金額", "累進金額"],
    "/opendata/t187ap18": ["券商(證券IB)簡稱", "證券代號", "設立日期"],
    "/opendata/t187ap19": ["出表日期", "成交月份", "成交筆數", "公司總成交筆數"],
    "/opendata/OpenData_BRK01": ["證券商代號", "男性員工人數", "女性員工人數", "總人數"],
    "/opendata/OpenData_BRK02": ["證券商代號", "證券商名稱", "地址", "電話"],
    "/brokerService/secRegData": ["SecuritiesFirmCode", "Name", "BrokerageBusinessStartingDate", "WealthManagementBusinessStartingDate"],
    "/brokerService/brokerList": ["Code", "Name", "EstablishmentDate", "Address", "Telephone"],
    
    # Company APIs
    "/opendata/t187ap08_L": ["公司代號", "公司名稱", "全體董事不足股數", "全體監察人不足股數"],
    "/opendata/t187ap30_L": ["公司代號", "公司名稱", "職稱", "姓名"],
    "/announcement/punish": ["Code", "Name", "DispositionMeasures", "ReasonsOfDisposition"],
    "/opendata/t187ap10_L": ["連續不足達3個月", "連續不足達4個月", "連續不足逾1年以上"],
    "/opendata/t187ap24_L": ["公司代號", "公司名稱", "經營權異動日期", "經營權異動說明"],
    "/opendata/t187ap25_L": ["公司代號", "公司名稱", "年度", "季別", "營業範圍重大變更說明"],
    "/opendata/t187ap09_L": ["百分比", "公司名稱"],
    "/opendata/t187ap34_L": ["公司代號", "公司名稱", "董監事選任方式"],
    "/opendata/t187ap35_L": ["公司代號", "公司名稱", "召開股東會日期", "提案內容"],
    "/opendata/t187ap33_L": ["公司代號", "公司名稱", "董事長是否兼任總經理"],
    
    # Company Listing APIs
    "/company/applylistingForeign": ["No", "Code", "Company", "ApplicationDate", "Chairman", 
                                      "AmountofCapital ", "CommitteeDate", "ApprovedDate", 
                                      "AgreementDate", "ListingDate", "Underwriter", 
                                      "UnderwritingPrice", "Note"],
    "/company/newlisting": ["Code", "Company", "ApplicationDate", "Chairman", 
                           "AmountofCapital ", "CommitteeDate", "ApprovedDate", 
                           "AgreementDate", "ListingDate", "ApprovedListingDate", 
                           "Underwriter", "UnderwritingPrice", "Note"],
    "/company/suspendListingCsvAndHtml": ["DelistingDate", "Company", "Code"],
    "/company/applylistingLocal": ["Code", "Company", "ApplicationDate", "Chairman", 
                                   "AmountofCapital ", "CommitteeDate", "ApprovedDate", 
                                   "AgreementDate", "ListingDate", "ApprovedListingDate", 
                                   "Underwriter", "UnderwritingPrice", "Note"],
    
    # Warrants APIs
    "/opendata/t187ap37_L": ["出表日期", "權證代號", "權證簡稱", "權證類型", "類別",
                            "流動量提供者報價方式", "履約開始日", "最後交易日", "履約截止日",
                            "發行單位數量(仟單位)", "結算方式(詳附註編號說明)", "標的證券/指數",
                            "最新標的履約配發數量(每仟單位權證)", "原始履約價格(元)/履約指數",
                            "原始上限價格(元)/上限指數", "原始下限價格(元)/下限指數",
                            "最新履約價格(元)/履約指數", "最新上限價格(元)/上限指數",
                            "最新下限價格(元)/下限指數", "備註"],
    "/opendata/t187ap43_L": ["出表日期", "日期", "人數"],
    "/opendata/t187ap36_L": ["出表日期", "發行人代號", "發行人名稱", "權證代號",
                            "名稱", "標的代號", "標的名稱", "申請發行日期"],
    
    # Other APIs
    "/opendata/t187ap47_L": ["基金名稱", "基金代號", "基金種類"],
    "/exchangeReport/BFI61U": ["債券名稱", "債券代號", "補息日期"],
    "/holidaySchedule/holidaySchedule": ["日期", "是否為假期", "說明"],
    
    # Trading APIs (daily)
    "/exchangeReport/STOCK_DAY_ALL": ["Code", "Name", "Date", "TradeVolume", "TradeValue", 
                                       "OpeningPrice", "HighestPrice", "LowestPrice", 
                                       "ClosingPrice", "Change", "Transaction"],
    
    # Trading APIs (periodic)
    "/exchangeReport/STOCK_DAY_AVG_ALL": ["Code", "Name"],
    "/exchangeReport/FMSRFK_ALL": ["Code", "Name", "Month", "HighestPrice", "LowestPrice",
                                    "WeightedAvgPriceAB", "Transaction", "TradeValueA", 
                                    "TradeVolumeB"],
    
    # Add more as needed...
}


def get_required_fields(endpoint: str) -> List[str]:
    """Get required fields for an API endpoint.
    
    Args:
        endpoint: API endpoint path
        
    Returns:
        List of required field names
        
    Raises:
        KeyError: If endpoint is not in schema map
    """
    if endpoint not in API_SCHEMA_MAP:
        raise KeyError(f"Endpoint {endpoint} not found in schema map. Please add it to API_SCHEMA_MAP.")
    
    return API_SCHEMA_MAP[endpoint]


def get_all_endpoints() -> List[str]:
    """Get list of all monitored API endpoints."""
    return list(API_SCHEMA_MAP.keys())
