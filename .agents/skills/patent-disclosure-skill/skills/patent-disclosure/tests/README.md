# tests 目录说明

本目录是 **patent-disclosure** 的测试。CAD / mermaid / 公式 / 轻量查新都在这里。其他包的测试在各自 `tests/`。

## 运行

在**仓库根目录**（子包目录名含连字符，发现测试时用 `-t` 指到本包，不要用仓库根当 top）：

```bash
python -m unittest discover -s skills/patent-disclosure/tests -t skills/patent-disclosure -p "test_*.py"
```

联调国知局实网（非 unittest）：

```bash
python skills/patent-disclosure/tests/test_cnipa_epub_chain.py [关键词]
```
