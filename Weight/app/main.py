from flask import Flask, request, jsonify   

# GET /weight?from=t1&to=t2&filter=f


app = Flask(__name__)

@app.route("/weight", methods=["GET"], strict_slashes=False)
def get_weight():
    start_time = request.args.get('from')  # yyyymmddhhmmss Default is today at 00:00:00.
    end_time = request.args.get('to')      # yyyymmddhhmmss Default is now.
    directions= request.args.get('filter') # default is "in,out,none"

# recive data from DB, calculate the following,
# returns an array of json objects (data), one per weighing (batch NOT included):
#   data=[{
#   "id": <id>,
#   "direction": in/out/none,
#   "bruto": <int>, //in kg
#   "neto": <int> or "na" // na if some of containers have unknown tara
#   "produce": <str>,
#   "containers": [ id1, id2, ...]  }]
    return jsonify(data), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)