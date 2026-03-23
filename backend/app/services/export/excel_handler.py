import xlsxwriter
from typing import List, Any
from pathlib import Path
from datetime import datetime


class ExcelHandler:
    """Excel 导出处理器"""

    @staticmethod
    def _convert_value(value: Any) -> Any:
        """转换值为 Excel 兼容格式"""
        if isinstance(value, datetime):
            # 移除时区信息并转为字符串
            return value.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
        return value

    @staticmethod
    async def write(columns: List[str], rows: List[List[Any]], output_path: str) -> int:
        """
        将数据写入 Excel 文件

        Args:
            columns: 列名列表
            rows: 数据行列表
            output_path: 输出文件路径

        Returns:
            写入的行数
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        workbook = xlsxwriter.Workbook(output_path, {'in_memory': True, 'remove_timezone': True})
        worksheet = workbook.add_worksheet()

        # 创建表头样式
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })

        # 写入表头
        for col_idx, col_name in enumerate(columns):
            worksheet.write(0, col_idx, col_name, header_format)

        # 写入数据
        for row_idx, row in enumerate(rows, start=1):
            for col_idx, value in enumerate(row):
                worksheet.write(row_idx, col_idx, ExcelHandler._convert_value(value))

        # 自动调整列宽
        for col_idx, col_name in enumerate(columns):
            max_length = len(str(col_name))
            for row in rows:
                if row[col_idx]:
                    max_length = max(max_length, len(str(row[col_idx])))
            worksheet.set_column(col_idx, col_idx, min(max_length + 2, 50))

        workbook.close()
        return len(rows)

    @staticmethod
    def get_content_type() -> str:
        """获取 MIME 类型"""
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @staticmethod
    def get_extension() -> str:
        """获取文件扩展名"""
        return ".xlsx"
