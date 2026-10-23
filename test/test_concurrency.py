"""多进程并发写入：验证 filelock 互斥与原子替换不会损坏配置文件。

注意断言语义：不同进程各自持有内存快照，跨进程写同一份配置无法合并，
因此这里只断言「文件始终可解析、无残留临时文件、进程无异常」，
而不是「所有写入都被保留」。
"""

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# filelock 是可选依赖：未安装时 ConfigFile 会静默降级为仅线程锁，
# 这条路径无法验证多进程互斥，直接跳过整个模块
pytest.importorskip('filelock')

PROCESS_COUNT = 3
WRITE_COUNT = 10

CHILD_SCRIPT = '''
import sys
sys.path.insert(0, __ROOT__)
from conf_base import ConfigBase, Section


class C(ConfigBase):
    _path = __PATH__
    s = Section('S')
    value = s.field(default='init')


tag = sys.argv[1]
for i in range(__WRITES__):
    C.value.value = tag + '-' + str(i)
'''


def _run_children(path: str) -> None:
    """启动多个子进程同时写同一配置文件，任一进程失败即判失败。"""
    script = (
        CHILD_SCRIPT
        .replace('__ROOT__', repr(ROOT))
        .replace('__PATH__', repr(path))
        .replace('__WRITES__', str(WRITE_COUNT))
    )
    procs = [
        subprocess.Popen(
            [sys.executable, '-c', script, f'p{index}'],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(PROCESS_COUNT)
    ]
    for index, proc in enumerate(procs):
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, (
            f'子进程 p{index} 退出码 {proc.returncode}\nstdout: {out}\nstderr: {err}'
        )


class TestMultiProcessLock:

    def test_parallel_writers_keep_file_valid(self, tmp_dir):
        path = os.path.join(tmp_dir, 'shared.json')
        _run_children(path)

        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        expected = {f'p{n}-{i}' for n in range(PROCESS_COUNT) for i in range(WRITE_COUNT)}
        assert data['S']['value'] in expected
        assert isinstance(data['_schema_version'], int)

    def test_no_temp_file_left_behind(self, tmp_dir):
        path = os.path.join(tmp_dir, 'cleanup.json')
        _run_children(path)

        # 每次写入都走 'xxx.json.tmp' + os.replace，任一进程中途崩溃都可能留下半成品；
        # 这里确认所有子进程正常结束后没有残留
        assert not os.path.exists(path + '.tmp')
