# Benchmark evidence

本地预发布 Value Gate，2026-08-11：

- Linux x86-64；
- CPython 3.12.13；
- Oracle：`python-dotenv==1.2.2` 固定源码；
- Candidate：当前 checkout 的 release Rust extension；
- Oracle 与 Candidate 在两个独立子进程、两个不同 `PYTHONPATH` 中运行；
- 计时前比较 `OrderedDict` 类型、键顺序和值；
- warmup 2 次，采样 7 次，表格报告中位数。

| Workload | Bytes | Oracle median | Candidate median | Speedup |
|---|---:|---:|---:|---:|
| 20 lines | 318 | 1,146.800 µs | 71.868 µs | 15.957× |
| 1,000 lines | 17,794 | 69,633.380 µs | 1,366.284 µs | 50.966× |
| ~100 KB | 97,790 | 591,698.924 µs | 6,677.670 µs | 88.609× |

复现命令：

```bash
python tests/benchmark.py --repeats 7 --warmup 2 --iterations 1000
```

该结果只衡量内存 `StringIO` 的 `dotenv_values()` CPU 解析路径，不衡量文件 I/O、
进程启动、应用冷启动或其他操作系统。它也不是 macOS/Windows 或所有真实 workload 的
结论。公开宣传跨平台性能之前，仍需在已发布 wheel 和真实下游 workload 上重复验证。
