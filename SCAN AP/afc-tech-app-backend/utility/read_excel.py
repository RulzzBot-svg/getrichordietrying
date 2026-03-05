"""Utility for reading Excel files."""
import pandas as pd


def read_excel_sheets(path: str) -> list[str]:
    xls = pd.ExcelFile(path)
    return xls.sheet_names


def read_sheet(path: str, sheet_name: str, header_row: int = 4) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, header=header_row)
