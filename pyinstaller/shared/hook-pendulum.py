from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("pendulum.locales", include_py_files=True)
