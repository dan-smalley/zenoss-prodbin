###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from itertools import islice
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.jsonutils import unjson
from Products import Zuul
from Products.Zuul.routers import TreeRouter
from Products.Zuul.form.interfaces import IFormBuilder

import logging
log = logging.getLogger('zen.Zuul')


class DeviceRouter(TreeRouter):

    def _getFacade(self):
        return Zuul.getFacade('device', self.context)

    def getTree(self, id):
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getComponents(self, uid=None, meta_type=None, keys=None, start=0, limit=50,
                      sort='name', dir='ASC', name=None):
        facade = self._getFacade()
        comps = facade.getComponents(uid, meta_type=meta_type, start=start,
                                     limit=limit, sort=sort, dir=dir,
                                     name=name)
        data = Zuul.marshal(comps, keys=keys)
        return DirectResponse(data=data, totalCount=comps.total,
                              hash=comps.hash_)

    def getComponentTree(self, uid=None, id=None):
        if id:
            uid=id
        facade = self._getFacade()
        data = facade.getComponentTree(uid)
        sevs = [c[0].lower() for c in
                self.context.ZenEventManager.severityConversions]
        data.sort(cmp=lambda a,b:cmp(sevs.index(a['severity']),
                                     sevs.index(b['severity'])))
        result = []
        for datum in data:
            result.append(dict(
                id=datum['type'],
                path='Components/%s' % datum['type'],
                text={
                    'text':datum['type'],
                    'count':datum['count'],
                    'description':'components'
                },
                iconCls='tree-severity-icon-small-'+datum['severity'],
                leaf=True
            ))
        return result

    def getForm(self, uid):
        info = self._getFacade().getInfo(uid)
        form = IFormBuilder(info).render()
        return DirectResponse(form=form)

    def getInfo(self, uid, keys=None):
        facade = self._getFacade()
        process = facade.getInfo(uid)
        data = Zuul.marshal(process, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return DirectResponse(data=data, disabled=disabled)

    def setInfo(self, **data):
        facade = self._getFacade()
        if not Zuul.checkPermission('Manage DMD'):
            raise Exception('You do not have permission to save changes.')
        process = facade.getInfo(data['uid'])
        Zuul.unmarshal(data, process)
        return DirectResponse()

    def getDevices(self, uid=None, start=0, params=None, limit=50, sort='name',
                   dir='ASC'):
        facade = self._getFacade()
        if isinstance(params, basestring):
            params = unjson(params)
        devices = facade.getDevices(uid, start, limit, sort, dir, params)
        keys = ['name', 'ipAddress', 'productionState', 'events']
        data = Zuul.marshal(devices, keys)
        return DirectResponse(devices=data, totalCount=devices.total,
                              hash=devices.hash_)

    def moveDevices(self, uids, target, hashcheck, ranges=(), uid=None,
                    params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)

        facade = self._getFacade()
        try:
            facade.moveDevices(uids, target)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to move devices.')
        else:
            target = '/'.join(target.split('/')[:4])
            tree = self.getTree(target)
            return DirectResponse.succeed(tree=tree)

    @require('Change Device')
    def lockDevices(self, uids, hashcheck, ranges=(), updates=False,
                    deletion=False, sendEvent=False, uid=None, params=None,
                    sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        success = True
        try:
            facade.setLockState(uids, deletion=deletion, updates=updates,
                                sendEvent=sendEvent)
            if not deletion and not updates:
                message = "Unlocked %s devices."
            else:
                actions = []
                if deletion: actions.append('deletion')
                if updates: actions.append('updates')
                message = "Locked %%s devices from %s." % ' and '.join(actions)
            return DirectResponse.succeed(message)
            message = message % len(uids)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to lock devices.')

    @require('Change Device')
    def resetIp(self, uids, hashcheck, uid=None, ranges=(), params=None,
                sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.ipAddress = '' # Set to empty causes DNS lookup
            return DirectResponse('Reset %s IP addresses.' % len(uids))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to reset IP addresses.')

    @require('Change Device')
    def resetCommunity(self, uids, hashcheck, uid=None, ranges=(), params=None,
                      sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                facade.resetCommunityString(uid)
            return DirectResponse('Reset %s community strings.' % len(uids))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to reset community strings.')

    @require('Change Device Production State')
    def setProductionState(self, uids, prodState, hashcheck, uid=None,
                           ranges=(), params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.productionState = prodState
            return DirectResponse()
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change production state.')

    @require('Change Device')
    def setPriority(self, uids, priority, hashcheck, uid=None, ranges=(),
                    params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.priority = priority
            return DirectResponse('Set %s devices to %s priority.' % (
                len(uids), info.priority
            ))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change priority.')

    @require('Change Device')
    def setCollector(self, uids, collector, hashcheck, uid=None, ranges=(),
                     params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.collector = collector
            return DirectResponse('Changed collector to %s for %s devices.' %
                                  (collector, len(uids)))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change the collector.')

    def setComponentsMonitored(self, uids, hashcheck, uid=None, ranges=(),
                               monitored=False, meta_type=None, keys=None,
                               start=0, limit=50, sort='name', dir='ASC',
                               name=None):
        if ranges:
            uids += self.loadComponentRanges(ranges, hashcheck, uid, (),
                                             meta_type, start, limit, sort,
                                             dir, name)
        facade = self._getFacade()
        facade.setMonitored(uids, monitored)
        return DirectResponse.succeed(('Set monitoring to %s for %s'
                                       ' components.') % (monitored, len(uids)))

    def lockComponents(self, uids, hashcheck, uid=None, ranges=(),
                       updates=False, deletion=False, sendEvent=False,
                       meta_type=None, keys=None, start=0, limit=50,
                       sort='name', dir='ASC', name=None):
        if ranges:
            uids += self.loadComponentRanges(ranges, hashcheck, uid, (),
                                             meta_type, start, limit, sort,
                                             dir, name)
        facade = self._getFacade()
        try:
            facade.setLockState(uids, deletion=deletion, updates=updates,
                                sendEvent=sendEvent)
            if not deletion and not updates:
                message = "Unlocked %s components."
            else:
                actions = []
                if deletion: actions.append('deletion')
                if updates: actions.append('updates')
                message = "Locked %%s components from %s." % ' and '.join(actions)
            return DirectResponse.succeed(message)
            message = message % len(uids)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to lock components.')

    def deleteComponents(self, uids, hashcheck, uid=None, ranges=(),
                         meta_type=None, keys=None, start=0, limit=50,
                         sort='name', dir='ASC', name=None):
        if ranges:
            uids += self.loadComponentRanges(ranges, hashcheck, uid, (),
                                             meta_type, start, limit, sort,
                                             dir, name)
        facade = self._getFacade()
        try:
            facade.deleteComponents(uids)
            return DirectResponse.succeed('Components deleted.')
        except:
            return DirectResponse.fail('Failed to delete components.')

    @require('Delete Device')
    def removeDevices(self, uids, hashcheck, action="remove", uid=None,
                      ranges=(), params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            if action=="remove":
                facade.removeDevices(uids, organizer=uid)
            elif action=="delete":
                facade.deleteDevices(uids)
            return DirectResponse.succeed(
                devtree = self.getTree('/zport/dmd/Devices'),
                grptree = self.getTree('/zport/dmd/Groups'),
                loctree = self.getTree('/zport/dmd/Locations')
            )
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to remove devices.')

    def getEvents(self, uid):
        facade = self._getFacade()
        events = facade.getEvents(uid)
        data = Zuul.marshal(events)
        return DirectResponse(data=data)

    def loadRanges(self, ranges, hashcheck, uid=None, params=None,
                      sort='name', dir='ASC'):
        facade = self._getFacade()
        if isinstance(params, basestring):
            params = unjson(params)
        devs = facade.getDevices(uid, sort=sort, dir=dir, params=params,
                                 hashcheck=hashcheck)
        uids = []
        for start, stop in sorted(ranges):
            uids.extend(b.uid for b in islice(devs, start, stop))
        return uids

    def loadComponentRanges(self, ranges, hashcheck, uid=None, types=(),
                            meta_type=(), start=0, limit=None, sort='name',
                            dir='ASC', name=None):
        facade = self._getFacade()
        comps = facade.getComponents(uid, types, meta_type, start, limit, sort,
                                     dir, name)
        uids = []
        for start, stop in sorted(ranges):
            uids.extend(b.uid for b in islice(comps, start, stop))
        return uids

    def getUserCommands(self, uid):
        facade = self._getFacade()
        cmds = facade.getUserCommands(uid)
        return Zuul.marshal(cmds, ['id', 'description'])

    def getProductionStates(self):
        return [s.split(':') for s in self.context.dmd.prodStateConversions]

    def getPriorities(self):
        return [s.split(':') for s in self.context.dmd.priorityConversions]

    def getCollectors(self):
        return self.context.dmd.Monitors.getPerformanceMonitorNames()

    def getDeviceClasses(self, **data):
        deviceClasses = self.context.dmd.Devices.getOrganizerNames(addblank=True)
        result = [{'name': name} for name in deviceClasses];
        return DirectResponse(deviceClasses=result, totalCount=len(result))
    
    def getManufacturerNames(self, **data):
        names = self.context.dmd.Manufacturers.getManufacturerNames()
        result = [{'name': name} for name in names];
        return DirectResponse(manufacturers=result, totalCount=len(result))
    
    def getHardwareProductNames(self, manufacturer = '', **data):
        manufacturers = self.context.dmd.Manufacturers
        names = manufacturers.getProductNames(manufacturer, 'HardwareClass')
        result = [{'name': name} for name in names];
        return DirectResponse(productNames=result, totalCount=len(result))

    def getOSProductNames(self, manufacturer = '', **data):
        manufacturers = self.context.dmd.Manufacturers
        names = manufacturers.getProductNames(manufacturer, 'OS')
        result = [{'name': name} for name in names];
        return DirectResponse(productNames=result, totalCount=len(result))

    @require('Manage DMD')
    def addDevice(self, deviceName, deviceClass, title=None, snmpCommunity="", snmpPort=161,
                  model=False, collector='localhost',  rackSlot=0, 
                  productionState=1000, comments="", hwManufacturer="", 
                  hwProductName="", osManufacturer="", osProductName="", 
                  priority = 3, tag="", serialNumber=""):
        jobStatus = self._getFacade().addDevice(deviceName, 
                                               deviceClass, 
                                               title,
                                               snmpCommunity, 
                                               snmpPort,
                                               model,
                                               collector, 
                                               rackSlot, 
                                               productionState, 
                                               comments, 
                                               hwManufacturer,
                                               hwProductName, 
                                               osManufacturer,
                                               osProductName, 
                                               priority, 
                                               tag,
                                               serialNumber)
        return DirectResponse(jobId=jobStatus.id)
        
    def getTemplates(self, id):
        facade = self._getFacade()
        templates = facade.getTemplates(id)
        return Zuul.marshal(templates)

    def getUnboundTemplates(self, uid):
        facade = self._getFacade()
        templates = facade.getUnboundTemplates(uid)
        return {'data': Zuul.marshal(templates), 'success': True}

    def getBoundTemplates(self, uid):
        facade = self._getFacade()
        templates = facade.getBoundTemplates(uid)
        return {'data': Zuul.marshal(templates), 'success': True}

    def setBoundTemplates(self, uid, templateIds):
        facade = self._getFacade()
        facade.setBoundTemplates(uid, templateIds)
        return {'success': True}

    def clearGeocodeCache(self):
        self.context.clearGeocodeCache()
        return DirectResponse.succeed()
