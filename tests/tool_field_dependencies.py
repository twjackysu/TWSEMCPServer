"""Fields that each tool explicitly accesses with .get("field").

Only endpoints where tools hardcode specific field names are listed here.
Endpoints where tools use format_properties_with_values_multiline (dump all
fields generically) are intentionally excluded — they have no hardcoded fields
to break.

Tests use this to check: required fields ⊆ live API response fields.
Extra fields added by TWSE are fine; missing required fields mean a tool is broken.
"""

from typing import Dict, List

TOOL_REQUIRED_FIELDS: Dict[str, List[str]] = {
    # --- market.py ---
    "/Announcement/BFZFZU_T": ["Code", "Date", "Name", "Number"],
    "/announcement/notetrans": ["Code", "Name", "RecentlyMetAttentionSecuritiesCriteria"],
    "/announcement/notice": ["ClosingPrice", "Code", "Date", "Name", "Number", "NumberOfAnnouncement", "PE", "TradingInfoForAttention"],
    "/announcement/punish": ["Code", "DispositionMeasures", "Name", "ReasonsOfDisposition"],
    "/exchangeReport/BFI84U": ["Code", "Name", "Reason"],
    "/exchangeReport/BFT41U": ["AskVolume", "BidVolume", "Code", "Name", "TradePrice", "TradeValue", "TradeVolume", "Transaction"],
    "/exchangeReport/MI_INDEX4": ["Change", "Date", "FormosaIndex", "TradeValue"],
    "/exchangeReport/MI_INDEX20": ["Change", "ClosingPrice", "Code", "Date", "Dir", "Name", "Rank", "TradeVolume", "Transaction"],
    "/exchangeReport/STOCK_FIRST": ["Code", "Name", "TradeValue", "TradeVolume"],
    "/exchangeReport/TWT53U": ["Code", "Name", "TradePrice", "TradeVolume"],
    "/exchangeReport/TWT84U": ["Code", "Name", "TodayLimitDown", "TodayLimitUp"],
    "/exchangeReport/TWT85U": ["Code", "Name", "PeriodicCallAuctionTrading"],
    "/exchangeReport/TWT88U": ["Code", "Name", "PriceUnderwritten"],
    "/exchangeReport/TWTAWU": ["Code", "Name", "TradingHaltDate", "TradingResumptionDate"],
    "/exchangeReport/TWTB4U": ["Code", "Name", "Suspension"],
    "/exchangeReport/TWTBAU1": ["Code", "Name", "StartDate"],
    "/exchangeReport/TWTBAU2": ["Code", "Name", "StartDate"],
    "/block/BFIAUU_d": ["Date", "TradeValue", "TradeVolume"],
    "/block/BFIAUU_m": ["Month", "TradeValue", "TradeVolume"],
    "/block/BFIAUU_y": ["Month", "TradeValue", "TradeVolume"],
    "/exchangeReport/BWIBBU_d": ["Code", "DividendYear", "DividendYield", "FiscalYearQuarter", "Name", "PBratio", "PEratio"],
    "/exchangeReport/BWIBBU_ALL": ["Code", "Date", "DividendYield", "Name", "PBratio", "PEratio"],
    "/exchangeReport/FMNPTK_ALL": ["AvgClosingPrice", "Code", "HDate", "HighestPrice", "LDate", "LowestPrice", "Name", "TradeValue", "TradeVolume", "Transaction", "Year"],
    "/exchangeReport/FMSRFK_ALL": ["Code", "HighestPrice", "LowestPrice", "Month", "Name", "TradeValueA", "TradeVolumeB", "Transaction", "TurnoverRatio", "WeightedAvgPriceAB"],
    "/exchangeReport/FMTQIK": ["Change", "Date", "TAIEX", "TradeValue", "TradeVolume", "Transaction"],
    "/exchangeReport/STOCK_DAY_ALL": ["Change", "ClosingPrice", "Code", "Date", "HighestPrice", "LowestPrice", "Name", "OpeningPrice", "TradeValue", "TradeVolume", "Transaction"],
    "/SBL/TWT96U": ["GRETAIAvailableVolume", "GRETAICode", "TWSEAvailableVolume", "TWSECode"],
    "/opendata/twtazu_od": ["上漲", "下跌", "出表日期", "持平", "未成交", "漲停", "無比價", "跌停", "類型"],

    # --- indices.py ---
    "/exchangeReport/MI_INDEX": ["收盤指數", "指數", "漲跌", "漲跌百分比"],

    # --- statistics.py ---
    "/exchangeReport/MI_5MINS": ["AccAskOrders", "AccAskVolume", "AccBidOrders", "AccBidVolume", "AccTradeValue", "AccTradeVolume", "AccTransaction", "Time"],

    # --- broker.py ---
    "/opendata/t187ap01": ["合計", "受託買賣", "自行買賣", "職位"],
    "/opendata/t187ap19": ["出表日期", "公司總成交筆數", "成交月份", "成交筆數"],
    "/opendata/t187ap20": ["券商代號", "券商名稱", "出表日期", "借方餘額", "會計科目名稱"],
    "/opendata/t187ap21": ["券商代號", "券商名稱", "出表日期", "本月金額", "會計科目名稱"],
    "/opendata/OpenData_BRK01": ["女性員工人數", "總人數", "男性員工人數", "證券商代號"],
    "/opendata/OpenData_BRK02": ["地址", "電話", "證券商代號", "證券商名稱"],
    "/brokerService/secRegData": ["BrokerageBusinessStartingDate", "Name", "SecuritiesFirmCode", "WealthManagementBusinessStartingDate"],
    "/brokerService/brokerList": ["Code"],

    # --- company/basic_info.py ---
    "/opendata/t187ap08_L": ["全體監察人不足股數", "全體董事不足股數", "公司代號", "公司名稱"],
    "/opendata/t187ap09_L": ["公司名稱", "百分比"],
    "/opendata/t187ap24_L": ["公司代號", "公司名稱", "經營權異動日期", "經營權異動說明"],
    "/opendata/t187ap25_L": ["公司代號", "公司名稱", "季別", "年度", "營業範圍重大變更說明"],
    "/opendata/t187ap26_L": ["停止買賣日期", "公司代號", "公司名稱"],
    "/opendata/t187ap27_L": ["公司代號", "公司名稱", "變更日期"],
    "/opendata/t187ap30_L": ["公司代號", "公司名稱"],
    "/opendata/t187ap33_L": ["公司代號", "公司名稱", "董事長是否兼任總經理"],
    "/opendata/t187ap34_L": ["公司代號", "公司名稱", "董監事選任方式", "股東常(臨時)會日期-日期"],
    "/opendata/t187ap35_L": ["公司代號", "公司名稱", "召開股東會日期", "提案內容", "股東依公司法第172條之1行使提案權-提案受理期間"],
    "/opendata/t187ap38_L": ["公司代號", "公司名稱"],
    "/opendata/t187ap41_L": ["公司代號", "公司名稱", "是否採電子投票", "股東常(臨時)會", "開會地點", "開會日期"],
    "/static/20151104/CSR103": ["公司代號", "公司名稱"],

    # --- company/listing.py ---
    "/company/applylistingForeign": ["ApplicationDate", "ApprovedDate", "Code", "Company", "ListingDate"],
    "/company/applylistingLocal": ["ApplicationDate", "ApprovedDate", "Code", "Company", "ListingDate"],
    "/company/newlisting": ["Code", "Company", "ListingDate"],
    "/company/suspendListingCsvAndHtml": ["Code", "Company", "DelistingDate"],

    # --- company/financials.py ---
    "/opendata/t187ap03_L": ["產業別"],
    "/opendata/t187ap17_L": [
        "出表日期", "年度", "季別", "公司代號", "公司名稱",
        "營業收入(百萬元)",
        "毛利率(%)(營業毛利)/(營業收入)",
        "營業利益率(%)(營業利益)/(營業收入)",
        "稅前純益率(%)(稅前純益)/(營業收入)",
        "稅後純益率(%)(稅後純益)/(營業收入)",
    ],

    # --- company/esg.py (specific endpoints with hardcoded fields) ---
    "/opendata/t187ap46_L_15": ["公司代號", "公司名稱", "在人口密集地區的煉油廠數量(座)", "報告年度"],
    "/opendata/t187ap46_L_17": [
        "公司代號", "公司名稱", "報告年度",
        "對促進小型企業及社區發展的貸放件數(件)",
        "對促進小型企業及社區發展的貸放餘額(仟元)",
        "對缺少銀行服務之弱勢族群提供金融教育之參與人數(人)",
    ],
    "/opendata/t187ap46_L_20": ["公司代號", "公司名稱", "因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)", "報告年度"],
}
