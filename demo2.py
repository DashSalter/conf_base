from conf_base import ConfigMeta, Section, crypto


class TestConfig(metaclass=ConfigMeta):
    _crypto = crypto.PlainCrypto('mysql_settings.json')

    mysql = Section('Mysql')
    host = mysql.add('host', '127.0.0.1')
    port = mysql.add('port', 3306)
    user = mysql.add('user', 'root')
    password = mysql.add('password', '<PASSWORD>')


print(TestConfig.host)  # <class 'Mysql:host'>
print(TestConfig.host.value)  # 127.0.0.1

TestConfig.host.value = '11.11.11.101'
print(TestConfig.host.value)  # 11.11.11.101

TestConfig.host.set_value('33.33.33.101')
print(TestConfig.host.value)  # 33.33.33.101
