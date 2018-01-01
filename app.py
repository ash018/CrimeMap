import feedparser
from flask import Flask,session, render_template, flash, request,Markup,redirect,url_for,escape,jsonify
import pymysql
from hashlib import md5
import json
import urllib
from dbhelper import DBHelper
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

db = pymysql.connect("localhost", "root", "", "rssfeed")
dbCrimeMap = pymysql.connect("localhost","root","","crimemap")

DB = DBHelper()

app= Flask(__name__)
#api = Api(app)
app.secret_key = 'my unobvious secret key'
BBC_FEED = "http://feeds.bbci.co.uk/news/rss.xml"
CNN_FEED = "http://rss.cnn.com/rss/edition.rss"
FOX_FEED = "http://feeds.foxnews.com/foxnews/latest"
IOL_FEED = "http://www.iol.co.za/cmlink/1.640"

WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather?q={}&units=metric&APPID=cb932829eacb6a0e9ee4f38bfbf112ed" 
CURRENCY_URL = "https://openexchangerates.org//api/latest.json?app_id=b23c94daab584f4580e4e2bf75cbcf7e"

DEFAULTS = {'publication': 'bbc',
            'city': 'London,UK',
            'currency_from': 'GBP',
            'currency_to': 'USD'
            }

cur=db.cursor()
curMap = dbCrimeMap.cursor()

@app.route('/')
def index():
    if 'username' in session:
        username_session = escape(session['username']).capitalize()
        return render_template('index.html', session_user_name=username_session)
    
    if request.method == 'POST':
        print('Hello')

    return redirect(url_for('login'))

@app.route('/crimemap')
def crimeMap():

    try:
        data = DB.get_all_inputs()
    except Exception as e:
        print(e)
        data =None

    return render_template('crimeMap.html',data=data)

@app.route("/addCrimeInfo", methods=["POST"])
def addCrimeInfo():
    try:
        data=request.form.get("userinput")
        DB.add_input(data)
    except Exception as e:
        print(e)
    
    return crimeMap()

@app.route("/clearCrimeInfo")
def clearCrimeInfo():
    try:
        DB.clear_all()
    except Exception as e:
        print(e)
    
    return crimeMap()



@app.route('/_get_data/', methods=['GET','POST'])
def _get_data():
    data = 0
    if request.method == 'POST':
        a = request.form['userName']
    # my_dict=json.loads(request.POST['argv'])
    # dir=my_dict['dir']
        print(a)
        cur.execute("SELECT COUNT(1) FROM users WHERE name = %s;", a) # CHECKS IF USERNAME EXSIST
        if cur.fetchone()[0]:
            data = 1
        else:
            data = 0
    
    myList = ['Element1', 'Element2', 'Element3']
    
    return jsonify({'data': data})


@app.route('/get_weather', methods=['GET', 'POST'])
def get_weather():
    error = None
    weather = None
    if request.method=='POST':
       cityName  = request.form['cityName']
       query = urllib.parse.quote(cityName)
       url = WEATHER_URL.format(query)
       print(url)
       
       try:
          data = urlopen(url).read()
          parsed = json.loads(data)
       
          if parsed.get('weather'):
                  weather = {'description': parsed['weather'][0]['description'],
                          'temperature': parsed['main']['temp'],
                          'city': parsed['name'],
                          'country': parsed['sys']['country']
                          }
       except urllib.error.HTTPError as err:
          if err.code == 404:
              weather={
                   'description': 'Not Found, Please Check City Name',
                   'temperature': 'Not Found',
                   'city': 'Not Found',
                   'country': 'Not Found'
            }

    return render_template('weather.html',weather=weather)

@app.route('/get_currency', methods=['GET', 'POST'])
def get_currency():
    error = None
    weather = None
    currency_from = request.args.get("currency_from")
    if not currency_from:
        currency_from = DEFAULTS['currency_from']
    currency_to = request.args.get("currency_to")
    if not currency_to:
        currency_to = DEFAULTS['currency_to']
    rate, currencies = get_rate(currency_from, currency_to)
    return render_template("currency.html", weather=weather,
                           currency_from=currency_from, currency_to=currency_to, rate=rate,
                           currencies=sorted(currencies))

@app.route('/signupform')
def signupform():
    return render_template('signup.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method=='POST':
       username_form  = request.form['username']
       password_form  = request.form['password'] 
       
       cur.execute("""INSERT INTO users(name,pass) VALUES(%s,%s);""",([username_form],[password_form]))
       flash('You were successfully Signed Up')
       return redirect(url_for('index'))

    return render_template('signup.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username_form  = request.form['username']
        password_form  = request.form['password']
        
        cur.execute("SELECT COUNT(1) FROM users WHERE name = %s;", [username_form]) # CHECKS IF USERNAME EXSIST
        if cur.fetchone()[0]:
            print(username_form)
            print(password_form)
            cur.execute("SELECT pass FROM users WHERE name = %s;", [username_form]) # FETCH THE HASHED PASSWORD
            for row in cur.fetchall():
                #if md5(password_form.encode('utf-8')).hexdigest() == row[0]:
                if password_form == row[0]:    
                    session['username'] = request.form['username']
                    return redirect(url_for('index'))
                else:
                    error = "Invalid Credential"
        else:
            error = "Invalid Credential"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/news",methods=['GET','POST'])
def get_news():
    select=1
    feed=''
    articles=''
    cursor = db.cursor()
    sql = "SELECT * From Channel"
    cursor.execute(sql)
    
    channelTup = cursor.fetchall()
    data = [list(t) for t in channelTup]
    print(data)
    if request.method == 'POST':
        select = request.form.get('comp_select')

        #if(select=="BBC"):
        print(select)
        print(type(select))
        
        feed = feedparser.parse(data[int(select)-1][2])
        #print(len(feed))
        size = 0
        articles = feed['entries']

        if(int(select)!=3):
            print(len(feed))
            while (size < len(feed)):
                #print(feed['entries'])
                first_article = feed['entries'][size]
                title = first_article.get("title")
                published = first_article.get("published")
                summary = first_article.get("summary")
                flash(title,'title')
                size+=1
        if(int(select)==3):
            print(len(feed))
            while (size < len(feed)-2):
                #print(feed['entries'])
                first_article = feed['entries'][size]
                title = first_article.get("title")
                published = first_article.get("published")
                summary = first_article.get("summary")
                flash(title,'title')
                size+=1
        
        
        
        
        '''
        if(select=="CNN"):
            feed = feedparser.parse(CNN_FEED)
            #print(len(feed))
            size = 0
            articles = feed['entries']
            
            while (size < len(feed)):
                first_article = feed['entries'][size]
                title = first_article.get("title")
                published = first_article.get("published")
                summary = first_article.get("summary")
                flash(title,'title')
                size+=1
        
        if(select=="FOX"):
            feed = feedparser.parse(FOX_FEED)
            print(len(feed))
            size = 0
            articles = feed['entries']
            

            while (size < len(feed)-2):
                print(size)
                first_article = feed['entries'][size]
                title = first_article.get("title")
                published = first_article.get("published")
                summary = first_article.get("summary")
                flash(title,'title')
                size+=1
        '''    
        if(select==4):
            feed = feedparser.parse(IOL_FEED)
            print(len(feed))
            size = 0
            articles = feed['entries']
            
            while (size < len(feed)-2):
                print(size)
                first_article = feed['entries'][size]
                title = first_article.get("title")
                published = first_article.get("published")
                summary = first_article.get("summary")
                flash(title,'title')
                size+=1

        
    #return render_template("hello.html",page_title="News headlines",data=[{'name':'BBC'}, {'name':'CNN'}, {'name':'FOX'},{'name':'Independent Online'}],articles=articles,select=select)
    select = data[int(select)-1][1]
    return render_template("hello.html",page_title="News headlines",data=data,articles=articles,select=select)

def get_rate(frm, to):
    all_currency = urlopen(CURRENCY_URL).read()
    parsed = json.loads(all_currency).get('rates')
    frm_rate = parsed.get(frm.upper())
    to_rate = parsed.get(to.upper())
    return (to_rate / frm_rate, parsed.keys())

if __name__ == "__main__":
    app.run(port=5000, debug=True)