"""Test company API schemas to detect field name changes."""

import pytest
from utils import TWSEAPIClient


class TestCompanyAPISchema:
    """Test that company APIs return expected field names."""

    def test_board_insufficient_shares_schema(self):
        """Test /opendata/t187ap08_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap08_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["公司代號", "公司名稱", "全體董事不足股數", "全體監察人不足股數"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_independent_directors_schema(self):
        """Test /opendata/t187ap30_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap30_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["公司代號", "公司名稱", "職稱", "姓名"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_disposal_stocks_schema(self):
        """Test /announcement/punish has required fields."""
        data = TWSEAPIClient.get_data("/announcement/punish")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["Code", "Name", "DispositionMeasures", "ReasonsOfDisposition"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_board_insufficient_consecutive_schema(self):
        """Test /opendata/t187ap10_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap10_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["連續不足達3個月", "連續不足達4個月", "連續不足逾1年以上"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_ownership_changes_schema(self):
        """Test /opendata/t187ap24_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap24_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["公司代號", "公司名稱", "經營權異動日期", "經營權異動說明"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_business_scope_changes_schema(self):
        """Test /opendata/t187ap25_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap25_L")
        assert len(data) > 0, "API should return data"
        
        # Filter out empty records
        valid_data = [item for item in data if item.get("公司代號") and item.get("公司名稱")]
        if not valid_data:
            pytest.skip("No valid data with company code and name")
        
        first_item = valid_data[0]
        required_fields = ["公司代號", "公司名稱", "年度", "季別", "營業範圍重大變更說明"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_board_pledged_shares_schema(self):
        """Test /opendata/t187ap09_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap09_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["百分比", "公司名稱"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_cumulative_voting_schema(self):
        """Test /opendata/t187ap34_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap34_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["公司代號", "公司名稱", "董監事選任方式"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_shareholder_proposal_schema(self):
        """Test /opendata/t187ap35_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap35_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["公司代號", "公司名稱", "召開股東會日期", "提案內容"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"

    def test_ceo_dual_role_schema(self):
        """Test /opendata/t187ap33_L has required fields."""
        data = TWSEAPIClient.get_data("/opendata/t187ap33_L")
        assert len(data) > 0, "API should return data"
        
        first_item = data[0]
        required_fields = ["公司代號", "公司名稱", "董事長是否兼任總經理"]
        
        for field in required_fields:
            assert field in first_item, f"Missing field: {field}. Available fields: {list(first_item.keys())}"
