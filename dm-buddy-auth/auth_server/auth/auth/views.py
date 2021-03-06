# api/auth/views.py


from flask import Blueprint, request, make_response, jsonify
from flask.views import MethodView

from auth import bcrypt, db
from auth.db_access.models import User, BlacklistToken
import auth.auth_library

auth_blueprint = Blueprint('auth', __name__)


class RegisterAPI(MethodView):
    """
    User Registration Resource
    """

    def post(self):
        # get the post data
        post_data = request.get_json()
        # check if user already exists
        user = User.query.filter( (User.email==post_data.get('email')) | (User.username==post_data.get('username')) ).first()
        if not user:
            try:
                user = User(
                    email=post_data.get('email'),
                    password=post_data.get('password'),
                    username=post_data.get('username')
                )

                # insert the user
                db.session.add(user)
                db.session.commit()
                # generate the auth token
                refresh_token = user.encode_refresh_token(user.id)
                responseObject = {
                    'status': 'success',
                    'message': 'Successfully registered.',
                    'refresh_token': refresh_token.decode(),
                    'access_token': (User.encode_access_token(user.id)).decode()
                }
                return make_response(jsonify(responseObject)), 201
            except Exception as e:
                responseObject = {
                    'status': 'fail',
                    'message': 'Some error occurred. Please try again.'
                }
                return make_response(jsonify(responseObject)), 401
        else:
            responseObject = {
                'status': 'fail',
                'message': 'Already registered. Please Log in.',
            }
            return make_response(jsonify(responseObject)), 202

class LoginAPI(MethodView):
    """
    User Login Resource
    """
    def post(self):
        # get the post data
        post_data = request.get_json()
        try:
            # fetch the user data
            user = User.query.filter_by(
                email=post_data.get('email')
            ).first()
            if user and bcrypt.check_password_hash(
                user.password, post_data.get('password')
            ):
                refresh_token = user.encode_refresh_token(user.id)
                if refresh_token:
                    responseObject = {
                        'status': 'success',
                        'message': 'Successfully logged in.',
                        'refresh_token': refresh_token.decode(),
                        'access_token':  (User.encode_access_token(user.id)).decode()
                    }
                    return make_response(jsonify(responseObject)), 200
            else:
                responseObject = {
                    'status': 'fail',
                    'message': 'User does not exist.'
                }
                return make_response(jsonify(responseObject)), 404
        except Exception as e:
            print(e)
            responseObject = {
                'status': 'fail',
                'message': 'Try again'
            }
            return make_response(jsonify(responseObject)), 500

class UserAPI(MethodView):
    """
    User Resource
    """
    def get(self):
        # get the auth token
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = User.decode_token(auth_token, 'access')
            if not isinstance(resp, str):
                    user = User.query.filter_by(id=resp['sub']).first()
                    responseObject = {
                        'status': 'success',
                        'data': {
                            'user_id': user.id,
                            'email': user.email,
                            'admin': user.admin,
                            'registered_on': user.registered_on
                        }
                    }
                    return make_response(jsonify(responseObject)), 200

            responseObject = {
                'status': 'fail',
                'message': resp
            }
            return make_response(jsonify(responseObject)), 401
        else:
            responseObject = {
                'status': 'fail',
                'message': 'Provide a valid access token.'
            }
            return make_response(jsonify(responseObject)), 401

class LogoutAPI(MethodView):
    """
    Logout Resource
    """
    def post(self):
        # get auth token
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = User.decode_token(auth_token, 'refresh')
            if not isinstance(resp, str):
                # mark the token as blacklisted
                blacklist_token = BlacklistToken(token=auth_token)
                try:
                    # insert the token
                    db.session.add(blacklist_token)
                    db.session.commit()
                    responseObject = {
                        'status': 'success',
                        'message': 'Successfully logged out.'
                    }
                    return make_response(jsonify(responseObject)), 200
                except Exception as e:
                    responseObject = {
                        'status': 'fail',
                        'message': e
                    }
                    return make_response(jsonify(responseObject)), 200
            else:
                responseObject = {
                    'status': 'fail',
                    'message': resp
                }
                return make_response(jsonify(responseObject)), 401
        else:
            responseObject = {
                'status': 'fail',
                'message': 'Provide a valid auth token.'
            }
            return make_response(jsonify(responseObject)), 403

class RefreshAPI (MethodView):
    """
    Access Token Refresh Resource
    """
    def post(self):
        # get the refresh token
        auth_header = request.headers.get('Authorization')
        if auth_header:
             refresh_token = auth_header.split(" ")[1]
        else:
             refresh_token = ''
        if refresh_token:
            resp = User.decode_token(refresh_token, 'refresh')
            if not isinstance(resp,str):
                 responseObject ={
                       'status' : 'success',
                       'message' : 'successfully created new access token',
                       'access_token' : (User.encode_access_token(resp['sub'])).decode()
                 }
                 return make_response(jsonify(responseObject)), 200
            else:
                 responseObject = {
                       'status': 'fail',
                       'message': 'Provide a valid auth token.'
                 }
                 return make_response(jsonify(responseObject)), 401
        else:
           responseObject = {
              'status': 'fail',
              'message': 'Provide a valid refresh token.'
           }
           return make_response(jsonify(responseObject)), 403


# define the API resources
registration_view = RegisterAPI.as_view('register_api')
login_view = LoginAPI.as_view('login_api')
user_view = UserAPI.as_view('user_api')
logout_view = LogoutAPI.as_view('logout_api')
refresh_view = RefreshAPI.as_view('refresh_api')

# add Rules for API Endpoints
auth_blueprint.add_url_rule(
    '/auth/register',
    view_func=registration_view,
    methods=['POST']
)
auth_blueprint.add_url_rule(
    '/auth/login',
    view_func=login_view,
    methods=['POST']
)
auth_blueprint.add_url_rule(
    '/auth/status',
    view_func=user_view,
    methods=['GET']
)
auth_blueprint.add_url_rule(
    '/auth/logout',
    view_func=logout_view,
    methods=['POST']
)
auth_blueprint.add_url_rule(
    '/auth/refresh',
    view_func=refresh_view,
    methods=['POST']
)

