from flask import Flask, json, Response
import requests
import simplejson
from bs4 import BeautifulSoup

app = Flask(__name__)


@app.route('/api/journals', methods=['GET'])
def get_journals():

    r = requests.get("https://cos.io/static/topjournals.json")
    response_json = None
    status = 200

    try:

        response_json = json.dumps(json.loads(r.content))

    except Exception as e:
        status = 500
        response_json = e.message

    return Response(response_json, status=200, mimetype='application/json')



@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run(debug=True)
