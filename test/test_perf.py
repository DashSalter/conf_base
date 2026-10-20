"""性能基准测试：读取、单次落盘、批量落盘。

运行：python -m pytest test_perf.py -v
或：  python test_perf.py
"""

import os, sys, time, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conf_base import ConfigMeta, Section, crypto


def _bench(label, fn, warmup=50, runs=200):
    """执行 fn(runs)，打印平均耗时。"""
    for _ in range(warmup):
        fn()
    t0 = time.perf_counter()
    for _ in range(runs):
        fn()
    elapsed = time.perf_counter() - t0
    per = elapsed / runs
    if per < 1e-3:
        print(f"  {label:<20} {elapsed:.4f}s / {runs}次 = {per*1e6:.1f}µs/次")
    else:
        print(f"  {label:<20} {elapsed:.4f}s / {runs}次 = {per*1000:.2f}ms/次")
    return per


def run_benchmarks():
    tmp = os.path.join(tempfile.gettempdir(), 'bench_conf.json')

    class C(metaclass=ConfigMeta):
        _crypto = crypto.PlainJson(tmp)
        s = Section('S')
        port = s.add('port', default=8080)
        items = s.add('items', default=[1, 2, 3])
        db = s.add('db', default={'host': 'localhost', 'port': 5432})

    proxy = C.port
    jf = proxy._parent._config_file

    print("=== 读取性能（纯内存字典访问） ===")
    _bench("单值读取", lambda: C.port.value, runs=100000)
    _bench("三项连续读", lambda: (C.port.value, C.items.value, C.db.value), runs=100000)

    print("\n=== 写入性能（含文件落盘） ===")
    def single_write():
        C.port.value = C.port.value + 1
    _bench("单次落盘", single_write, runs=200)

    print("\n=== 批量写入（batch 合并落盘） ===")
    def batch_write():
        with jf.batch():
            C.port.value = C.port.value + 1
            C.items.append(0)
            C.db['port'] = C.db.value['port'] + 1
    _bench("batch 3项/批", batch_write, runs=200)

    print("\n=== update 批量写 ===")
    def update_write():
        C.s.update(port=1234, items=[1, 2], db={'host': 'x', 'port': 1})
    _bench("update 3项", update_write, runs=200)

    # 清理
    try:
        os.remove(tmp)
        os.remove(tmp + '.lock')
    except OSError:
        pass


if __name__ == '__main__':
    run_benchmarks()
