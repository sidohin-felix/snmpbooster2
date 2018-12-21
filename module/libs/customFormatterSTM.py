import json

#Original
#def prct(ds_data):#
#    try:
#        max_ = float(ds_data['ds_max_oid_value_computed'])
#    except:
#        raise Exception("Cannot calculate prct, max value for the "
#                        "datasource '%s' is missing" % ds_data['ds_name'])
#    return float(ds_data['ds_oid_value_computed']) * 100 / max_

def prct(value,max):
    try:
        return round((float(value)/float(max)) * 100.0)
    except:
        return None

#Original
#def diff(ds_data):
#    """ Are last computed value and last-1 computed  value the same ? """
#    return ds_data['ds_oid_value_computed'] == ds_data['ds_oid_value_last_computed']

def diff(currentVal,lastVal):
    return (currentVal == lastVal)


#def last(ds_data):
#    """ Get the last value computed """
#    return ds_data['ds_oid_value_computed']#

def last(value):
    return value


#Trigger dis-assembly function


def disassembleTrigger(complexTrigger,real_triggers):
    #Remove the "and_" values from the tail
    while(len(complexTrigger) % 3 != 0):
        complexTrigger = complexTrigger[:-2]
    #Now that we have removed the tail, we need to populate the real trigger map
    while(len(complexTrigger) != 0):
        component,function = complexTrigger[0].split(".")
        bound              = complexTrigger[1]
        comparator         = complexTrigger[2]
        if(component not in real_triggers.keys()):
            real_triggers[component] = {"function":function,"bound":bound,"comparator":comparator}
        complexTrigger = complexTrigger[3:]

def customOutputCreator(x):
    y = x.replace("\'", "\"").strip()
    y = y.replace("None", "null")
    y = y.replace("True", "true")
    y = y.replace(" ", "")
    y = y.replace("\n", "")
    y = y.replace("u\"", "\"")
    y = y.replace("False", "false")
    y = y.replace("OrderedDict([", "[")
    y = y.replace("})", "}")
    y = y.replace("])", "]")
    y = y.replace("(\"", "\"")
    z = json.loads(y)

    # First, we prepare the sensor data which will be used to return statuses.

    temp = z['db_data']['ds']
    sensor_data = {}

    i = 0
    while (i < len(temp)):
        sensor_data[temp[i]] = temp[i + 1]
        i = i + 2

    # This is largely debug, feel free to ignore it
    # for key in sensor_data.keys():
    #    print(key)
    #    print(sensor_data[key])

    # Now we need to read the triggers, the issue is the trigers are composite, so it's unclear which
    # of the actual components are "failed", in this case we propose taking the first in the warning
    # and if no warning then critical - it's a big "hack-ish" but whatever.

    real_triggers = {}
    temp = z['db_data']['triggers']

    # This is largely debug, feel free to ignore it
    for key in dict(temp).keys():
        if ("warning" in temp[key]):
            composite_trigger = temp[key]['warning']
            if composite_trigger is not None: disassembleTrigger(composite_trigger, real_triggers)
        elif ("critical" in temp[key]):
            composite_trigger = temp[key]['warning']
            if composite_trigger is not None: disassembleTrigger(composite_trigger, real_triggers)

    # Now we can match sensor data and the triggers easily, basically for each we have component:{value:1000,state:OK)

    state_map = {}

    for component in sensor_data:
        if component in real_triggers.keys():
            # This is a big more complicated, so I'll try to handle this.
            state = None
            function = real_triggers[component]['function']
            if function == "last()":
                state = last(sensor_data[component]['ds_oid_value_computed'])
            elif function == "diff()":
                state = diff(sensor_data[component]['ds_oid_value_computed'],
                                       sensor_data[component]['ds_oid_value_last_computed'])
            elif function == "prct()":
                state = prct(sensor_data[component]['ds_oid_value_computed'],
                                       sensor_data[component]['ds_max_oid_value_computed'])
            state_map[component] = {}
            state_map[component]['value'] = sensor_data[component]['ds_oid_value']
            if state is None:
                state_map[component]['state'] = "NOT OK"
            else:
                #Use the data from the real triggers to get this one:
                if real_triggers[component]['comparator'] == 'eq' and state != float(real_triggers[component]['bound']):
                    state_map[component]['state'] = "NOT OK"
                elif real_triggers[component]['comparator'] == 'gt' and state > float(real_triggers[component]['bound']):
                    state_map[component]['state'] = "NOT OK"
                elif real_triggers[component]['comparator'] == 'lt' and state < float(real_triggers[component]['bound']):
                    state_map[component]['state'] = "NOT OK"
                else:
                    state_map[component]['state'] = "OK"
        else:
            state_map[component] = {}
            state_map[component]['value'] = sensor_data[component]['ds_oid_value']
            state_map[component]['state'] = "OK"

    #Now we format the state map into a string and return it.
    #SNMP OK - nom = STATE(metrique), nom2 = STATE(metrique)
    output = ""
    for key in state_map.keys():
        output = output + key + " = " + state_map[key]['state'] + " (" + str(state_map[key]['value']) + "), "
    return output[:-2]


if __name__ == '__main__':
    with open("/Users/felixsidokhine/Untitled-8.json", 'r') as fin:
        x = fin.read()
    print(customOutputCreator(x))
