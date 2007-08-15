###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.ZenTales import talesEval
from Products.ZenEvents.ZenEventClasses import Perf_Snmp


def rpneval(value, rpn):
    """totally bogus rpn valuation only works with one level stack"""
    if value is None: return value
    operators = ('+','-','*','/')
    rpn = rpn.split(',')
    operator = ''
    for i in range(len(rpn)):
        symbol = rpn.pop()
        symbol = symbol.strip()
        if symbol in operators:
            operator = symbol
        else:
            expr = str(value) + operator + symbol
            value = eval(expr)
    return value


def manage_addRRDThreshold(context, id, REQUEST = None):
    """make a RRDThreshold"""
    tt = RRDThreshold(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

addRRDThreshold = DTMLFile('dtml/addRRDThreshold',globals())

class RRDThreshold(ZenModelRM, ZenPackable):
    
    meta_type = 'RRDThreshold'
    
    security = ClassSecurityInfo()
 
    dsnames = []
    minval = ""
    maxval = ""
    eventClass = Perf_Snmp
    severity = 3
    escalateCount = 0
    enabled = True

    _properties = (
                 {'id':'dsnames', 'type':'lines', 'mode':'w'},
                 {'id':'minval', 'type':'string', 'mode':'w'},
                 {'id':'maxval', 'type':'string', 'mode':'w'},
                 {'id':'eventClass', 'type':'string', 'mode':'w'},
                 {'id':'severity', 'type':'int', 'mode':'w'},
                 {'id':'escalateCount', 'type':'int', 'mode':'w'},
                 {'id':'enabled', 'type':'boolean', 'mode':'w'},
                )

    _relations =  ZenPackable._relations + (
        ("rrdTemplate", ToOne(ToManyCont,"Products.ZenModel.RRDTemplate", "thresholds")),
        )


    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDThreshold',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'RRD Threshold'
            , 'action'        : 'editRRDThreshold'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )
    
    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from RRDTemplate import crumbspath
        crumbs = super(RRDThreshold, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -2)


    def getConfig(self, context):
        """Return the config used by the collector to process simple min/max
        thresholds. (id, minval, maxval, severity, escalateCount)
        """
        return (self.id,self.getMinval(context),self.getMaxval(context),
                self.eventClass, self.severity,self.escalateCount)

  
    def getMinval(self, context):
        """Build the min value for this threshold.
        """
        minval = None
        if self.minval:
            minval = talesEval("python:"+self.minval, context)
        return minval


    def getMaxval(self, context):
        """Build the max value for this threshold.
        """
        maxval = None
        if self.maxval:
            maxval = talesEval("python:"+self.maxval, context)
        return maxval


    def getGraphMinval(self, context):
        return self.getGraphValue(context, self.getMinval)


    def getGraphMaxval(self, context):
        return self.getGraphValue(context, self.getMaxval)


    def getGraphValue(self, context, getfunc):
        """when graphing use this so that rpn conversions are accounted for"""
        val = getfunc(context)
        if val is None or len(self.dsnames) == 0: return 
        dp = self.getRRDDataPoint(self.dsnames[0])
        if dp and dp.rpn:
            #When VDEF does full rpn
            #val = "%s,%s" % (val, dp.rpn)
            val = rpneval(val, dp.rpn)
        return val


    def getMinLabel(self, context):
        """build a label for a min threshold"""
        return "%s < %s" % (self.id,self.setPower(self.getGraphMinval(context)))


    def getMaxLabel(self, context):
        """build a label for a max threshold"""
        return "%s > %s" % (self.id,self.setPower(self.getGraphMaxval(context)))


    def setPower(self, number):
        powers = ("k", "M", "G")
        if number < 1000: return number
        for power in powers:
            number = number / 1000
            if number < 1000:  
                return "%0.2f%s" % (number, power)
        return "%.2f%s" % (number, powers[-1])


    def getSeverityString(self):
        return self.ZenEventManager.getSeverityString(self.severity)


InitializeClass(RRDThreshold)
