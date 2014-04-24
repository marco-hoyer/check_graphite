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
    """Get confidene bands value from a Graphite graph"""

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
  
def f_hw(values):
    pass

# is24 Max None method
def check_max_none_values(values):
    if not graphite.options.maxnone.isdigit():
        print "Limit of None values have to be a digit (false param : -m %s)" % (str(graphite.options.maxnone))
        sys.exit(3)
    none_limit=float(graphite.options.maxnone)
    percent_nones = 100 * float(values.count("None"))/float(len(values))
    
    if graphite.options.treatnonescritical == "no":
      status_output = "Status UNKNOWN"
      nones_exceeded_exit_code = 3
    else:
      status_output = "Status CRITICAL"
      nones_exceeded_exit_code = 2      
  
    if percent_nones > none_limit:
        print "%s, over %s percent (limit) of values are None. (sum values : %s, sum \"None\" : %s, percent \"None\": %.2f%%)" % (status_output,str(none_limit),str(len(values)),str(values.count("None")),percent_nones) 
        sys.exit(nones_exceeded_exit_code)           
    return

# retrieve data from graphite host
def get_data_from_graphite(url):
    req = urllib2.Request(url, headers={'Accept-Encoding': ''})
    usock = urllib2.urlopen(req)
    data = usock.read().rstrip()
    usock.close()

    if graphite.options.debug == 'yes':
        print "\n[Debug] Origin data from Graphite:\n%s" % data

    return data

functionmap = {
  "hw":{  "label": "hw", "function": f_hw },
  "sixSigma":{  "label": "sixSigma", "function": lambda x: None},
  "avg":{  "label": "average", "function": f_avg },
  "last":{ "label": "last",    "function": f_last },
  "min":{  "label": "minimum", "function": f_min },
  "max":{  "label": "maximum", "function": f_max },
  "sum":{  "label": "sum",  "function": f_sum }
}

graphite = Plugin("Plugin to retrieve data from graphite", "1.0")
graphite.add_option("u", "url", "URL to query for data", required=True)
graphite.add_option("U", "username", "User for authentication")
graphite.add_option("P", "password", "Password for authentication")
graphite.add_option("d", "debug", "Debug/verbose mode ('yes' or 'no' , default = no)", default="no")
graphite.add_option("H", "hostname", "Host name to use in the URL")
graphite.add_option("m", "maxnone", "Number of percent of None values as limit e.g. -m 5 means less then 5 percent of None values are allowed.(default=20%)",default="20")
graphite.add_option("n", "none", "Ignore None values: 'yes' or 'no' (default no)")
graphite.add_option("e", "treatnonescritical", "Print a critical status instead of a warning if none level is exceeded - ignored in -n option is used ('yes' or 'no', default = no)",default="no")
graphite.add_option("h", "critupper", "Upper Holt-Winters band breach causes a crit - breaching lower band causes a warn - use it together with -f hw. ('yes' or 'no', default = yes)",default="yes")
graphite.add_option("l", "critlower", "Lower Holt-Winters band breach causes a crit - breaching upper band causes a warn - use it together with -f hw. ('yes' or 'no', default = yes)",default="yes")
graphite.add_option("f", "function", "Function to run on retrieved values: avg/min/max/last/sum/hw (hw = Holt-Winters). Default is 'avg'", default="avg")
graphite.add_option("p", "printperformancedata", "Add performance data to output", default="yes")

graphite.enable_status("warning")
graphite.enable_status("critical")
graphite.start()

if graphite.options.username and graphite.options.password:
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None,uri=graphite.options.url,
                            user=graphite.options.username,
                            passwd=graphite.options.password)
    auth_handler =urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)

if graphite.options.hostname:
    graphite.options.url = graphite.options.url.replace('@HOSTNAME@', 
    graphite.options.hostname.replace('.','_'))

if graphite.options.function not in functionmap:
    graphite.unknown_error("Bad function name given to -f/--function option: '%s'" % graphite.options.function)

data = get_data_from_graphite(graphite.options.url)

if graphite.options.function in ['hw', 'sixSigma']:
    if graphite.options.function == 'hw':
        prefix = 'holtWintersConfidence'
    elif graphite.options.function == 'sixSigma':
        prefix = 'sixSigma'
    else:
        raise Exception

    # Here we handle the data as Holt-Winters and exit with message - all without NagAconda functionality because NagAconda can't do Holt-Winters  
    if len(data.strip().split('\n')) == 1:
        raise 'Graphite returned one line but three lines are needed for Holt-Winters (hw)'
    graphite_data, graphite_lower, graphite_upper = get_confindence_bands(data, 0, prefix)
    print "Current value: %s, lower band: %s, upper band: %s" % (graphite_data, graphite_lower, graphite_upper)
    if (graphite_data > graphite_upper) or (graphite_data < graphite_lower):
        if graphite.options.critupper == 'yes' or graphite.options.critlower == 'yes' :
            sys.exit(2)
        else:
            sys.exit(1)
    else:
        sys.exit(0)

    sys.exit(6)
else:
    # Here is the normal NagAconda handle (even not Holt-Winters)  
    try:
        pieces = data.split("|")
        counter = pieces[0].split(",")[0]
        values = pieces[1].split(",")      
        if len(data.strip().split('\n')) > 1:
            raise 'Graphite returned multiple lines'
    except:
        graphite.unknown_error("Graphite returned bad data")
    
    # Here we are check proportion of None values in the sum of values and exit with unknown if max limit is reached  
    check_max_none_values(values)         
                     
    if graphite.options.none == 'yes':
        values = map(lambda x: float(x), filter(lambda x: x != 'None', values))
        if graphite.options.debug == 'yes':
            print "[Debug] None values are ignored (removed):\n%s\n" % values
    else:
        values = map(lambda x: 0.0 if x == 'None' else float(x), values)
        if graphite.options.debug == 'yes':
            print "[Debug] None values are not ignored (NONE = 0.0):\n%s\n" % values
    if len(values) == 0:
        graphite.unknown_error("Graphite returned an empty list of values")
    else:
        value = functionmap[graphite.options.function]["function"](values)
    if graphite.options.debug == 'yes':
        print "[Debug] Average value from this script:\n%s\n" % str(value)   
    
    graphite.set_value(counter, value)
    
    graphite.set_status_message("%s value of %s: %f" % (functionmap[graphite.options.function]["label"], counter, value))

    try :
        if graphite.options.printperformancedata == "yes":
          graphite.set_print_performance_data(True)
        else:
          graphite.set_print_performance_data(False)
    except AttributeError:
        pass
    
    graphite.finish()

