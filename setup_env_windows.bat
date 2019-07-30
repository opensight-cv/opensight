@echo off

echo Deleting env\ folder
rd /s /q "%~dp0env"

echo:
echo Creating new env
py -3 -m venv env

echo:
echo Activate env
"%~dp0env\Scripts\activate.bat"

echo:
echo Update package manager
python -m pip install -U pip
python -m pip install -U setuptools wheel

echo:
echo Install dependencies
pip install -r requirements_working.txt

echo:
echo Done!
