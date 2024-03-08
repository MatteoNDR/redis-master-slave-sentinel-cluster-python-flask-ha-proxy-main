from flask import Flask, jsonify, session, request, redirect, url_for
from redis import Redis
from redis.sentinel import Sentinel
from datetime import timedelta
import os

app = Flask(__name__)

# Secret key per encrypt di ogni sessione
app.secret_key = os.getenv('SECRET_KEY', default="123")


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


@app.route('/get', methods=['GET'])
def get_email_and_items():
    try:
        # Scoperta Master
        redis_connection = get_redis_connection()

        # Recupera l'email dell'utente dalla sessione
        email = session.get('email', 'Nessuna email impostata')

        # Recupera l'ID di sessione
        session_id = session.get('sid')

        # Se non c'è un ID di sessione, restituisci un messaggio vuoto
        if session_id is None:
            return f"Email: {email}<br>Items: Nessun elemento associato alla sessione"

        # Recupera gli elementi associati a questo ID di sessione e email dall'hash Redis
        redis_key = f'items:{session_id}:{email}'
        items = redis_connection.hgetall(redis_key)
        items = {key.decode(): int(value.decode()) for key, value in items.items()}

        # Aggiorna la sessione con gli elementi recuperati
        session['items'] = items

        session.permanent = True

        # Codice di debug per verificare se i dati vengono recuperati correttamente dal database Redis
        print("Dati recuperati dalla chiave Redis:", items)

        return f"Email: {email}<br>Items: {items}"
    except Exception as ex:
        print('Errore:', ex)
        return jsonify({'errore': str(ex)}), 500


@app.route('/add', methods=['GET', 'POST'])
def set_email_and_items():
    try:
        redis_connection = get_redis_connection()

        if request.method == 'POST':
            session_id = session.get('sid')

            if session_id is None:
                session_id = os.urandom(24).hex()
                session['sid'] = session_id

            session_items = session.get('items', {})
            
            # Recupera l'email dell'utente dalla sessione
            user_email = session.get('email', '')

            for i in range(1, 6):
                item_name = f'item_{i}'
                quantity = int(request.form.get(f'quantity_{i}', 0))
                session_items[item_name] = quantity

            session['items'] = session_items

            # Aggiorna la chiave Redis utilizzando lo stesso formato usato per memorizzare gli items
            redis_key = f'items:{session_id}:{user_email}'

            # Elimina la chiave esistente prima di memorizzare i nuovi dati solo se ci sono items nella sessione
            if session_items:
                redis_connection.delete(redis_key)

                for item_name, quantity in session_items.items():
                    redis_connection.hset(redis_key, item_name, quantity)

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


@app.route('/delete')
def delete_email():
    try:
        redis_connection = get_redis_connection()

        # Recupera l'ID di sessione
        session_id = session.pop('sid', None)

        # Recupera l'email dell'utente dalla sessione
        user_email = session.pop('email', '')

        # Cancella l'intera sessione nel browser
        session.clear()

        # Genera la chiave Redis utilizzando lo stesso formato come nella funzione /add
        redis_key = f'items:{session_id}:{user_email}'

        # Verifica se esistono items associati alla sessione e procedi con la cancellazione
        if session_id and redis_connection.exists(redis_key):
            redis_connection.delete(redis_key)
            return '<h1>Items associati alla sessione cancellati!</h1>'
        else:
            return 'Nessun item associato alla sessione trovato da cancellare.'

    except Exception as ex:
        print('Error:', ex)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)