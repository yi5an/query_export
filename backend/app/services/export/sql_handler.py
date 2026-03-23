from pathlib import Path
from typing import Any, List


class SQLHandler:
    """SQL 导出处理器，导出为包含原始查询的 .sql 文件。"""

    @staticmethod
    async def write(columns: List[str], rows: List[List[Any]], output_path: str, sql_text: str) -> int:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        content = sql_text.strip()
        if content and not content.endswith(";"):
            content = f"{content};"
        content += "\n"

        output_file.write_text(content, encoding="utf-8")
        return len(rows)

    @staticmethod
    def get_content_type() -> str:
        return "application/sql"

    @staticmethod
    def get_extension() -> str:
        return ".sql"
