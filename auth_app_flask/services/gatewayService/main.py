from flask import Flask, request, make_response, jsonify, Response
import requests
import datetime
import json
import os

from authlib.integrations.flask_client import OAuth
import jwt
from jwt import PyJWKClient

#from auth0.v3.authentication.token_verifier import TokenVerifier, AsymmetricSignatureVerifier

cars_url = f"http://{os.environ['CARS_SERVICE_HOST']}:{os.environ['CARS_SERVICE_PORT']}"
rental_url = f"http://{os.environ['RENTAL_SERVICE_HOST']}:{os.environ['RENTAL_SERVICE_PORT']}"
payment_url = f"http://{os.environ['PAYMENT_SERVICE_HOST']}:{os.environ['PAYMENT_SERVICE_PORT']}"

def get_data_from_service(service_url, headers={}, timeout=5):
    try:
        response = requests.get(service_url, timeout=timeout, headers=headers)
        return response
    except:
        return None

def post_data_to_service(service_url, headers={}, timeout=5, data={}):
    try:
        response = requests.post(service_url, timeout=timeout, headers=headers, json=data)
        return response
    except:
        return None

def delete_data_from_service(service_url, headers={}, timeout=5):
    try:
        response = requests.delete(service_url, timeout=timeout, headers=headers)
        return response
    except:
        return None

####### описание маршрутов #######
app = Flask(__name__)

# подключение OAuth
app.config['JSON_AS_ASCII'] = False
#app.secret_key = os.environ['APP_SECRET_KEY']
"""
oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=os.environ['AUTH0_CLIENT_ID'],
    client_secret=os.environ['AUTH0_CLIENT_SECRET'],
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{os.environ['AUTH0_DOMAIN']}/.well-known/openid-configuration",
)


def validation(id_token):
    domain = os.environ['AUTH0_DOMAIN']
    client_id = os.environ['AUTH0_CLIENT_ID']

    jwks_url = 'https://{}/.well-known/jwks.json'.format(domain)
    issuer = 'https://{}/'.format(domain)

    try:
        sv = AsymmetricSignatureVerifier(jwks_url)
        tv = TokenVerifier(signature_verifier=sv, issuer=issuer, audience=client_id)
        tv.verify(id_token)
        return True
    except:
        return False 
"""

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id='2tzOe8ODXk00x0wmzA8RoWhSR552QD8f',
    client_secret='YZIJUrFjzqlozGrRLT7eGx3gjrBjGVW1sJ8jcCcwE1wswL4d8rN42QpfwpfPQC6o',
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://dev-268y6str0e3mrg1n.us.auth0.com/.well-known/openid-configuration",
)

jwks = PyJWKClient("https://dev-268y6str0e3mrg1n.us.auth0.com/.well-known/jwks.json")

def check_jwt(bearer):
    try:
        jwt_token = bearer.split()[1]
        signing_key = jwks.get_signing_key_from_jwt(jwt_token)
        data = jwt.decode(
            jwt_token,
            signing_key.key,
            algorithms=["RS256"],
            audience="http://127.0.0.1:8080",
            options={"verify_exp": False}
        )
        return data["name"]
    except:
        return False

## пустой маршрут
@app.route("/")
def service():
    return "GATEWAY"

## маршрут get cars
@app.route('/api/v1/cars', methods=['GET'])
def get_cars():
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
    
    #получаем данные из сервиса Cars
    url = f"{cars_url}/api/v1/cars?{request.full_path.split('?')[-1]}"
    resp = get_data_from_service(url, timeout=5)
    
    if resp:
        response = make_response(resp.text)
        response.status_code = resp.status_code
        response.headers['Content-Type'] = 'application/json'
        
        return response
    else:
        response = make_response(jsonify({'errors': ['Cars Service not working']}))
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        
        return response

## маршрут get rental
def car_simplify(car: dict) -> dict:
    return{
        "carUid": car['carUid'],
        "brand": car['brand'],
        "model": car['model'],
        "registrationNumber": car['registrationNumber']
    }

@app.route('/api/v1/rental/<string:rentalUid>', methods=['GET'])
def get_rental(rentalUid):
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
    """
    # проверка имени пользователя
    if 'X-User-Name' not in request.headers.keys():
        response = make_response(jsonify({'errors': ['user not found!!']}))
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    user = request.headers['X-User-Name']
    """
    # получаем данные из сервиса Rental
    url = f"{rental_url}/api/v1/rental/{rentalUid}"
    head = {'X-User-Name': client}

    resp = get_data_from_service(url, headers=head, timeout=5)

    if resp is None:
        response = make_response(jsonify({'errors': ['Rental Service not working']}))
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    rental = resp.json()

    # получаем данные из сервиса Cars
    url = f"{cars_url}/api/v1/cars/{rental['carUid']}"
    resp = get_data_from_service(url, timeout=5)

    if resp is None:
        response = make_response(jsonify({'errors': ['Cars Service not working']}))
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        
        return response

    del rental['carUid']
    rental['car'] = car_simplify(resp.json())

    # получаем данные из сервиса Payment
    url = f"{payment_url}/api/v1/payment/{rental['paymentUid']}"
    resp = get_data_from_service(url, timeout=5)

    if resp is None:
        response = make_response(jsonify({'errors': ['Payment Service not working']}))
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    rental['payment'] = resp.json()
    del rental['paymentUid']

    response = make_response(jsonify(rental))
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
        
    return response

## маршрут get rentals
@app.route('/api/v1/rental', methods=['GET'])
def get_rentals():
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
    
    """
    # проверка имени пользователя 
    if 'X-User-Name' not in request.headers.keys():
        response = make_response(jsonify({'errors': ['user not found!!']}))
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    user = request.headers['X-User-Name']
    """
    head = {'X-User-Name': client}

    # получаем данные из сервиса Rental
    url = f"{rental_url}/api/v1/rental"
    resp = get_data_from_service(url, headers=head, timeout=5)

    if resp is None:
        response = make_response(jsonify({'errors': ['Rental Service not working']}))
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    rentals = resp.json()

    for rental in rentals:
        # получаем данные из сервиса Cars
        url = f"{cars_url}/api/v1/cars/{rental['carUid']}"
        resp = get_data_from_service(url, timeout=5)

        if resp is None:
            response = make_response(jsonify({'errors': ['Cars Service not working']}))
            response.status_code = 500
            response.headers['Content-Type'] = 'application/json'
            
            return response

        del rental['carUid']
        rental['car'] = car_simplify(resp.json())

        # получаем данные из сервиса Payment
        url = f"{payment_url}/api/v1/payment/{rental['paymentUid']}"
        resp = get_data_from_service(url, timeout=5)

        if resp is None:
            response = make_response(jsonify({'errors': ['Payment Service not working']}))
            response.status_code = 500
            response.headers['Content-Type'] = 'application/json'
            
            return response
        
        rental['payment'] = resp.json()
        del rental['paymentUid']

    response = make_response(jsonify(rentals))
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
        
    return response

## маршрут post rentals
def validate_body(body):
    try:
        body = json.loads(body)
    except:
        return None, ['wrong']

    errors = []
    if ('carUid' not in body or type(body['carUid']) is not str) or ('dateFrom' not in body or type(body['dateFrom']) is not str) or ('dateTo' not in body or type(body['dateTo']) is not str):
        return None, ['wrong structure']

    return body, errors


def clear_headers(headers: dict) -> dict:
    technical_headers = ['Remote-Addr', 'User-Agent', 'Accept', 'Postman-Token', 'Host', 'Accept-Encoding', 'Connection']
    keys = list(headers.keys())
    for key in keys:
        if key in technical_headers:
            del headers[key]

    return headers

@app.route('/api/v1/rental', methods=['POST'])
def post_rentals():
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
    """
    # проверка имени пользователя 
    if 'X-User-Name' not in request.headers.keys():
        response = make_response(jsonify({'errors': ['user not found!!']}))
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    user = request.headers['X-User-Name']
    """
    head = {'X-User-Name': client}

    body, errors = validate_body(request.get_data())

    if len(errors) > 0:
        response = make_response(jsonify(errors))
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    # создание записи с помощью Cars сервиса
    url = f"{cars_url}/api/v1/cars/{body['carUid']}/order"
    resp = post_data_to_service(url, timeout=5)

    if resp is None:
        response = make_response(jsonify({'errors': ['Payment Service not working']}))
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    if resp.status_code == 404 or resp.status_code == 403:
        response = make_response(resp.text)
        response.status_code = resp.status_code
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    car = resp.json()
    price = (datetime.datetime.strptime(body['dateTo'], "%Y-%m-%d").date() - datetime.datetime.strptime(body['dateFrom'], "%Y-%m-%d").date()).days * car['price']

    # создание записи с помощью Payment сервиса
    url = f"{payment_url}/api/v1/payment"
    resp = post_data_to_service(url, timeout=5, data={'price': price})

    if resp is None:
        url = f"{cars_url}/api/v1/cars/{body['carUid']}/order"
        resp = delete_data_from_service(url, timeout=5)

        response = make_response(jsonify({'errors': ['Payment Service not working']}))
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    payment = resp.json()
    body['paymentUid'] = payment['paymentUid']

    # создание записи с помощью Rental сервиса
    url = f"{rental_url}/api/v1/rental"
    resp = post_data_to_service(url, headers=head, timeout=5, data=body)

    if resp is None:
        url = f"{cars_url}/api/v1/cars/{body['carUid']}/order"
        resp = delete_data_from_service(url, timeout=5)

        url = f"{payment_url}/api/v1/payment/{body['paymentUid']}"
        resp = delete_data_from_service(url, timeout=5)

        response = make_response(jsonify({'errors': ['Rental Service not working']}))
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    if resp.status_code != 200:
        response = make_response(resp.text)
        response.status_code = resp.status_code
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    rental = resp.json()

    rental['payment'] = payment
    del rental['paymentUid']

    response = make_response(jsonify(rental))
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
        
    return response 

## маршрут post finish rental
@app.route('/api/v1/rental/<string:rentalUid>/finish', methods=['POST'])
def post_rental_finish(rentalUid):
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
    
    # создание записи с помощью Rental сервиса
    url = f"{rental_url}/api/v1/rental/{rentalUid}/finish"
    resp = post_data_to_service(url, timeout=5)

    if resp is None:
            response = make_response(jsonify({'errors': ['Rental Service not working']}))
            response.status_code = 500
            response.headers['Content-Type'] = 'application/json'
            
            return response
    elif resp.status_code != 200:
            response = make_response(resp.text)
            response.status_code = resp.status_code
            response.headers['Content-Type'] = 'application/json'
            
            return response

    rental = resp.json()

    # удаление записи с помощью Cars сервиса
    url = f"{cars_url}/api/v1/cars/{rental['carUid']}/order"
    resp = delete_data_from_service(url, timeout=5)

    if resp is None:
            response = make_response(jsonify({'errors': ['Cars Service not working']}))
            response.status_code = 500
            response.headers['Content-Type'] = 'application/json'

    response = make_response(jsonify({'status': 'OK'}))
    response.status_code = 204
    
    return response

## маршрут delete rental
@app.route('/api/v1/rental/<string:rentalUid>', methods=['DELETE'])
def delete_rental(rentalUid):
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
    
    # удаление записи с помощью Rental сервиса
    url = f"{rental_url}/api/v1/rental/{rentalUid}"
    resp = delete_data_from_service(url, timeout=5)

    if resp is None:
            response = make_response(jsonify({'errors': ['Rental Service not working']}))
            response.status_code = 500
            response.headers['Content-Type'] = 'application/json'
            
            return response
    elif resp.status_code != 200:
            response = make_response(resp.text)
            response.status_code = resp.status_code
            response.headers['Content-Type'] = 'application/json'
            
            return response

    rental = resp.json()

    # удаление записи с помощью Cars сервиса
    url = f"{cars_url}/api/v1/cars/{rental['carUid']}/order"
    resp = delete_data_from_service(url, timeout=5)

    if resp is None:
            response = make_response(jsonify({'errors': ['Cars Service not working']}))
            response.status_code = 500
            response.headers['Content-Type'] = 'application/json'
            
            return response

    # удаление записи с помощью Payment сервиса
    url = f"{payment_url}/api/v1/payment/{rental['paymentUid']}"
    resp = delete_data_from_service(url, timeout=5)

    if resp is None:
            response = make_response(jsonify({'errors': ['Payment Service not working']}))
            response.status_code = 500
            response.headers['Content-Type'] = 'application/json'
            
            return response
    
    response = make_response(jsonify({'status': 'OK'}))
    response.status_code = 204
    
    return response

## маршрут health check
@app.route('/manage/health', methods=['GET'])
def health_check():
    response = make_response(jsonify({'status': 'OK'}))
    response.status_code = 200
    
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
