from conf_base import ConfigMeta, Section, crypto


class TestConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainJson('mysql_settings.json')

    mysql = Section('Mysql')
    host = mysql.add('host', '127.0.0.1', read_only=False)
    port = mysql.add('port', 3306, validator=lambda x: x > 0)
    user = mysql.add('user', 'root')
    password = mysql.add('password', '<PASSWORD>')


# 配置块信息
print(TestConfig.mysql)  # <Section:Mysql [host=127.0.0.1, port=3306, user=root, password=<PASSWORD>]>
print(TestConfig.mysql.section_tuple)  # ('Mysql',)
print(TestConfig.mysql.get_options())  # ['host', 'port', 'user', 'password']

# 配置项信息
print(TestConfig.host)  # <class 'Mysql:host'>
print(TestConfig.host.section)  # Mysql
print(TestConfig.host.option)  # host
print(TestConfig.host.default)  # 127.0.0.1
print(TestConfig.host.value)  # 33.33.33.101

TestConfig.host.value = '11.11.11.101'
print(TestConfig.host.value)  # 11.11.11.101

TestConfig.host.set_value('33.33.33.101')
print(TestConfig.host.value)  # 33.33.33.101
