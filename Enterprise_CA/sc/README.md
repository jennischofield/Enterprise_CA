
To run this code, follow these steps:

  

1) Configure VENV:

- In a terminal connected to one of the Lovelace computers, run the following commands:

	- rm -rf venv

	- python3 -m venv venv

	- source venv/bin/activate	

	- (venv) python3 -m pip install flask

	- (venv) python3 -m pip install requests

- This has now configured the venv and packages

2) Set FBASE

- Based on the name of your firebase realtime database (already set up at firebase.com), run the following command:

	- export FBASE="{name of db}"

- You can verify this worked by running:

	- python3

		- import os

		- print(os.getenv("FBASE"))

- It should display your environment variable. If it doesn't set, the code will default to using a sqlite database.

3) Run code:

- You can run the code using a firebase database or sqlite database:

	- python3 sc.py -r firebase

	- python3 sc.py -r sqlite

- Anything other than those options will not work.

4) You can now run bash scripts and curl commands on the code.
