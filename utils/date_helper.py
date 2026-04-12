"""ROC (Republic of China) and AD (Anno Domini) date conversion utilities.

Taiwan uses the ROC calendar where year = AD year - 1911.
TWSE legacy APIs return dates in ROC format (e.g., "114/01/02" for 2025-01-02).
"""


def roc_to_ad(roc_date: str) -> str:
    """
    Convert ROC date to AD date.

    Args:
        roc_date: ROC date string, e.g. "114/01/02" or "1140102"

    Returns:
        AD date string in "YYYY-MM-DD" format, e.g. "2025-01-02"
    """
    roc_date = roc_date.strip()

    if "/" in roc_date:
        parts = roc_date.split("/")
        roc_year = int(parts[0])
        month = parts[1]
        day = parts[2]
    else:
        # Format: "1140102" (7 digits: YYY + MM + DD)
        roc_year = int(roc_date[:-4])
        month = roc_date[-4:-2]
        day = roc_date[-2:]

    ad_year = roc_year + 1911
    return f"{ad_year}-{month}-{day}"


def ad_to_roc(ad_date: str) -> str:
    """
    Convert AD date to ROC date.

    Args:
        ad_date: AD date string, e.g. "2025-01-02" or "20250102"

    Returns:
        ROC date string in "YYY/MM/DD" format, e.g. "114/01/02"
    """
    ad_date = ad_date.strip()

    if "-" in ad_date:
        parts = ad_date.split("-")
        ad_year = int(parts[0])
        month = parts[1]
        day = parts[2]
    else:
        # Format: "20250102"
        ad_year = int(ad_date[:4])
        month = ad_date[4:6]
        day = ad_date[6:8]

    roc_year = ad_year - 1911
    return f"{roc_year}/{month}/{day}"
