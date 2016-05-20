from flask import Flask, json, Response, request, render_template, session, flash, redirect, url_for, jsonify
import requests
import simplejson
import os
from celery import Celery
from helpers.search import parse_search_input

app = Flask(__name__)
app.config['SECRET_KEY'] = '#very-secret-key-123'

redis_host = os.getenv("REDIS_PORT_6379_TCP_ADDR") or "10.10.23.32"
redis_url = 'redis://{0}:6379/0'.format(redis_host)

print redis_url

# Celery configuration
app.config['CELERY_BROKER_URL'] = redis_url
app.config['CELERY_RESULT_BACKEND'] = redis_url

# Initialize Celery
# celery = Celery(app.name, broker=redis_url, backend=redis_url)

celery = Celery(app.name)
celery.conf.update(app.config)


@celery.task(bind=True)
def search_task(self, search_input):

    results = []
    what, options = parse_search_input(search_input)

    journals_list = []
    with open(os.path.dirname(os.path.realpath(__file__)) + "/data/journals.json", "r") as f:
            journals_list = simplejson.loads(f.read())

    # journal_title = "Acta Psychologica".replace(" ", "+")
    for journal in journals_list[:1]:
        journal_title = journal["Journal Title"]
        print journal_title

        term = journal_title.replace(" ", "+")
        journals_search_url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term={0}+AND+{1}".format(term, options.year)
        journals_search_response = requests.request("GET", journals_search_url)
        print journals_search_response.content

        journals_search_content = simplejson.loads(journals_search_response.content)

        for id in journals_search_content["esearchresult"]["idlist"]:
            article_search_url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={0}&retmode=json".format(id)
            article_search_response = requests.request("GET", article_search_url)
            article_search_content = simplejson.loads(article_search_response.content)

            print "ID " + id

            if "error" not in article_search_content["result"][id]:

                pubdate = article_search_content["result"][id]["epubdate"]
                source = article_search_content["result"][id]["source"]
                title = article_search_content["result"][id]["title"]

                for item in article_search_content["result"][id][what]:
                    item["journal_title"] = journal_title
                    item["pubdate"] = pubdate
                    item["source"] = source
                    item["title"] = title
                    item["id"] = id
                    item["url"] = article_search_url
                    print ">>> {0}".format(item)
                    results.append(item)
                    self.update_state(state="PROGRESS",
                                      meta={"items": results, "total": len(results)})

    return {"total": len(results), "items": results}



@app.route('/api/search', methods=['POST'])
def do_search():

    response = ""
    status = 200

    try:

        print request.form["search"]
        task = search_task.apply_async(args=[request.form["search"]])
        response = {"task_id": task.id}

    except Exception as e:
        status = 500
        response = e.message

    return Response(simplejson.dumps(response), status=status, mimetype='application/json')


@app.route('/api/search/status/<task_id>')
def do_search_status(task_id):

    task = search_task.AsyncResult(task_id)

    print task.state

    if task.state != "FAILURE" and task.info:
        response = {
            "state": task.state,
            "results": task.info.get("items", []),
            "total": task.info.get("total", 0)
        }

    elif task.state == "SUCCESS" and task.info:
        response = {
            "state": task.state,
            "results": task.info.get("items", []),
            "total": task.info.get("total", 0)
        }

    else:
        response = {
            'state': task.state,
            # 'status': str(task.info),  # this is the exception raised
        }

    return Response(simplejson.dumps(response), status=200, mimetype='application/json')


@app.route('/api/journals', methods=['GET'])
def get_journals():

    response_json = None
    status = 200

    try:

        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/journals.json", "r") as f:
            response_json = f.read()

    except Exception as e:
        status = 500
        response_json = e.strerror

    return Response(response_json, status=200, mimetype='application/json')



@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    return redirect(url_for('index'))


if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host="0.0.0.0")

    # venv\Scripts\celery worker -A main.celery --loglevel=info
