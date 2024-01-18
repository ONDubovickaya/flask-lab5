from flask import Flask, request, make_response, jsonify
import uuid
import json

import os
from peewee import *
from peewee import Model, PostgresqlDatabase

####### БД #######
pg_db = PostgresqlDatabase(
    os.getenv('DATA_BASE_NAME'),
    user=os.getenv('DATA_BASE_USER'),
    password=os.getenv('DATA_BASE_PASS'),
    host=os.getenv('DATA_BASE_HOST'),
    port=int(os.getenv('DATA_BASE_PORT'))
)

class BaseModel(Model):
    class Meta:
        database = pg_db

class PaymentModel(BaseModel):
    id = IdentityField()
    payment_uid = UUIDField(null=False)
    status = CharField(max_length=20, constraints=[Check("status IN ('PAID', 'CANCELED')")])
    price = IntegerField(null=False)

    def to_dict(self):
        return {
            "paymentUid": str(self.payment_uid),
            "status": str(self.status),
            "price": self.price,
        }

    class Meta:
        db_table = "payment"

####### создание таблицы в БД #######
def create_tables():
    PaymentModel.drop_table()
    PaymentModel.create_table()

####### описание сервиса #######
app = Flask(__name__)

#пустой маршрут
@app.route("/")
def service():
    return "PAYMENT"

#маршрут get
@app.route('/api/v1/payment/<string:paymentUid>', methods=['GET'])
def get_payment(paymentUid):
    try:
        payment = PaymentModel.select().where(PaymentModel.payment_uid == paymentUid).get().to_dict()

        response = make_response(jsonify(payment))
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except:
        response = make_response(jsonify({'errors': ['No Uid']}))
        response.status_code = 404
        response.headers['Content-Type'] = 'application/json'
        
        return response

#маршрут post
def validate_body(body):
    try:
        body = json.loads(body)
    except:
        return None, ['Error']

    errors = []
    if 'price' not in body.keys() or type(body['price']) is not int:
        return None, ['wrong structure']

    return body, errors

@app.route('/api/v1/payment', methods=['POST'])
def post_payment():
    body, errors = validate_body(request.get_data())

    if len(errors) > 0:
        
        response = make_response(jsonify(errors))
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        
        return response

    payment = PaymentModel.create(payment_uid=uuid.uuid4(), price=body['price'], status='PAID')

    response = make_response(jsonify(payment.to_dict()))
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
    
    return response

#маршрут delete
@app.route('/api/v1/payment/<string:paymentUid>', methods=['DELETE'])
def delete_payment(paymentUid):
    try:
        payment = PaymentModel.select().where(PaymentModel.payment_uid == paymentUid).get()
        
        payment.status = 'CANCELED'
        payment.save()

        response = make_response(jsonify(payment.to_dict()))
        #response = make_response(jsonify({'message': 'Payment canceled'}))
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except:
        response = make_response(jsonify({'errors': ['No Uid']}))
        response.status_code = 404
        response.headers['Content-Type'] = 'application/json'

        return response

#маршрут health check
@app.route('/manage/health', methods=['GET'])
def health_check():
    response = make_response(jsonify({'status': 'OK'}))
    response.status_code = 200
    
    return response

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=8050)
