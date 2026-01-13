"""Row detection logic for identifying header rows and trailing metadata rows."""

from typing import Optional, Union
import pandas as pd
import re

from .schema import SPORT_PASSPORT_SCHEMA, get_required_fields


# Summary keywords that indicate a row is not data
SUMMARY_KEYWORDS = [
    "total", "sum", "summary", "subtotal", "grand total",
    "count", "average", "avg", "mean", "maximum", "minimum",
    "note", "notes", "footer", "end of", "page", "continued"
]


def detect_header_row(
    data: Union[pd.DataFrame, list[list[str]]],
    min_matches: int = 3
) -> Optional[int]:
    """
    Detect the header row by scanning for expected column headers.
    
    Args:
        data: DataFrame or list of rows to scan
        min_matches: Minimum number of column header matches required
        
    Returns:
        Index of the header row (0-based), or None if not found
    """
    # Convert DataFrame to list of rows if needed
    if isinstance(data, pd.DataFrame):
        rows = [row.values.tolist() for _, row in data.iterrows()]
    else:
        rows = data
    
    # Get all expected column headers (with and without asterisks)
    expected_headers = []
    for spec in SPORT_PASSPORT_SCHEMA:
        header = spec.column_header
        expected_headers.append(header)
        # Also check without asterisk
        if header.endswith('*'):
            expected_headers.append(header.rstrip('*'))
    
    # Normalize headers for comparison (lowercase, strip)
    normalized_expected = [h.lower().strip() for h in expected_headers]
    
    # Scan rows from top
    for row_idx, row in enumerate(rows):
        # Convert row to list of strings
        row_values = [str(cell).strip() if cell is not None else "" for cell in row]
        
        # Count matches with expected headers
        matches = 0
        for value in row_values:
            value_normalized = value.lower().strip()
            # Check for exact match or partial match (header contains value or vice versa)
            for expected in normalized_expected:
                if value_normalized == expected:
                    matches += 1
                    break
                # Also check if one contains the other (for variations)
                elif expected in value_normalized or value_normalized in expected:
                    # Only count if it's a substantial match (not just a single letter)
                    if len(value_normalized) >= 3 and len(expected) >= 3:
                        matches += 1
                        break
        
        if matches >= min_matches:
            return row_idx
    
    # Fallback: pattern matching - look for row with mostly text that looks like headers
    return _detect_header_by_pattern(rows)


def _detect_header_by_pattern(rows: list[list[str]]) -> Optional[int]:
    """
    Fallback header detection using pattern matching.
    Looks for rows that are mostly text (not numbers/dates) and have reasonable length.
    """
    for row_idx, row in enumerate(rows[:20]):  # Only check first 20 rows
        if not row:
            continue
        
        # Convert to strings
        row_values = [str(cell).strip() if cell is not None else "" for cell in row]
        non_empty = [v for v in row_values if v]
        
        if len(non_empty) < 3:
            continue
        
        # Check if values look like headers (mostly text, title case, etc.)
        header_like_count = 0
        for value in non_empty[:10]:  # Check first 10 non-empty values
            # Headers are usually:
            # - Title case or all caps
            # - Not numbers
            # - Not dates
            # - Not empty
            if not value:
                continue
            
            # Skip if it's clearly a number
            try:
                float(value.replace(',', ''))
                continue
            except ValueError:
                pass
            
            # Skip if it's clearly a date
            if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', value):
                continue
            
            # If it's title case, all caps, or has spaces (likely multi-word header)
            if (value.istitle() or value.isupper() or ' ' in value) and len(value) > 2:
                header_like_count += 1
        
        # If most values look like headers, this is likely the header row
        if header_like_count >= min(3, len(non_empty) * 0.5):
            return row_idx
    
    return None


def detect_trailing_rows(
    data: Union[pd.DataFrame, list[list[str]]],
    header_row_idx: int = 0
) -> Optional[int]:
    """
    Detect trailing rows that should be removed (empty rows, summary rows, etc.).
    
    Args:
        data: DataFrame or list of rows to scan
        header_row_idx: Index of the header row (to know where data starts)
        
    Returns:
        Index of the last valid data row (inclusive), or None if no trailing rows detected
    """
    # Convert DataFrame to list of rows if needed
    if isinstance(data, pd.DataFrame):
        rows = [row.values.tolist() for _, row in data.iterrows()]
    else:
        rows = data
    
    if len(rows) <= header_row_idx + 1:
        return None  # No data rows to check
    
    # Start from the bottom and work up
    last_valid_idx = len(rows) - 1
    
    # Skip trailing empty rows
    for i in range(len(rows) - 1, header_row_idx, -1):
        row = rows[i]
        if _is_empty_row(row):
            last_valid_idx = i - 1
        else:
            break
    
    # Check for summary rows (rows that don't look like data)
    for i in range(last_valid_idx, header_row_idx, -1):
        row = rows[i]
        if not _is_likely_data_row(row):
            last_valid_idx = i - 1
        else:
            break
    
    # If we removed any rows, return the last valid index
    if last_valid_idx < len(rows) - 1:
        return last_valid_idx
    
    return None


def _is_empty_row(row: list) -> bool:
    """Check if a row is empty (all cells are empty/whitespace/None)."""
    if not row:
        return True
    
    for cell in row:
        if cell is not None:
            value = str(cell).strip()
            if value:
                return False
    
    return True


def _is_likely_data_row(row: list) -> bool:
    """
    Determine if a row looks like actual data (not a summary/metadata row).
    
    A data row should:
    - Have a reasonable number of non-empty cells (>30% filled)
    - Not contain summary keywords
    - Not be mostly empty
    """
    if not row:
        return False
    
    # Convert to strings
    row_values = [str(cell).strip() if cell is not None else "" for cell in row]
    non_empty = [v for v in row_values if v]
    
    # Too few non-empty cells - likely not data
    if len(non_empty) < len(row) * 0.3:
        return False
    
    # Check for summary keywords
    row_text = " ".join(row_values).lower()
    for keyword in SUMMARY_KEYWORDS:
        if keyword in row_text:
            return False
    
    # Check if row looks like a summary (e.g., all numbers in certain columns)
    # This is a heuristic - if most values are numbers, might be a summary row
    numeric_count = 0
    for value in non_empty[:5]:  # Check first 5 non-empty values
        try:
            float(value.replace(',', '').replace('£', '').replace('$', ''))
            numeric_count += 1
        except ValueError:
            pass
    
    # If all first few values are numbers, might be a summary row
    # But we need at least one text value (like a name) to be confident it's data
    if len(non_empty) >= 5 and numeric_count == len(non_empty[:5]):
        # Check if there's any text that looks like a name
        has_name_like = False
        for value in non_empty:
            # Names usually have letters and might have spaces
            if re.search(r'[a-zA-Z]{2,}', value) and not re.match(r'^\d+[/-]\d+', value):
                has_name_like = True
                break
        
        if not has_name_like:
            return False
    
    return True


def detect_rows_to_remove(
    data: Union[pd.DataFrame, list[list[str]]],
    min_header_matches: int = 3
) -> tuple[Optional[int], Optional[int]]:
    """
    Detect both header row and trailing rows to remove.
    
    Args:
        data: DataFrame or list of rows to scan
        min_header_matches: Minimum column header matches for header detection
        
    Returns:
        Tuple of (header_row_idx, last_valid_row_idx)
        - header_row_idx: Index of header row (rows before this will be removed)
        - last_valid_row_idx: Index of last valid data row (rows after this will be removed)
        Either can be None if no removal needed
    """
    header_row_idx = detect_header_row(data, min_header_matches)
    
    if header_row_idx is None:
        # If we can't find a header, assume first row is header
        header_row_idx = 0
    
    last_valid_idx = detect_trailing_rows(data, header_row_idx)
    
    return (header_row_idx, last_valid_idx)
