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

import time
import re
from socket import getfqdn

from twisted.internet import reactor

import Globals
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon
from Products.ZenEvents.ZenEventClasses import \
     Heartbeat, App_Start, App_Stop, Clear, Warning
from Products.ZenUtils.Driver import drive, driveLater

from Constants import TIMEOUT_CODE, RPC_ERROR_CODE, ERROR_CODE_MAP
 
class WinCollector(PBDaemon):

    configCycleInterval = 20.

    initialServices = ['EventService', 'WmiConfig']
    attributes = ('configCycleInterval',)

    heartbeat = dict(eventClass=Heartbeat, device=getfqdn())
    deviceConfig = 'getDeviceWinInfo'

    def __init__(self):
        self.heartbeat['component'] = self.agent
        self.wmiprobs = []
        PBDaemon.__init__(self)
        self.reconfigureTimeout = None


    def start(self):
        self.heartbeat['component']=self.agent
        self.log.info("Starting %s", self.agent)
        self.sendEvent(dict(summary='Starting %s' % self.agent,
                            eventClass=App_Start,
                            device=getfqdn(),
                            severity=Clear,
                            agent=self.agent,
                            component=self.agent))

    def remote_notifyConfigChanged(self):
        self.log.info("Async config notification")
        if self.reconfigureTimeout and not self.reconfigureTimeout.called:
            self.reconfigureTimeout.cancel()
        self.reconfigureTimeout = reactor.callLater(5, drive, self.reconfigure)

    def remote_deleteDevice(self, device):
        pass

    def processLoop(self):
        pass


    def startScan(self, unused=None):
        drive(self.scanCycle)


    def scanCycle(self, driver):
        now = time.time()
        try:
            yield self.eventService().callRemote('getWmiConnIssues')
            self.wmiprobs = [e[0] for e in driver.next()]
            self.log.debug("Wmi Probs %r", self.wmiprobs)
            self.processLoop()
            self.heartbeat['timeout'] = self.cycleInterval() * 3
            self.sendEvent(self.heartbeat)
        except Exception, ex:
            self.log.exception("Error processing main loop")
        delay = time.time() - now
        if self.options.cycle:
            driveLater(max(0, self.cycleInterval() - delay), self.scanCycle)
        else:
            self.stop()

    def stop(self):
        self.log.info("Starting %s", self.agent)
        self.sendEvent(dict(summary='Stopping %s' % self.agent,
                            eventClass=App_Stop,
                            device=getfqdn(),
                            severity=Warning,
                            component=self.agent))
        reactor.callLater(1, reactor.stop)

    def cycleInterval(self):
        return 60
        
    def buildOptions(self):
        PBDaemon.buildOptions(self)
        self.parser.add_option('-d', '--device', 
                               dest='device', 
                               default=None,
                               help="single device to collect")
        self.parser.add_option('--debug', 
                               dest='debug', 
                               default=False,
                               help="turn on additional debugging")


    def configService(self):
        return self.services.get('WmiConfig', FakeRemote())


    def updateDevices(self, cfg):
        pass


    def updateConfig(self, cfg):
        cfg = dict(cfg)
        for attribute in self.attributes:
            current = getattr(self, attribute, None)
            value = cfg.get(attribute)
            if current is not None and current != value:
                self.log.info("Setting %s to %r", attribute, value);
                setattr(self, attribute, value)

    def error(self, why):
        why.printTraceback()
        self.log.error(why.getErrorMessage())


    def reconfigure(self, driver):
        try:
            yield self.eventService().callRemote('getWmiConnIssues')
            self.wmiprobs = [e[0] for e in driver.next()]
            self.log.debug("Wmi Probs %r", self.wmiprobs)
            yield self.configService().callRemote('getConfig')
            self.updateConfig(driver.next())
            yield self.configService().callRemote(self.deviceConfig)
            self.updateDevices(driver.next())
        except Exception, ex:
            self.log.exception("Error fetching config")


    def startConfigCycle(self):
        def driveAgain(result):
            driveLater(self.configCycleInterval * 60, self.reconfigure)
            return result
        return drive(self.reconfigure).addBoth(driveAgain)

    def connected(self):
        d = self.startConfigCycle()
        d.addCallback(self.startScan)
        
    def parseComError(self, ex):
        match = re.search('com_error\((?P<code>[0-9]*)\).*', str(ex))
        if match:
            code = match.group('code')
            if ERROR_CODE_MAP.has_key(code):
                return (code,) + ERROR_CODE_MAP[code]
            else:
                return (code, None, None)
        else:
            return (None, None, None)
            
    def printComErrorMessage(self, ex):
        code, error, msg = self.parseComError(ex)
        if code and error and msg:
            return '%s: %s (%s)' % (error, msg, code)
        elif code:
            return 'Could not map the error code %s to a com_error' % code
        else:
            return None
        

