import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from django.http.response import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

'''
# 这里使用drf_excel处理Excel数据
class DemosViewSet(ReadOnlyModelViewSet):
    """任务管理"""

    queryset = Results.objects.all().prefetch_related(
        Prefetch("executor", queryset=User.objects.select_related("dept__pid"))
    )
    serializer_class = ResultsListSerializer
    renderer_classes = [XLSXRenderer]

    def _get_cached_results(self, cache_key):
        """从缓存获取或生成并缓存数据"""
        items = cache.get(cache_key)
        if not items:
            items = [
                {
                    "id": item.id,
                    "username": executor.nick_name,
                    "college": executor.dept.pid.name if executor.dept.pid else None,
                    "major": executor.dept.name,
                    "gender": "男" if executor.gender == 1 else "女",
                    "code": executor.username,
                    "depression": item.depression,
                    "anxiety": item.anxiety,
                    "A": per_list[0],
                    "B": per_list[1],
                    "C": per_list[2],
                    "D": per_list[3],
                    "E": per_list[4],
                    "bipolar_disorder": item.bipolar_disorder,
                }
                for item in self.queryset
                if (executor := item.executor.first()) and (per_list := ast.literal_eval(item.personality))
            ]
            cache.set(cache_key, items, timeout=360000)  # 缓存1小时
        return items

    def list(self, request, *args, **kwargs):
        """
        展示测试数据
        :param request: 请求对象
        :return: 检索后的分页数据或导出数据
        """
        dept_id = request.query_params.get("deptId")
        username = request.query_params.get("blurry")
        gender = request.query_params.get("gender")
        query = Q()
        if dept_id:
            search_dept = Dept.objects.get(id=int(dept_id))
            dept_ids = cache.get(f"dept_ids_{search_dept.id}")
            if not dept_ids:
                dept_ids = get_all_sub_depts(search_dept) + [dept_id]
                cache.set(f"dept_ids_{search_dept.id}", dept_ids, timeout=3600)  # 缓存1小时
            query &= Q(executor__dept_id__in=dept_ids)
        if username:
            query &= Q(executor__nick_name__icontains=username)
        if gender:
            query &= Q(executor__gender=gender)

        self.queryset = self.queryset.filter(query)

        if "export" in request.GET:
            self.renderer_classes = [XLSXRenderer]
            items = self._get_cached_results(f"results_{dept_id}_{username}_{gender}")
            return Response(items)
        else:
            page = int(request.query_params.get("page", 1))
            size = int(request.query_params.get("size", 10))
            paginated_results = self.queryset[(page - 1) * size : page * size]

            items = [
                {
                    "id": item.id,
                    "username": executor.nick_name,
                    "college": executor.dept.pid.name if executor.dept.pid else None,
                    "major": executor.dept.name,
                    "gender": executor.gender,
                    "code": executor.username,
                    "depression": float(item.depression) if item.depression is not None else None,
                    "anxiety": float(item.anxiety) if item.anxiety is not None else None,
                    "A": per_list[0],
                    "B": per_list[1],
                    "C": per_list[2],
                    "D": per_list[3],
                    "E": per_list[4],
                    "bipolar_disorder": float(item.bipolar_disorder) if item.bipolar_disorder is not None else None,
                }
                for item in paginated_results
                if (executor := item.executor.first()) and (per_list := ast.literal_eval(item.personality))
            ]

            return XopsResponse(
                data={
                    "content": items,
                    "totalElements": self.queryset.count(),
                    "page": page,
                    "size": size,
                },
                status=status.HTTP_200_OK,
            )

    @action(methods=["POST"], detail=False)
    def download(self, request):
        """下载数据"""
        request.GET = request.GET.copy()
        request.GET["export"] = "1"
        return self.list(request)
'''


# 获取表格单元格的类型并返回字符类型
def get_cell_value(cell: Any) -> str:
    """
    获取单元格的值并转换为字符串
    :param cell: 单元格对象
    :return: 字符串格式的单元格值
    """
    if isinstance(cell, (int, float)):
        return str(int(cell)).strip()
    return str(cell).strip()


# action获取通用设置更新人和更新时间
def get_update_params(request, is_create: bool = False) -> Dict:
    """
    获取更新参数
    :param request: 请求对象
    :param is_create: 是否为创建操作
    :return: 包含更新信息的字典
    """
    now = datetime.now()
    params = {"update_by": request.user, "update_date": now}
    if is_create:
        params.update({"create_by": request.user, "create_date": now})
    return params


# 基于 pandas DataFrame 下载 Excel
def pandas_download_excel(
    data: Union[List[Dict], pd.DataFrame], filename: str = None, sheet_name: str = "Sheet1", index: bool = False
) -> HttpResponse:
    """
    使用pandas导出Excel文件
    :param data: 要导出的数据
    :param filename: 文件名
    :param sheet_name: 工作表名称
    :param index: 是否包含索引
    :return: HTTP响应对象
    """
    # df = pd.DataFrame(list(serializer_data))
    # response = HttpResponse(content_type="application/msexcel")
    # with pd.ExcelWriter(response, engine="openpyxl") as writer:
    #     df.to_excel(writer, index=False, sheet_name="Users")
    # return response

    try:
        if not isinstance(data, pd.DataFrame):
            df = pd.DataFrame(data)
        else:
            df = data

        response = HttpResponse(content_type="application/vnd.ms-excel")
        if filename:
            response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'

        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, index=index, sheet_name=sheet_name)

        return response
    except Exception as e:
        logger.error(f"导出Excel失败: {str(e)}")
        raise


def read_excel(
    file_path: str,
    sheet_name: Optional[Union[str, int]] = 0,
    skiprows: int = 0,
    usecols: Optional[List] = None,
) -> pd.DataFrame:
    """
    读取Excel文件
    :param file_path: Excel文件路径
    :param sheet_name: 工作表名称或索引
    :param skiprows: 跳过的行数
    :param usecols: 使用的列
    :return: DataFrame对象
    """
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skiprows, usecols=usecols)
    except Exception as e:
        logger.error(f"读取Excel失败: {str(e)}")
        raise


def create_styled_excel(
    data: List[Dict], headers: List[str], filename: str, sheet_name: str = "Sheet1"
) -> HttpResponse:
    """
    创建带样式的Excel文件
    :param data: 数据列表
    :param headers: 表头列表
    :param filename: 文件名
    :param sheet_name: 工作表名称
    :return: HTTP响应对象
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # 设置表头样式
    header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    header_font = Font(bold=True)
    header_alignment = Alignment(horizontal="center", vertical="center")

    # 写入表头
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment

    # 写入数据
    for row, item in enumerate(data, 2):
        for col, key in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=item.get(key, ""))
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # 调整列宽
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 15

    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    wb.save(response)
    return response


def merge_excel_files(file_paths: List[str], output_path: str) -> None:
    """
    合并多个Excel文件
    :param file_paths: Excel文件路径列表
    :param output_path: 输出文件路径
    """
    try:
        dfs = []
        for file_path in file_paths:
            df = pd.read_excel(file_path)
            dfs.append(df)

        merged_df = pd.concat(dfs, ignore_index=True)
        merged_df.to_excel(output_path, index=False)
    except Exception as e:
        logger.error(f"合并Excel文件失败: {str(e)}")
        raise


# -------- https://mp.weixin.qq.com/s/oi609jepfEYF3TjnWzFRjw --------
#
import string
import xlsxwriter


def export_to_excel(filename, col_items, datas):
    """将信息导出为excel文件并返回给前端

    Args:
        filename (str): 文件名
        col_items (list): 列名
        datas (list): 数据信息

    Returns:
        HttpResponse: 包含excel文件的响应对象
    """
    import io

    # 创建一个内存中的文件对象
    output = io.BytesIO()

    # 生成.xlsx文件
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})

    # 设置sheet页签名称
    table = workbook.add_worksheet(filename)

    # 定义格式
    header_format = workbook.add_format(
        {
            "align": "center",
            "bg_color": "gray",
            "color": "white",
            "font": "宋体",
            "bold": True,
            "border": 1,
        }
    )
    data_format = workbook.add_format({"align": "center", "border": 1, "font_name": "Calibri Light"})

    # 设置列名及宽度
    for idx, (col_name, col_width) in enumerate(col_items):
        col_code = string.ascii_uppercase[idx]
        table.write(0, idx, col_name, header_format)
        table.set_column(f"{col_code}:{col_code}", col_width)

    # 写入数据
    for row, item in enumerate(datas, start=1):
        for col, value in enumerate(item):
            table.write(row, col, value, data_format)

    # 关闭工作簿
    workbook.close()

    # 将文件指针移动到开始位置
    output.seek(0)

    # 创建HttpResponse对象并返回
    response = HttpResponse(output, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    # response["Content-Disposition"] = f"attachment; filename={filename}.xlsx"
    return response


#
# if __name__ == "__main__":
#
#     # 构造数据
#     faker_obj = Faker(locale="zh")
#
#     # 文件名
#     filename = "人员名单"
#
#     # 列名
#     cols = [("序号", 10), ("姓名", 20)]
#
#     # 构造数据
#     datas = []
#     for i in range(10):
#         datas.append((i + 1, faker_obj.name()))
#
#     # 将数据信息导出到excel文件中
#     export_to_excel(filename, cols, datas)
#
# import time
# from openpyxl import Workbook
# from django.http import HttpResponse
# from myapp.models import User
#
# def export_data(request):
#     # 记录开始时间
#     start_time = time.time()
#
#     # 获取数据
#     data = User.objects.all()[:10000]
#
#     # 创建 Excel 文件
#     wb = Workbook()
#     ws = wb.active
#     ws.append(['姓名', '学号', '性别', '手机'])
#
#     # 流式写入数据
#     for user in data.iterator():  # 使用 iterator 避免一次性加载所有数据
#         ws.append([user.nick_name, user.username, user.gender, user.phone])
#
#     # 将文件作为 HTTP 响应返回
#     response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
#     response['Content-Disposition'] = 'attachment; filename=users.xlsx'
#     wb.save(response)
#
#     # 记录结束时间并输出
#     end_time = time.time()
#     print(f"Excel 写入并返回耗时：{end_time - start_time:.2f} 秒")
#
#     return response
