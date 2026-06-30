from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import yaml
from typing import Dict, Any, List

app = FastAPI(title="Effective Config")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 1: Defaults
config: Dict[str, Any] = {
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

# Layer 3: .env + NUM_WORKERS alias
try:
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = [x.strip() for x in line.split("=", 1)]
                if key == "NUM_WORKERS":
                    config["workers"] = int(value)
                elif key == "APP_API_KEY":
                    config["api_key"] = value
except FileNotFoundError:
    pass

# Layer 4: OS Environment Variables (APP_* prefix)
for key, value in os.environ.items():
    if key.startswith("APP_"):
        config_key = key[4:].lower()
        if config_key == "debug":
            config["debug"] = value.lower() in ("true", "1", "yes", "on", "t")
        elif config_key in ("port", "workers"):
            try:
                config[config_key] = int(value)
            except ValueError:
                pass
        else:
            config[config_key] = value

class ConfigResponse(BaseModel):
    port: int
    workers: int
    debug: bool
    log_level: str
    api_key: str

@app.get("/effective-config", response_model=ConfigResponse)
async def get_effective_config(set: List[str] = Query(default=[])):
    final_config = config.copy()
    
    # HIGHEST precedence: CLI overrides ?set=key=value
    for item in set:
        if "=" in item:
            key, value = [x.strip() for x in item.split("=", 1)]
            key = key.lower()
            
            if key in ("port", "workers"):
                try:
                    final_config[key] = int(value)
                except ValueError:
                    pass
            elif key == "debug":
                final_config[key] = str(value).lower() in ("true", "1", "yes", "on", "t", "true")
            else:
                final_config[key] = value

    # Mask api_key
    masked_config = final_config.copy()
    masked_config["api_key"] = "****"
    
    return masked_config
