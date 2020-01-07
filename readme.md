#  Capybara

## Download

https://github.com/Helio-Wang/Capybara-app/releases/latest

You can find the binary executables of Capybara for the following OS:
- Microsoft Windows
- macOs
- Ubuntu (>=17.04)
- Arch Linux

Please note that no additional installation is required.


## Documentation

https://capybara-doc.readthedocs.io/en/latest


## License

CeCILL 2.1 (GPL compatible)


## Build

You may want to build the binary from source if
- You are not using one of the supported OS (Windows, macOS, Ubuntu, Arch), or
- You have made some changes to the source code.


First, clone or create the project directory:
```
cd capybara-app
```

Capybara includes a `Pipfile` specifying all requirements, generated by the virtual environment management tool Pipenv. Install Pipenv if you don't have it alreday:
```
pip install pipenv
```

Next, build the Pipenv virtual environment and install the requirements from `Pipfile`. Be sure that you already have Python 3.6 installed on your system. If you have multiple versions of Python, this command will automatically search for Python 3.6.
```
pipenv install
```

Then, you can execute the main script directly:
```
pipenv run python3 main.py
```

Alternatively, you can build and run the binary:
```
pipenv run python -OO -m PyInstaller main.py -F
dist/./main
```

Note that, although Pipenv automatically scans for the targeted Python version (Python 3.6), this may not give the desired result if you have multiple implementations of Python (for instance, CPython 3.6.8 and PyPy 3.6.9). In this case, you can specify the path to the correct Python version, for example:
```
pipenv --python /usr/bin/python3.6
```


