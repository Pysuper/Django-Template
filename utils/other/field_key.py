import inflection


def convert_dict_keys_to_camel_case(data):
    """
    将字典中的键转换为驼峰命名法
    :param data: 字典数据
    :return: 转换后的字典数据
    """
    # 判断数据类型是否为字典
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            # 仅在需要时转换键
            new_key = inflection.camelize(k, uppercase_first_letter=False) if '_' in k else k
            # 递归转换字典中的值
            new_data[new_key] = convert_dict_keys_to_camel_case(v)
        return new_data
    # 判断数据类型是否为列表
    elif isinstance(data, list):
        # 递归转换列表中的每一项
        return [convert_dict_keys_to_camel_case(item) for item in data]
    else:
        # 返回原始数据
        return data
