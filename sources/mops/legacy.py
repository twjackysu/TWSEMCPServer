"""What the legacy MOPS HTML pages (mopsov.twse.com.tw, read with ``utils.mops.parse_html_tables``) share.

Their tables head the columns with two rows: most header cells span both rows, a few span two columns and
have the names of those columns in the second row (t35sc09's 買回價格區間 → 最低 / 最高, t100sb02_1's
法人說明會簡報內容 → 中文檔案 / 英文檔案). ``parse_html_tables`` drops ``rowspan`` / ``colspan``, so each page
says which header cells are such groups.
"""

from typing import Dict, List, Sequence, Tuple

from utils.errors import UpstreamFormatError

UNEXPECTED_PAGE = "公開資訊觀測站回應非預期頁面（可能暫時限制存取或頁面改版），請稍後再試"


def two_row_header(top: Sequence[str], sub: Sequence[str], groups: Dict[str, Tuple[str, ...]],
                   source: str) -> List[str]:
    """One name per data cell: a group's columns are named "group/sub" (買回價格區間/最低), every other cell keeps its
    own name. Raises ``UpstreamFormatError`` when the second row no longer holds the groups' names in order."""
    expected = [s for t in top if t in groups for s in groups[t]]
    if list(sub) != expected:
        raise UpstreamFormatError(f"{source} 第二列表頭已變更：{list(sub)}，預期 {expected}")
    names: List[str] = []
    for t in top:
        names += [f"{t}/{s}" for s in groups[t]] if t in groups else [t]
    return names
