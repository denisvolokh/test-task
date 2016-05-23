from flask import Flask, json, Response, request, render_template, session, flash, redirect, url_for, jsonify
import requests
import simplejson
import os
from celery import Celery
from helpers.search import parse_search_input
from celery import group
from celery.result import GroupResult

app = Flask(__name__)
app.config['SECRET_KEY'] = '#very-secret-key-123'

redis_host = os.getenv("REDIS_PORT_6379_TCP_ADDR", "127.0.0.1")
redis_url = 'redis://{0}:6379/0'.format(redis_host)

# Celery configuration
app.config['CELERY_BROKER_URL'] = redis_url
app.config['BROKER_URL'] = redis_url
# app.config['BROKER_BACKEND'] = redis_url
app.config['CELERY_RESULT_BACKEND'] = redis_url

# Initialize Celery
celery = Celery(app.name)
celery.conf.update(app.config)


@celery.task
def search_sub_task(id, what):
    """
        Single celery task to request journal data by ID.

        Returns list of authors.
    """

    results = []

    article_search_url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={0}&retmode=json".format(id)
    article_search_response = requests.request("GET", article_search_url)
    article_search_content = simplejson.loads(article_search_response.content)

    print "ID " + id

    if "error" not in article_search_content["result"][id]:

        pubdate = article_search_content["result"][id]["epubdate"]
        source = article_search_content["result"][id]["source"]
        title = article_search_content["result"][id]["title"]

        for item in article_search_content["result"][id][what]:
            # item["journal_title"] = journal_title
            item["pubdate"] = pubdate
            item["source"] = source
            item["title"] = title
            item["id"] = id
            item["url"] = article_search_url
            results.append(item)

    return results

@celery.task(bind=True)
def search_task(self, search_input):
    """
        Celery task. It creates group of tasks to execute it in concurrently.

        Returns group id.
    """

    results = []
    what, options = parse_search_input(search_input)

    journals_list = []
    with open(os.path.dirname(os.path.realpath(__file__)) + "/data/journals.json", "r") as f:
            journals_list = simplejson.loads(f.read())

    tasks = []

    for journal in journals_list[:2]:
        journal_title = journal["Journal Title"]

        term = journal_title.replace(" ", "+")
        journals_search_url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term={0}+AND+{1}".format(term, options.year)
        journals_search_response = requests.request("GET", journals_search_url)

        journals_search_content = simplejson.loads(journals_search_response.content)
        idlist = journals_search_content["esearchresult"]["idlist"]

        # Create list of sub tasks to search journals by ID
        for id in idlist:
            tasks.append(search_sub_task.subtask(args=(id, "authors")))

    # Start all tasks in group asynchronously and concurrently
    tasks_group_result = group(tasks).apply_async()
    tasks_group_result.save()

    return {"total": len(results), "items": results, "tasks_group_id" : tasks_group_result.id}



@app.route('/api/search', methods=['POST'])
def do_search():
    """
        HTTP POST request to start search.

    """

    response = ""
    status = 200

    try:

        print request.form["search"]

        # Start search_task asynchronously and return task id
        task = search_task.apply_async(args=[request.form["search"]])
        response = {"task_id": task.id}

    except Exception as e:
        status = 500
        response = e.message

    return Response(simplejson.dumps(response), status=status, mimetype='application/json')


@app.route('/api/search/status/<task_id>')
def do_search_status(task_id):
    """
        Check task status by ID

    :param task_id:
    :return:
    """

    response = {"state": "PENDING"}

    # Retrieve search task by ID
    task = search_task.AsyncResult(task_id)

    if task.info:

        tasks_group_id = task.info.get("tasks_group_id")

        # Get restore group data by ID
        tasks_group_result = celery.GroupResult.restore(tasks_group_id)

        # Was all of the tasks successful?
        if tasks_group_result.successful():

            # If successful join all results in one list
            results = tasks_group_result.join()

            total_result = []
            for results_list in results:
                total_result += results_list

            response = {
                "state": "SUCCESS",
                "results": total_result
            }

        elif tasks_group_result.failed():
            response = {
                "state": "FAILED"
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
        response_json = e.message

    return Response(response_json, status=200, mimetype='application/json')



@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    return redirect(url_for('index'))


if __name__ == '__main__':

    env = os.getenv("env", "DEV")

    if env == "DEV":
        app.run(debug=True)

    else:
        app.run(host="0.0.0.0")

    # venv\Scripts\celery worker -A main.celery --loglevel=info
