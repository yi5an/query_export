import csv
from typing import List, Any
from pathlib import Path


class CSVHandler:
    """CSV 导出处理器"""

    @staticmethod
    async def write(columns: List[str], rows: List[List[Any]], output_path: str) -> int:
        """
        将数据写入 CSV 文件

        Args:
            columns: 列名列表
            rows: 数据行列表
            output_path: 输出文件路径

        Returns:
            写入的行数
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        return len(rows)

    @staticmethod
    def get_content_type() -> str:
        """获取 MIME 类型"""
        return "text/csv"

    @staticmethod
    def get_extension() -> str:
        """获取文件扩展名"""
        return ".csv"
