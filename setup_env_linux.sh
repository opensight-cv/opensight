#!/usr/bin/env bash

echo Delete env/ folder
rm -fdrv env

echo
echo Create new env
python3 -m venv env

echo
echo Activate env
source env/bin/activate

echo
echo Update package manager
python3 -m pip install -U pip
python3 -m pip install -U setuptools wheel

echo
echo Install dependencies
pip install -r requirements.txt

echo
echo Done!
