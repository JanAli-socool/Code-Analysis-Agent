def getUserData(userId):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s" % userId)
    return cursor.fetchone()

def connect_db():
    import mysql.connector
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="password123",
        database="legacy_db"
    )

class UserManager:
    def __init__(self):
        self.users = []
        self.cache = {}
    
    def addUser(self, name, email, password):
        user = {'name': name, 'email': email, 'password': password}
        self.users.append(user)
        return user
    
    def getUser(self, id):
        if id in self.cache:
            return self.cache[id]
        for u in self.users:
            if u.get('id') == id:
                self.cache[id] = u
                return u
        return None
    
    def updateUser(self, id, data):
        user = self.getUser(id)
        if user:
            user.update(data)
        return user
    
    def deleteUser(self, id):
        user = self.getUser(id)
        if user:
            self.users.remove(user)
            if id in self.cache:
                del self.cache[id]
        return True

def processPayment(amount, currency='USD'):
    import requests
    response = requests.post('https://api.payment.com/charge', 
        data={'amount': amount, 'currency': currency})
    return response.json()