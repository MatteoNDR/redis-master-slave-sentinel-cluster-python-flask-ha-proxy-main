# Redis-Master-Slave-Sentinel-Cluster Failover con Docker, Python , Flask e HaProxy



# Descrizione Diagramma - Applicazione

**Haproxy**
- Contiene la configurazione del nostro container con immagine "haproxy", la pagina **stats** risponde su porta 8404 mentre il frontend delle due applicazioni Flask è bilanciato in modalità round robin su porta 80.
Viene effettuato un check tra il Redis Master ed i Redis Slave per capire chi tra questi ha il ruolo **Master** , il ruolo può cambiare nel tempo e venire passato in seguito a crash o restart del Master precedente.

**Flask app**
- Gli applicativi utilizzano Python con le libreria Flask e Redis.
Le route disponibili di Flask che rispondono a localhost sono:
  - /register -> Registrazione utente su db Redis, controllo se email già presente tramite redis_connection.exists
  - /login -> Login utente con check su credenziali valide o meno
  - /get -> Restituisce tramite html il nostro indirizzo email con cui siamo loggati, inoltre se abbiamo già aggiunto degli items tramite /add viene restituita la quantità selezionata
  - /add -> Permette di selezionare la quantità di 6 option value
  - /delete -> Cancella Item associati all'email ed alla sessione corrente

Per ogni route viene effettuato il controllo tramite

 **def get_redis_connection():
    sentinel = Sentinel([('redis-sentinel', 26379), ('redis-sentinel-2', 26379), ('redis-sentinel-3', 26379)])
    redis_master = sentinel.discover_master("mymaster")**

per scoprire se il precedente master sia ancora valido/raggiungibile o meno.

Tramite **Flask session**

**app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)**

andiamo ad associare il cookie di sessione alla nostra email loggata, in modo che se la connessione originale non risulta più disponibile al connettersi al nuovo Master la nostra sessione è nuovamente disponibile, al momento è impostato come default di timeout 10 minuti , il valore di default scade quando viene chiuso il browser.

**Cluster Redis**
- Cluster formato da 1 Redis Master in modalità Scrittura / Lettura, 2 Redis Slave in modalità Lettura al redis slave e 3 Redis Sentinel che si occupano di monitorare i Master ed i due Slave.
Se il Master non è più raggiungibile, i 3 Sentinel provvederanno ad effettuare un failover automatico andando ad eleggere uno tra i due slave come nuovo Master.
Questo processo viene chiamato come **Quorum** tra Sentinel, è importante averne configurati un numero dispari in modo che si possa raggiungere la decisione per maggioranza, come nel nostro caso dove è impostato a 2.

**Configurazione Sentinel**
Lanciamo come comando entrypoint lo script **sentinel-entrypoint.sh** con 3 variabili ENV configurate nel Dockerfile della stessa cartella

**Docker compose e Dockerfile**

- **Dockerfile** della nostra app Flask (nome immagine pythonredis).
- **Docker compose** tramite Docker compose up abbiamo creati i seguenti container:
  
  - 1 Redis Master
  - 2 Redis Slave
  - 3 Redis Sentinel
  - 1 Redis Insight 
  - 2 Flask App
  - 1 HaProxy

# Clone Repo e Docker Build

Procedura per clonare repo e renderlo operativo

1) ..>  git clone git@gitlab.passepartout.local:matteo.andruccioli/redis-master-slave-sentinel-cluster-python-flask-ha-proxy.git
2) ..> cd redis-master-slave-sentinel-cluster-python-flask-ha-proxy
3) ..> code .
4) ..> docker build -t pythonredis .

```
PS C:\Users\matteo.andruccioli\Desktop\redis-master-slave-sentinel-cluster-python-flask-ha-proxy> docker build -t pythonredis .
[+] Building 6.6s (11/11) FINISHED                                                                                                                                                  docker:default
 => [internal] load build definition from Dockerfile                                                                                                                                          0.1s
 => => transferring dockerfile: 440B                                                                                                                                                          0.0s
 => [internal] load metadata for docker.io/library/python:3.10-alpine                                                                                                                         1.3s
 => [auth] library/python:pull token for registry-1.docker.io                                                                                                                                 0.0s
 => [internal] load .dockerignore                                                                                                                                                             0.1s
 => => transferring context: 2B                                                                                                                                                               0.0s
 => [builder 1/5] FROM docker.io/library/python:3.10-alpine@sha256:a84794f8f487847a49a6f92bc426f99b865d4c991344c682ce2c151a64c3d79b                                                           0.0s
 => [internal] load build context                                                                                                                                                             0.1s
 => => transferring context: 35.74kB                                                                                                                                                          0.0s
 => CACHED [builder 2/5] WORKDIR /flask-app                                                                                                                                                   0.0s
 => CACHED [builder 3/5] COPY requirements.txt /flask-app                                                                                                                                     0.0s
 => [builder 4/5] COPY /flask-app /flask-app                                                                                                                                                  0.1s
 => [builder 5/5] RUN --mount=type=cache,target=/root/.cache/pip     pip3 install -r requirements.txt                                                                                         4.6s 
 => exporting to image                                                                                                                                                                        0.2s 
 => => exporting layers                                                                                                                                                                       0.2s 
 => => writing image sha256:27412f0e3dfe1d9c0a0f7156a3043bd5f8062649cb50638c7146b6af27c3b63a                                                                                                  0.0s 
 => => naming to docker.io/library/pythonredis   
```

5) ..> docker compose up -d:

Prove effettuabili per ogni container:

HaProxy -> http://localhost:8404/stats

FlaskApp -> http://localhost/register , http://localhost/login , http://localhost/add , http://localhost/delete 

Redis-Insight-> http://localhost:5540

6) Per terminare prova lanciare ..> docker compose down 

