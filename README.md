# MonolithStandlone
![](https://github.com/ktmdan/MonolithStandlone/workflows/Python%20application/badge.svg)

Monolith is a standalone web based python editor.  This project was created because we needed a way to run one off processes and have complete history of the code base.  This could easily be done with Git or the like but the advantage is that this can execute code off a central remote repository (this is still being worked on.)

All code is saved in a Sqllite3 database.

Code was originally designed to be compatible with IronPython 2.7, but this fork has been updated to run on standard Python 3 (and tested on macOS).

## How to run

### macOS / Linux / Windows (Python 3)

1. Install Python 3 (e.g. via Homebrew on macOS: `brew install python`).
2. Create and activate a virtual environment in the project folder:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the server:

   ```bash
   python MonolithStandalone.py
   ```

5. Open a browser to `http://localhost:8000`.

### Original IronPython 2.7 (Windows-only, legacy)

The original project targeted IronPython 2.7 and `pypyodbc` for remote database features. If you need that legacy setup on Windows, use the original instructions from upstream:

```bash
pip install pypyodbc
ipy MonolithStandalone.py
```

Then open a browser to `http://localhost:8000`.

To run an application designed in Monolith, where 5 is the codeid shown in the editor.
```
ipy -c "from PythonRunner import PythonRunner as pr;m=pr.PythonGetAndRun('5');print m.Test();"
```

## Custom Injected Commands
PythonGetAndRun(codeid) : get the code and return it as a script object
```
m = PythonGetAndRun(5)
r = m.Test()
LogError(r)
```

PythonGetAndRunDict(codeid,dict) : run the code adding dict to the global dictionary 
```
l = { 'version': 1 }
m = PythonGetAndRunDict(5,l)
r = m.Test()
LogError(r)
```

PythonGetCode(codeid) : Get just the code
```
code = PythonGetCode(5)
LogError(code)
```

LogError(msg) : Log an error to the console using print

![Alt](https://raw.githubusercontent.com/ktmdan/MonolithStandlone/master/docs/monolithscreenshot.png "Screenshot")
