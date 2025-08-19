![example workflow](https://github.com/AberdeenRSS/FlightManagementServer/actions/workflows/deploy_to_server.yml/badge.svg)
![example_workflow](https://github.com/AberdeenRSS/FlightManagementServer/actions/workflows/test.yml/badge.svg)


# Introduction

The Flight Management Server is a cloud service that handles all data produced by vessels during a flight. This includes the storing and live forwarding of all measurement data as well as dispatching commands to the vessels.   

We are currently hosting the api at [https://api.uoarocketry.org](https://api.uoarocketry.org)   
Click [here](https://api.uoarocketry.org/docs) for the auto generated api documentation

The app is currently hosted at [https://aberdeenrss.github.io/FlightManagementClient/](https://aberdeenrss.github.io/FlightManagementClient/)

## Build

To build the project youself follow these steps:

1. Create a virtual environment with python 3.9 or above
2. Install all required packages using `pip install -r requirements.txt` within your venv
3. Change settings as required in `/app/config.py` (config values can be changed through cmd, but this is sightly easier to begin with)

## Run

### VS Code
if you are using vscode you can just hit `F5` to start the preconfigured debugger 

### Any other environment

Use `python -m uvicorn app.main:app --reload` to start the server
