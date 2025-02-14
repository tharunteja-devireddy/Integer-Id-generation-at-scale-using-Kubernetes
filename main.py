

import os
import re
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from snowflake import SnowflakeGenerator

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import jwt

load_dotenv(dotenv_path="./dev.env")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Read environment variables
DEV_USERNAME = os.getenv("DEV_USERNAME", "devuser")
DEV_PASSWORD = os.getenv("DEV_PASSWORD", "devpass")
JWT_SECRET = os.getenv("JWT_SECRET", "mysecret")  # used to sign the JWT


# Extract node index from node name
CURRENT_NODE = os.getenv("NODE_NAME", "node-0")
node_match = re.search(r'(\d+)$', CURRENT_NODE)
DATACENTER_ID= int(node_match.group(1)) if node_match else 0

# Extract pod index from pod name
CURRENT_POD = os.getenv("POD_NAME", "id-generator-0")
pod_match = re.search(r'(\d+)$', CURRENT_POD)
WORKER_ID = int(pod_match.group(1)) if pod_match else 0

print(f"Node Details: {CURRENT_NODE} - {node_match} - {DATACENTER_ID}")
print(f"Pod Details: {CURRENT_POD} - {pod_match} - {WORKER_ID}")

MACHINE_ID = (DATACENTER_ID << 5) | WORKER_ID
EPOCH = 1739526270 # 2025-02-14 15:13:00


integer_id_generator = SnowflakeGenerator(
    instance=MACHINE_ID,
    epoch=EPOCH
)

# We will use OAuth2 with "password" flow (though we won't actually store hashed passwords in a DB).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# A simple Pydantic model to structure the JWT response
class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    Create a JWT token with an optional expiry.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)  # default 30 minutes
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def authenticate_user(username: str, password: str) -> bool:
    """
    Check username and password against environment variables.
    """
    return (username == DEV_USERNAME) and (password == DEV_PASSWORD)

def decode_token(token: str):
    """
    Decode the JWT token. Raises jwt exceptions if invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    FastAPI dependency that parses the token from the Authorization header
    and returns the current user information (from the JWT token).
    """
    payload = decode_token(token)
    user: str = payload.get("sub")
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.get("/health")
def health():
    return {
        "status": "OK",
        "node": CURRENT_NODE,
        "pod": CURRENT_POD,
        "worker_id": WORKER_ID,
        "datacenter_id": DATACENTER_ID,
        "machine_id": MACHINE_ID
    }

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 style login endpoint.
    Expects form fields: username, password
    If valid, returns a JWT token.
    """

    username = form_data.username
    password = form_data.password

    if not authenticate_user(username, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token with the subject being the username
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": username},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/generate-id")
def generate_id(current_user: str = Depends(get_current_user)):
    """
    Requires a valid JWT token. If valid, returns a new UUID.
    """
    new_id = str(uuid.uuid4())
    return {"uuid": new_id}


@app.get("/generate-id-integer")
def generate_id_integer(current_user: str = Depends(get_current_user)):
    """
    Requires a valid JWT token. If valid, returns a new integer.
    """
    return {"id": next(integer_id_generator)}


# uvicorn main:app --port 8000 --reload