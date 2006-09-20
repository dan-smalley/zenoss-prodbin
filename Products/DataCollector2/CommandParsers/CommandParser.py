#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__ = """CommandParser

CommandParser parses the output of a command to return a datamap

$Id: CommandParser.py,v 1.1 2003/09/25 16:21:52 edahl Exp $"""

__version__ = '$Revision: 1.1 $'[11:-2]

import re

from Products.DataCollector.ObjectMap import ObjectMap
from Products.DataCollector.RelationshipMap import RelationshipMap

class CommandParser:

    #Subclasses must fill this in with appropriate command
    command = ''
   
    prepId = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')


    def newObjectMap(self, className=None):
        return ObjectMap(className)

    def newRelationshipMap(self, relationshipName, componentName=""):
        return RelationshipMap(relationshipName, componentName)
        
    def condition(self, device, snmpsess):
        """does device meet the proper conditions for this collector to run"""
        return 0


    def parse(self, results, log):
        """collect snmp information from this device
        device is the a Device class (or subclass) object
        snmpsess is a valid instance of SnmpSession to connect
        to this device"""
        pass


    def description(self):
        """return a description of what this map does"""
        pass
