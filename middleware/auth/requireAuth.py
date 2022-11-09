from functools import wraps
from flask import app, g, request, redirect, url_for, flash
import jwt
from flask import jsonify, request

from services.auth.jwtVerify import try_decode_token
from services.auth.jwt_user_info import set_user_info



def auth_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):

        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']

        if not token:
            return flash('a valid token is missing')

        if token.startswith('Bearer '):
            token = token.replace('Bearer ', '')

        try:
            decoded_token = try_decode_token(token)
            set_user_info(decoded_token)
        except:
            return flash('token is invalid')
    
        return f(*args, **kwargs)
    return decorator