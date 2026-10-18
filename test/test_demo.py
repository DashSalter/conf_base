from conf_base import ConfigMeta, Section, crypto

"""
基础的修改 读取 重置功能测试
"""


class TestConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('mysql_settings.json')

    mysql = Section('Mysql')
    host = mysql.add('host', '127.0.0.1', read_only=False)
    port = mysql.add('port', 3306, validator=lambda x: x > 0)
    user = mysql.add('user', 'root')
    password = mysql.add('password', '<PASSWORD>')


print('配置块信息')
print(TestConfig.mysql)
print(TestConfig.mysql.section_tuple)  # ('Mysql',)
print(TestConfig.mysql.get_options())  # ['host', 'port', 'user', 'password']

print('\n配置项信息读取')
print(TestConfig.host)  # <class 'Mysql:host'>
print(TestConfig.host.section)  # Mysql
print(TestConfig.host.option)  # host
print(TestConfig.host.default)  # 127.0.0.1
print(TestConfig.host.value)  # 33.33.33.101

print('\n配置项信息修改')
TestConfig.host.value = '11.11.11.101'
print(TestConfig.host.value)  # 11.11.11.101
assert TestConfig.host.value == '11.11.11.101'

TestConfig.host.set_value('33.33.33.101')
print(TestConfig.host.value)  # 33.33.33.101
assert TestConfig.host.value == '33.33.33.101'

print('\n批量修改')
TestConfig.mysql.update(
    host='123.456.789.10',
    port=3333,
    user='root2',
    password='<PASSWORD2>',
)
print(TestConfig.mysql)  # 输出该配置块的修改后的全部数据
assert str(TestConfig.mysql) == '<Section: Mysql={host=123.456.789.10, port=3333, user=root2, password=<PASSWORD2>}>'

print(TestConfig.mysql.default_options)  # 获取默认配置
# {'host': '127.0.0.1', 'port': 3306, 'user': 'root', 'password': '<PASSWORD>'}

print('\n批量读取')
print(TestConfig.mysql.current_options)
assert (TestConfig.mysql.current_options ==
        {'host': '123.456.789.10',
         'port': 3333,
         'user': 'root2',
         'password': '<PASSWORD2>'}
        )

print('\n全部重置')
TestConfig.mysql.reset()
print(TestConfig.mysql)
assert str(TestConfig.mysql) == '<Section: Mysql={host=127.0.0.1, port=3306, user=root, password=<PASSWORD>}>'
