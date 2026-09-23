# Contributing / 贡献指南

Thanks for your interest in **JSON Lab**. / 欢迎给 JSON Lab 提贡献。

## Development / 开发

```powershell
python main.py                 # run app
python -m unittest discover -s tests -v
```

Requirements: Python 3.10+ with `tkinter` (included in standard Windows installers).  
依赖：Python 3.10+，仅标准库（Windows 安装包自带 tkinter），无需 pip 安装第三方包。

## Build exe / 打包

```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --name "JSONLab" main.py
```

## Pull requests / 提交 PR

1. Fork and create a feature branch
2. Keep the app offline (no network calls)
3. Run tests before opening a PR
4. Prefer small, focused commits

## Code style / 代码风格

- Python 3.10+ type hints where helpful
- Keep UI strings in Chinese primary; English in README sections
- Do not commit tokens, binaries under `dist/`, or IDE junk
