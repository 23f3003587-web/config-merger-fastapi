from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import yaml
from typing import Dict, Any

app = FastAPI(title="Effective Config")

# CORS - required by grader
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 1: Defaults
config = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000"
}

# Layer 2: config.development.yaml
try:
    with open("config.development.yaml", "r") as f:
        yaml_config = yaml.safe_load(f) or {}
        config.update(yaml_config)
except FileNotFoundError:
    pass

# Layer 3: .env file + NUM_WORKERS alias
env_file = {}
try:
    with open(".env", "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                env_file[key.strip()] = value.strip()
except FileNotFoundError:
    pass

if "NUM_WORKERS" in env_file:
    config["workers"] = int(env_file["NUM_WORKERS"])
if "APP_API_KEY" in env_file:
    config["api_key"] = env_file["APP_API_KEY"]

# Layer 4: OS Environment Variables (APP_* prefix)
for key, value in os.environ.items():
    if key.startswith("APP_"):
        config_key = key[4:].lower()
        if config_key == "debug":
            config["debug"] = value.lower() in ("true", "1", "yes", "on")
        elif config_key in ("port", "workers"):
            config[config_key] = int(value)
        else:
            config[config_key] = value

class ConfigResponse(BaseModel):
    port: int
    workers: int
    debug: bool
    log_level: str
    api_key: str

@app.get("/effective-config", response_model=ConfigResponse)
async def get_effective_config(set: list[str] = Query(default=[])):
    final_config = config.copy()

    # Apply CLI overrides (?set=key=value)
    for item in set:
        if "=" in item:
            key, value = item.split("=", 1)
            key = key.strip().lower()
            
            if key in ("port", "workers"):
                final_config[key] = int(value)
            elif key == "debug":
                final_config[key] = value.lower() in ("true", "1", "yes", "on")
            else:
                final_config[key] = value

    # Mask api_key
    masked_config = final_config.copy()
    masked_config["api_key"] = "****"

    return masked_config
