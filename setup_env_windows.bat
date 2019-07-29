@echo off

echo Delete env\ folder
rd /s /q "%~dp0env"

echo:
echo Create new env
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
pip install -r requirements.txt

echo:
echo Done!
