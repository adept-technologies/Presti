import os
import jwt
import httpx
from functools import wraps
from quart import request, jsonify

# Pull strictly from env variables injected by Docker
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")
ALGORITHMS = ["RS256"]

async def get_auth0_public_key(token):
    # Yes, we are using JWKS here!
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        jwks_res = await client.get(jwks_url)
    jwks = jwks_res.json()
    
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}
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
                issuer=f"https://{AUTH0_DOMAIN}/"
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"Error": "Token is expired"}), 401
        except jwt.InvalidAudienceError:
            return jsonify({"Error": "Incorrect claims, please check the audience"}), 401
        except Exception as e:
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
