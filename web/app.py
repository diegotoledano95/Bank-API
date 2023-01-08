from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.BankDB
users = db["Users"]

def UserExist(username):
    if users.count_documents({"Username":username}) == 0:
        return False
    else:
        return True

class Register(Resource):
    def post(self):
        #Step 1 is to get posted data by the user
        postedData = request.get_json()

        #Get the data
        username = postedData["username"]
        password = postedData["password"] 

        if UserExist(username):
            retJson = {
                'status':301,
                'msg': 'Invalid Username'
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        #Store username and pw into the database
        users.insert_one({
            "Username": username,
            "Password": hashed_pw,
            "Own":0,
            "Debt":0
        })

        retJson = {
            "status": 200,
            "msg": "You successfully signed up for the API"
        }
        return jsonify(retJson)

def verifyPw(username, password):
    if not UserExist(username):
        return False

    hashed_pw = users.find({
        "Username":username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def userCash(username):
    cash = users.find({"Username":username})[0]["Own"]
    return cash

def userDebt(username):
    debt = users.find({"Username":username})[0]["Debt"]
    return debt

def generateReturnDictionary(status, msg):
    retJson = {
        "status": status,
        "msg": msg
    }
    return retJson

def verifyCredentials(username, password):
    if not UserExist(username):
        return generateReturnDictionary(301, "Invalid username"), True
    
    correct_pw = verifyPw(username, password)
    if not correct_pw:
        return generateReturnDictionary(302, "Invalid password"), True

    return None, False

def updateBalance(username, amount):
    users.update_one({
        "Username":username
        },{
            "$set":{
                "Own":amount
            }
    })

def updateDebt(username, amount):
    users.update_one({
        "Username":username
        },{
            "$set":{
                "Debt":amount
            }
    })

class Add(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return jsonify(retJson)

        if money <= 0:
            return generateReturnDictionary(304, "The money amount entered must be greater than 0")

        cash = userCash(username)
        bank_cash = userCash("BANK")
        money -= 1
        updateBalance("BANK", bank_cash+1)
        updateBalance(username, cash+money)

        return jsonify(generateReturnDictionary(200, "Amount added succesfully, service tariff of $1"))

class Transfer(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        to = postedData["to"]
        money = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return jsonify(retJson)
        
        cash = userCash(username)

        if cash <= 0:
            return jsonify(generateReturnDictionary(304, "Your balance is equal to 0"))

        if not UserExist(username):
            return jsonify(generateReturnDictionary(301,"user does not exist"))
        
        cash_from = userCash(username)
        cash_to = userCash(to)
        bank_cash = userCash("BANK")
        money -= 1
        updateBalance("BANK", bank_cash+1)
        updateBalance(to, cash_to+money)
        updateBalance(username, cash_from-money)

        return jsonify(generateReturnDictionary(200, "Amount transferred successfully"))

class Balance(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return jsonify(retJson)

        retJson = users.find({
            "Username":username
            }, {
                "Password":0,
                "_id":0
            })[0]
        
        return jsonify(retJson)

class TakeLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return jsonify(retJson)

        cash = userCash(username)
        debt = userDebt(username)

        updateBalance(username, cash+money)
        updateDebt(username, debt+money)  

        return jsonify(generateReturnDictionary(200, f"You have taken a loan for the amount of ${money}"))     

class PayLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return jsonify(retJson)

        cash = userCash(username)

        if cash < money:
            return jsonify(generateReturnDictionary(303, "Not enough cash in account"))

        debt = userDebt(username)

        updateBalance(username, cash-money)
        updateDebt(username, debt-money)

        return jsonify(generateReturnDictionary(200, f"You successfully payed ${money} to your debt"))

api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(PayLoan, '/payloan')
api.add_resource(TakeLoan, '/takeloan')

if __name__=="__main__":
    app.run(host='0.0.0.0', port=3000, debug=True)
