from flask import Flask, jsonify, session, request, redirect, url_for
from redis import Redis
from redis.sentinel import Sentinel
from datetime import timedelta
import os

app = Flask(__name__)

# Secret key per encrypt di ogni sessione
app.secret_key = os.getenv('SECRET_KEY', default='ADVRFGMKRRKKGK')


# Tramite la classe Sentinel effettuo la scoperta del mio container con ruolo master, assegno il nome dei tre container sentinel nel mio cluster
def get_redis_connection():
    sentinel = Sentinel([('redis-sentinel', 26379), ('redis-sentinel-2', 26379), ('redis-sentinel-3', 26379)])
    redis_master = sentinel.discover_master("mymaster")
    host, port = redis_master
    return Redis(host=host, port=port)

# Func per login utente usata route /login , controllo credenziali valide o meno
def login_user(email, password):
    try:        
        master_object = get_redis_connection()
        master_object.get("data")
        stored_password = master_object.get(f'user:{email}:password')
        if stored_password and stored_password.decode('utf-8') == password:
            return True
        return False
    except Exception as ex:
        print('Error:', ex)
        return False

# Configurazione parametri per gestire la session e set cookie 

# Indica a Flask di utilizzare Redis come backend per la gestione delle sessioni
app.config['SESSION_TYPE'] = 'redis'
# Indica se la sessione dell'utente deve essere permanente o meno. Se è impostato su True, la sessione dell'utente sarà permanente e non scadrà mai.
app.config['SESSION_PERMANENT'] = False
# Indica se i cookie delle sessioni dovrebbero essere firmati o meno. La firma dei cookie assicura che i dati delle sessioni non possano essere modificati da parte dell'utente. 
# Impostando questa opzione su True, i cookie delle sessioni verranno firmati.
app.config['SESSION_USE_SIGNER'] = True
# Questa impostazione definisce la durata della sessione permanente se SESSION_PERMANENT è impostato su True. In questo caso è di 10 minuti.
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)


# Route Get , restituisce email e items se presenti
@app.route('/get', methods=['GET'])
def get_email_and_items():
    try:
        # Scoperta Master
        redis_connection = get_redis_connection()

        # Recupera l'email dalla sessione
        email = session.get('email', 'Nessuna email impostata')
        
        # Recupera l'ID di sessione
        session_id = session.setdefault('sid', os.urandom(24).hex())

        # Recupera gli elementi associati a questo ID di sessione dal database Redis
        items = redis_connection.hgetall(f'items:{session_id}')
        items = {key.decode(): int(value.decode()) for key, value in items.items()}

        # Aggiorna la sessione con gli elementi recuperati
        session['items'] = items

        session.permanent = True

        return f"Email: {email}<br>Items: {items}"
    except Exception as ex:
        print('Errore:', ex)
        return jsonify({'errore': str(ex)}), 500

# Route Add , aggiungiamo lists di items
@app.route('/add', methods=['GET', 'POST'])
def set_email_and_items():
    try:
        # Scoperta Master
        redis_connection = get_redis_connection()

        if request.method == 'POST':
            # Recupera l'ID di sessione
            session_id = session.get('sid')

            # Se non è presente un ID di sessione lo andiamo a creare
            if session_id is None:
                session_id = os.urandom(24).hex()
                session['sid'] = session_id

            session['items'] = {}
            for i in range(1, 6):
                item_name = f'item_{i}'
                quantity = int(request.form.get(f'quantity_{i}', 0))
                session['items'][item_name] = quantity

                # Aggiungi l'elemento al database Redis associandolo all'ID di sessione
                redis_connection.hset(f'items:{session_id}', item_name, quantity)

            # Questo va usato quando lavoriamo con dati di tipologia mutable, come le list 
            session.modified = True
            return redirect(url_for('get_email_and_items'))

        return """
            <form method="post">
                """ + ''.join([f"""
                <label for="item{i}">Item {i}</label>
                <select id="item{i}" name="quantity_{i}">
                    <option value="0">0</option>
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="4">4</option>
                    <option value="5">5</option>
                    <!-- Aggiungi altre opzioni se necessario -->
                </select><br><br>
                """ for i in range(1, 6)]) + """
                <button type="submit">Invia</button>
            </form>
            """
    except Exception as ex:
        print('Error:', ex)

# Route login
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        # Scoperta Master
        master_object = get_redis_connection()
        master_object.get("data")

        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            if login_user(email, password):
                session['email'] = email  # Imposta l'email nella sessione
                return redirect(url_for('get_email_and_items'))
            else:
                return "Credenziali non valide. Riprova."
        return """
            <form method="post">
                <h1>Pagina Login</h1>
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required /><br><br>
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required /><br><br>
                <button type="submit">Login</button>
            </form>
            """
    except Exception as ex:
        print('Error:', ex)

# Route register
@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            redis_connection = get_redis_connection()
            if redis_connection.exists(f'user:{email}:password'):
                return "Email già registrata."
            else:
                redis_connection.set(f'user:{email}:password', password)
                session['email'] = email
                return redirect(url_for('login'))
        return """
            <form method="post">
                <h1>Pagina Registrazione</h1>
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required /><br><br>
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required /><br><br>
                <button type="submit">Register</button>
                <h5>Già registrato?<a href="/login">Login</a></h5>
            </form>
            """
    except Exception as ex:
        print('Error:', ex)

# Route delete 
@app.route('/delete')
def delete_email():
    try:
        master_object = get_redis_connection()
        master_object.get("data")

        # Recupera l'ID di sessione
        session_id = session.get('sid')

        # Elimina gli elementi associati a questo ID di sessione dal database Redis
        redis_connection = get_redis_connection()
        redis_connection.delete(f'items:{session_id}')

        return '<h1>Items associati alla sessione cancellati!</h1>'
    except Exception as ex:
        print('Error:', ex)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)