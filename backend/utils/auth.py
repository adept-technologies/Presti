import os
import jwt
import httpx
from functools import wraps
from dotenv import load_dotenv
from quart import request, jsonify
import logging

# Pull strictly from env variables injected by Docker
load_dotenv()
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")
ALGORITHMS = ["RS256"]

# Cache the jwks avoid hitting auth0's servers on each request
_jwks_cache: dict = {}

async def get_jwks()->dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        jwks_res = await client.get(jwks_url)
        jwks_res.raise_for_status()

    _jwks_cache = jwks_res.json()
    return _jwks_cache

async def get_auth0_public_key(token):
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}

    jwks = await get_jwks() 
    
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        return jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)
    raise Exception("Unable to find appropriate key")

def requires_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            return jsonify({"Error": "Authorization header is expected"}), 401

        parts = auth_header.split()
        if parts[0].lower() != "bearer" or len(parts) != 2:
            return jsonify({"Error": "Authorization header must be Bearer token"}), 401

        token = parts[1]
        try:
            public_key = await get_auth0_public_key(token)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/",
                leeway=30 # 30 seconds of clock skew allowance
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"Error": "Token is expired"}), 401
        except jwt.InvalidAudienceError:
            return jsonify({"Error": "Incorrect claims, please check the audience"}), 401
        except Exception as e:
            logging.error(f"JWT decode error: {type(e).__name__}: {str(e)}")
            return jsonify({"Error": f"Unable to parse authentication token: {str(e)}"}), 401

        # Extract the email using the Audience first, then fallback to lead gen namespace
        payload['email'] = (
            payload.get(f'{API_AUDIENCE}/email') or
            payload.get('https://adept.api/email') or
            ''
        )
        request.user = payload
        return await f(*args, **kwargs)
    return decorated
