from setuptools import setup

setup(
    author="czp",
    author_email="blackandrechen@gmail.com",
    name="taobao_crawled",
    version="0.2.0",
    url = "https://github.com/blackandrechen/taobao_crawled",
    py_modules=['youdao', 'requests'],
    description="Query words meanings via the command line",
    entry_points={
        'console_scripts':['wd=youdao:command_line_runner']
    }
)