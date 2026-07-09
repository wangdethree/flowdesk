import os


def get_env(name, default=None, required=False):
    """读取字符串环境变量。

    项目配置统一通过这个函数读取，而不是在 settings.py 里到处写 os.environ.get。
    这样做有两个好处：
    - 读取规则集中，后续要加日志、类型转换或错误提示时只改这里。
    - settings.py 更像“配置声明”，不会混入太多环境变量解析细节。
    """

    value = os.environ.get(name)
    if value is None or value == '':
        if required and default is None:
            raise RuntimeError(f'缺少必要环境变量：{name}')
        return default
    return value


def get_bool_env(name, default=False):
    """读取布尔环境变量。

    环境变量本质上都是字符串，所以 DEBUG=false 如果不转换，在 Python 里仍然是真值。
    这里明确约定常见的 true/false 写法，避免生产环境误把 DEBUG 打开。
    """

    value = get_env(name)
    if value is None:
        return default

    normalized_value = value.strip().lower()
    if normalized_value in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized_value in {'0', 'false', 'no', 'off'}:
        return False

    raise RuntimeError(f'环境变量 {name} 不是合法布尔值：{value}')


def get_list_env(name, default=None, separator=','):
    """读取列表型环境变量。

    例如：
    ALLOWED_HOSTS=localhost,127.0.0.1

    会被解析成：
    ['localhost', '127.0.0.1']
    """

    value = get_env(name)
    if value is None:
        return default if default is not None else []

    return [item.strip() for item in value.split(separator) if item.strip()]
