#!/usr/bin/env python

# Copyright (c) 2011 Recoset <nicolas@recoset.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# IS24: Add Holt-Winters and debug/verbose at Do 4. Jul 17:45:29 CEST 2013    
# IS24: Add sixSigma at Thu Feb 20 16:10:17 CET 2014

from NagAconda import Plugin
import argparse
import urllib2
import sys

# Methods
def f_avg(values):
  return sum(values)/len(values)

def f_last(values):
  return values[-1]

def f_min(values):
  return min(values)

def f_max(values):
  return max(values)

def f_sum(values):
  return sum(values)

def f_hw(values):
    pass

functionmap = {
  "hw":{  "label": "hw", "function": f_hw },
  "sixSigma":{  "label": "sixSigma", "function": lambda x: None},
  "avg":{  "label": "average", "function": f_avg },
  "last":{ "label": "last",    "function": f_last },
  "min":{  "label": "minimum", "function": f_min },
  "max":{  "label": "maximum", "function": f_max },
  "sum":{  "label": "sum",  "function": f_sum }
}

def exit_ok(error_message):
    print "OK: %s" % error_message
    sys.exit(0)

def exit_warning(error_message):
    print "Warning: %s" % error_message
    sys.exit(1)

def exit_critical(error_message):
    print "Critical: %s" % error_message
    sys.exit(2)

def exit_unknown(error_message):
    print "Unknown: %s" % error_message
    sys.exit(3)

# Methods for Holt-Winters
def eval_graphite_data(data, seconds):
    
    sample_period = int(data.split('|')[0].split(',')[-1])
    all_data_points = data.split('|')[-1].split(',')

    # Evaluate what graphite returned, should either be a float, or None
    # First, if the number of seconds of data we want to examine is smaller or
    # equals the graphite sample period, just grab the latest data point.
    # If that data point is None, grab the one before it.
    # If that is None too, return 0.0.
    if seconds <= sample_period:
        if eval(all_data_points[-1]):
            data_value = float(all_data_points[-1])
        elif eval(all_data_points[-2]):
            data_value = float(all_data_points[-2])
        else:
            data_value = 0.0
    else:
    # Second, if we requested more than on graphite sample period, work out how
    # many sample periods we wanted (python always rounds division *down*)
        data_points = (seconds/sample_period)
        data_set = [ float(x) for x in all_data_points[-data_points:]
                     if eval(x) ]
        if data_set:
            data_value = float( sum(data_set) / len(data_set) )
        else:
            data_value = 0.0
    return data_value

def get_confindence_bands(hwdata, seconds=0, prefix='holtWintersConfidence'):
    """Get confidence bands value from a Graphite graph"""

    data = hwdata
    for line in data.split('\n'):
        if line.startswith(prefix + 'Mean'):
            continue
        elif line.startswith(prefix + 'Upper'):
            graphite_upper = eval_graphite_data(line, seconds)
        elif line.startswith(prefix + 'Lower'):
            graphite_lower = eval_graphite_data(line, seconds)
        else:
            graphite_data = eval_graphite_data(line, seconds)

    return graphite_data, graphite_lower, graphite_upper
  


# test if there are too much of none values in raw data
def check_max_none_values(values, maxnones, treatnonescritical):

    if values:
        nones_limit=float(maxnones)
        nones_count=float(values.count("None"))
        values_count=float(len(values))

        percent_nones = 100 * nones_count/values_count
        if percent_nones > nones_limit:
            message = "Over %s percent (limit) of values are None. (sum values : %s, sum \"None\" : %s, percent \"None\": %.2f%%)" % (str(nones_limit),str(values_count),str(nones_count),percent_nones)

            if treatnonescritical:
                exit_critical(message)
            else:
                exit_unknown(message)

# retrieve data from graphite host
def get_data_from_graphite(url):
    try:
        request = urllib2.Request(url, headers={'Accept-Encoding': ''})
        socket = urllib2.urlopen(request)
        data = socket.read().rstrip()
        socket.close()
    except Exception as exception:
        exit_unknown("Could not retrieve data from graphite: %s") % str(exception)
    return data

def get_metrics_count(data):
    return len(data.strip().split('\n'))

def parse_rawdata(raw_data):
    pieces = raw_data.split("|")
    counter = pieces[0].split(",")[0]
    values = pieces[1].split(",")
    return counter, values

def evaluate_single_metric(raw_data):
    if get_metrics_count(rawdata) > 1:
        exit_unknown("Graphite returned multiple metrics, need only one to check!")

    counter, values = parse_rawdata(raw_data)

    check_max_none_values(values)

    if args.ignorenones:
        values = map(lambda x: float(x), filter(lambda x: x != 'None', values))
        if debug:
            print "[Debug] None values are ignored (removed):\n%s\n" % values
    else:
        values = map(lambda x: 0.0 if x == 'None' else float(x), values)
        if debug == 'yes':
            print "[Debug] None values are not ignored (NONE = 0.0):\n%s\n" % values
    if len(values) == 0:
        exit_unknown("Graphite returned an empty list of values")
    else:
        value = functionmap[args.function]["function"](values)
    if debug == 'yes':
        print "[Debug] Average value from this script:\n%s\n" % str(value)

    graphite.set_value(counter, value)
    graphite.set_status_message("%s value of %s: %f" % (functionmap[args.function]["label"], counter, value))

    # TODO: print perfdata

def evaluate_holt_winters_metric(rawdata):
    if get_metrics_count(rawdata) != 3:
        exit_unknown("Graphite did not return 3 metrics, check your configuration!")

    graphite_data, graphite_lower, graphite_upper = get_confindence_bands(rawdata, 0)
    print "Current value: %s, lower band: %s, upper band: %s" % (graphite_data, graphite_lower, graphite_upper)

    # TODO: check if this is a good idea and use exit functions
    if (graphite_data > graphite_upper) or (graphite_data < graphite_lower):
        if args.critupper == 'yes' or args.critlower == 'yes' :
            sys.exit(2)
        else:
            sys.exit(1)
    else:
        sys.exit(0)

# main action
def main(args):

    global debug
    # check if debug option is set
    if args.debug:
        print "debug mode on"
        debug = True
    else:
        debug = False

    if args.function not in functionmap:
        exit_unknown("Bad function name given to --function option: '%s'" % args.function)

    data = get_data_from_graphite(args.url)

    if args.function == "hw":
        evaluate_holt_winters_metric(data)
    else:
        evaluate_single_metric(data)


# parameter handling separation
if __name__ == '__main__':
    # parameter handling
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to query for data", type=str)
    parser.add_argument("--debug", help="Debug/verbose mode", action="store_true")
    parser.add_argument("--maxnones", help="Number of percent of None values as limit e.g. -m 5 means less then 5 percent of None values are allowed.(default=20%)", default=20, type=int)
    parser.add_argument("--ignorenones", help="Ignore None values", action="store_true", default=False)
    parser.add_argument("--treatnonescritical", help="Print a critical status instead of a warning if none level is exceeded", action="store_true", default=False)
    parser.add_argument("--critupper", help="Upper Holt-Winters band breach causes a crit - breaching lower band causes a warn - use it together with -f hw.", action="store_true", default=True)
    parser.add_argument("--critlower", help="Lower Holt-Winters band breach causes a crit - breaching upper band causes a warn - use it together with -f hw.", action="store_true", default=True)
    parser.add_argument("--function", help="Function to run on retrieved values: avg/min/max/last/sum/hw (hw = Holt-Winters). Default is 'avg'", type=str, default="avg")
    parser.add_argument("--printperformancedata", help="Add performance data to output", action="store_true", default=True)
    parser.add_argument("-w", help="Warning treshold", type=float)
    parser.add_argument("-c", help="Critical treshold", type=float)
    args = parser.parse_args()
    main(args)